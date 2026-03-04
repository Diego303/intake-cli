"""GitHub Issues API connector.

Fetches issues from GitHub repositories and saves them as local
JSON files that the GithubIssuesParser can process.

Supported URI patterns:
- Single issue: ``github://org/repo/issues/42``
- Multiple issues: ``github://org/repo/issues/42,43,44``
- Filtered issues: ``github://org/repo/issues?labels=bug&state=open``

Requires: ``pip install intake-ai-cli[connectors]``
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any

import structlog

from intake.config.schema import GithubConfig
from intake.connectors.base import ConnectorError
from intake.plugins.protocols import FetchedSource, PluginMeta

logger = structlog.get_logger()

MAX_ISSUES = 50
MAX_COMMENTS_PER_ISSUE = 10


class GithubConnector:
    """Connector for GitHub Issues API.

    Implements the ConnectorPlugin protocol. Fetches issues via PyGithub
    and writes them as JSON temp files in the format expected by
    GithubIssuesParser.
    """

    def __init__(self, config: GithubConfig | None = None) -> None:
        self._config = config or GithubConfig()
        self._client: Any = None

    @property
    def meta(self) -> PluginMeta:
        """Plugin metadata."""
        return PluginMeta(
            name="github",
            version="1.0.0",
            description="GitHub Issues API connector",
        )

    @property
    def uri_schemes(self) -> list[str]:
        """Supported URI schemes."""
        return ["github://"]

    def can_handle(self, uri: str) -> bool:
        """Check if this connector handles the given URI."""
        return uri.startswith("github://")

    async def fetch(self, uri: str) -> list[FetchedSource]:
        """Fetch GitHub issues and save as JSON temp files.

        Args:
            uri: GitHub source URI (e.g. ``github://org/repo/issues/42``).

        Returns:
            List of FetchedSource with local JSON file paths.

        Raises:
            ConnectorError: If the GitHub API call fails.
        """
        self._ensure_client()

        path, params = self._parse_uri(uri)

        # Parse: org/repo/issues/42 or org/repo/issues
        parts = path.split("/")
        if len(parts) < 3:
            raise ConnectorError(
                reason=f"Invalid GitHub URI: {uri}",
                suggestion=(
                    "Expected format: github://org/repo/issues/42 or "
                    "github://org/repo/issues?labels=bug"
                ),
            )

        org, repo = parts[0], parts[1]
        repo_full = f"{org}/{repo}"
        rest = "/".join(parts[2:])

        issues = self._resolve_issues(repo_full, rest, params)

        results: list[FetchedSource] = []
        for issue_data in issues:
            number = issue_data.get("number", 0)
            tmp = tempfile.NamedTemporaryFile(  # noqa: SIM115
                mode="w",
                suffix=".json",
                prefix=f"github_{repo}_{number}_",
                delete=False,
            )
            json.dump(issue_data, tmp, indent=2, default=str)
            tmp.close()

            results.append(
                FetchedSource(
                    local_path=tmp.name,
                    original_uri=f"github://{repo_full}/issues/{number}",
                    format_hint="github_issues",
                    metadata={
                        "number": str(number),
                        "title": issue_data.get("title", ""),
                        "repo": repo_full,
                    },
                )
            )

        logger.info("github_fetched", uri=uri, issues=len(results))
        return results

    def validate_config(self) -> list[str]:
        """Check that GitHub credentials are configured.

        Returns:
            List of error messages. Empty means valid.
        """
        errors: list[str] = []
        if not os.environ.get(self._config.token_env):
            errors.append(
                f"Environment variable {self._config.token_env} is not set. "
                f"Set it to a GitHub personal access token."
            )
        return errors

    def _ensure_client(self) -> None:
        """Lazily initialize the GitHub API client."""
        if self._client is not None:
            return

        try:
            from github import Github
        except ImportError as e:
            raise ConnectorError(
                reason="GitHub connector requires PyGithub.",
                suggestion="Install with: pip install intake-ai-cli[connectors]",
            ) from e

        token = os.environ.get(self._config.token_env, "")
        if not token:
            raise ConnectorError(
                reason=f"Environment variable {self._config.token_env} is not set.",
                suggestion="Set it to a GitHub personal access token.",
            )

        try:
            self._client = Github(token)
        except Exception as e:
            raise ConnectorError(
                reason=f"Could not initialize GitHub client: {e}",
                suggestion=f"Check your {self._config.token_env} env var.",
            ) from e

    def _parse_uri(self, uri: str) -> tuple[str, dict[str, str]]:
        """Parse a GitHub URI into path and query params."""
        remainder = uri.removeprefix("github://")
        if "?" in remainder:
            path, query = remainder.split("?", 1)
            params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
            return path, params
        return remainder, {}

    def _resolve_issues(
        self,
        repo_full: str,
        rest: str,
        params: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Resolve a URI to a list of GitHub issue dicts.

        Args:
            repo_full: Full repo name (e.g. ``org/repo``).
            rest: URI path after repo (e.g. ``issues/42``).
            params: Query parameters (e.g. ``{"labels": "bug"}``).

        Returns:
            List of serialized issue dicts.

        Raises:
            ConnectorError: If the API call fails.
        """
        assert self._client is not None

        try:
            repo = self._client.get_repo(repo_full)
        except Exception as e:
            raise ConnectorError(
                reason=f"Could not access repository {repo_full}: {e}",
                suggestion=(
                    "Check that the repository exists and your "
                    f"{self._config.token_env} has access."
                ),
            ) from e

        try:
            return self._do_resolve(repo, rest, params)
        except ConnectorError:
            raise
        except Exception as e:
            raise ConnectorError(
                reason=f"GitHub API call failed: {e}",
                suggestion=("Check that the issue numbers, labels, or milestone name are valid."),
            ) from e

    def _do_resolve(
        self,
        repo: Any,
        rest: str,
        params: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Internal issue resolution logic."""
        # Specific issues: issues/42,43,44
        if rest.startswith("issues/") and rest[7:]:
            numbers_str = rest[7:]
            numbers = [int(n.strip()) for n in numbers_str.split(",")]
            return [self._issue_to_dict(repo.get_issue(n)) for n in numbers]

        # Filtered list: issues?labels=bug&state=open
        kwargs: dict[str, Any] = {}
        if "labels" in params:
            kwargs["labels"] = [
                repo.get_label(label.strip()) for label in params["labels"].split(",")
            ]
        if "state" in params:
            kwargs["state"] = params["state"]
        if "milestone" in params:
            for ms in repo.get_milestones():
                if ms.title == params["milestone"]:
                    kwargs["milestone"] = ms
                    break

        issues = repo.get_issues(**kwargs)
        return [self._issue_to_dict(issue) for issue in list(issues[:MAX_ISSUES])]

    def _issue_to_dict(self, issue: Any) -> dict[str, Any]:
        """Convert a PyGithub Issue to a serializable dict.

        The output format matches what GithubIssuesParser expects.
        """
        comments = [
            {
                "author": c.user.login if c.user else "unknown",
                "body": c.body or "",
                "created_at": str(c.created_at),
            }
            for c in list(issue.get_comments()[:MAX_COMMENTS_PER_ISSUE])
        ]
        return {
            "number": issue.number,
            "title": issue.title,
            "body": issue.body or "",
            "state": issue.state,
            "labels": [label.name for label in issue.labels],
            "assignees": [a.login for a in issue.assignees],
            "milestone": (issue.milestone.title if issue.milestone else None),
            "comments": comments,
            "created_at": str(issue.created_at),
            "updated_at": str(issue.updated_at),
        }
