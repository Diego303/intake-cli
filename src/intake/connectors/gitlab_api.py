"""GitLab Issues API connector.

Fetches issues from GitLab projects (Cloud and self-hosted) and saves them
as local JSON files that the GitlabIssuesParser can process.

Supported URI patterns:
- Single issue: ``gitlab://group/project/issues/42``
- Multiple issues: ``gitlab://group/project/issues/42,43,44``
- Filtered issues: ``gitlab://group/project/issues?labels=bug&state=opened``
- Milestone issues: ``gitlab://group/project/milestones/3/issues``

Works with GitLab.com (SaaS), self-hosted GitLab CE/EE, and local instances.

Requires: ``pip install intake-ai-cli[connectors]``
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any

import structlog

from intake.config.schema import GitlabConfig
from intake.connectors.base import ConnectorError
from intake.plugins.protocols import FetchedSource, PluginMeta

logger = structlog.get_logger()

MAX_ISSUES = 50
MAX_NOTES_PER_ISSUE = 10


class GitlabConnector:
    """Connector for GitLab Issues API (Cloud and self-hosted).

    Implements the ConnectorPlugin protocol. Fetches issues via python-gitlab
    and writes them as JSON temp files in the format expected by
    GitlabIssuesParser.
    """

    def __init__(self, config: GitlabConfig | None = None) -> None:
        self._config = config or GitlabConfig()
        self._client: Any = None

    @property
    def meta(self) -> PluginMeta:
        """Plugin metadata."""
        return PluginMeta(
            name="gitlab",
            version="1.0.0",
            description="GitLab Cloud/Self-hosted Issues API connector",
        )

    @property
    def uri_schemes(self) -> list[str]:
        """Supported URI schemes."""
        return ["gitlab://"]

    def can_handle(self, uri: str) -> bool:
        """Check if this connector handles the given URI."""
        return uri.startswith("gitlab://")

    async def fetch(self, uri: str) -> list[FetchedSource]:
        """Fetch GitLab issues and save as JSON temp files.

        Args:
            uri: GitLab source URI (e.g. ``gitlab://group/project/issues/42``).

        Returns:
            List of FetchedSource with local JSON file paths.

        Raises:
            ConnectorError: If the GitLab API call fails.
        """
        self._ensure_client()

        path, params = self._parse_uri(uri)
        issues = self._resolve_issues(path, params)

        results: list[FetchedSource] = []
        for issue_data in issues:
            iid = issue_data.get("iid", 0)
            project_path = issue_data.get("_project_path", path.rsplit("/issues", 1)[0])
            safe_project = project_path.replace("/", "_")

            try:
                tmp = tempfile.NamedTemporaryFile(  # noqa: SIM115
                    mode="w",
                    suffix=".json",
                    prefix=f"gitlab_{safe_project}_{iid}_",
                    delete=False,
                )
                json.dump(issue_data, tmp, indent=2, default=str)
                tmp.close()
            except OSError as e:
                raise ConnectorError(
                    reason=f"Could not write temp file for issue #{iid}: {e}",
                    suggestion="Check disk space and permissions on the temp directory.",
                ) from e

            results.append(
                FetchedSource(
                    local_path=tmp.name,
                    original_uri=f"gitlab://{project_path}/issues/{iid}",
                    format_hint="gitlab_issues",
                    metadata={
                        "iid": str(iid),
                        "title": issue_data.get("title", ""),
                        "project": project_path,
                        "source_type": "gitlab",
                    },
                )
            )

        logger.info("gitlab_fetched", uri=uri, issues=len(results))
        return results

    def validate_config(self) -> list[str]:
        """Check that GitLab credentials are configured.

        Returns:
            List of error messages. Empty means valid.
        """
        errors: list[str] = []
        if not self._config.url:
            errors.append("GitLab URL not configured (connectors.gitlab.url in .intake.yaml)")
        if not os.environ.get(self._config.token_env):
            errors.append(
                f"Environment variable {self._config.token_env} is not set. "
                f"Create a personal access token with 'read_api' scope at "
                f"{self._config.url}/-/user_settings/personal_access_tokens"
            )
        return errors

    def _ensure_client(self) -> None:
        """Lazily initialize the GitLab API client."""
        if self._client is not None:
            return

        try:
            import gitlab as gitlab_lib
        except ImportError as e:
            raise ConnectorError(
                reason="GitLab connector requires python-gitlab.",
                suggestion="Install with: pip install intake-ai-cli[connectors]",
            ) from e

        token = os.environ.get(self._config.token_env, "")
        if not token:
            raise ConnectorError(
                reason=f"Environment variable {self._config.token_env} is not set.",
                suggestion=(
                    f"Create a personal access token with 'read_api' scope at "
                    f"{self._config.url}/-/user_settings/personal_access_tokens"
                ),
            )

        try:
            self._client = gitlab_lib.Gitlab(
                url=self._config.url,
                private_token=token,
                ssl_verify=self._config.ssl_verify,
            )
            self._client.auth()
        except Exception as e:
            err_str = str(e)
            if "401" in err_str or "authentication" in err_str.lower():
                raise ConnectorError(
                    reason=f"GitLab authentication failed at {self._config.url}.",
                    suggestion=(
                        f"Check your {self._config.token_env} token and ensure "
                        f"it has 'read_api' scope."
                    ),
                ) from e
            raise ConnectorError(
                reason=f"Could not connect to GitLab at {self._config.url}: {e}",
                suggestion=(
                    "Check the URL and network connectivity. "
                    "For self-hosted instances with self-signed certs, "
                    "set connectors.gitlab.ssl_verify to false."
                ),
            ) from e

    def _parse_uri(self, uri: str) -> tuple[str, dict[str, str]]:
        """Parse a GitLab URI into path and query params."""
        remainder = uri.removeprefix("gitlab://")
        if "?" in remainder:
            path, query = remainder.split("?", 1)
            params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
            return path, params
        return remainder, {}

    def _resolve_issues(
        self,
        path: str,
        params: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Resolve a GitLab URI path to a list of issue dicts.

        Args:
            path: URI path after ``gitlab://``.
            params: Query parameters.

        Returns:
            List of serialized issue dicts.

        Raises:
            ConnectorError: If the API call fails.
        """
        assert self._client is not None

        parts = path.split("/")
        project_path, resource_path = self._split_project_resource(parts)

        try:
            project = self._client.projects.get(project_path)
        except Exception as e:
            raise ConnectorError(
                reason=f"Could not access GitLab project '{project_path}': {e}",
                suggestion=(
                    "Check that the project path is correct and your "
                    f"{self._config.token_env} has access."
                ),
            ) from e

        try:
            return self._do_resolve(project, project_path, resource_path, params)
        except ConnectorError:
            raise
        except Exception as e:
            raise ConnectorError(
                reason=f"GitLab API call failed: {e}",
                suggestion="Check that the issue IDs, labels, or milestone are valid.",
            ) from e

    def _do_resolve(
        self,
        project: Any,
        project_path: str,
        resource_path: str,
        params: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Internal issue resolution logic."""
        # Milestone issues: milestones/3/issues
        if resource_path.startswith("milestones/"):
            ms_parts = resource_path.split("/")
            if len(ms_parts) >= 2:
                milestone_id = int(ms_parts[1])
                milestone = project.milestones.get(milestone_id)
                raw_issues = milestone.issues()
                return [
                    self._issue_to_dict(project.issues.get(i.iid), project_path)
                    for i in list(raw_issues)[:MAX_ISSUES]
                ]

        # Specific issues: issues/42 or issues/42,43,44
        if resource_path.startswith("issues/") and resource_path[7:]:
            iids_str = resource_path[7:]
            iids = [int(n.strip()) for n in iids_str.split(",")]
            return [self._issue_to_dict(project.issues.get(iid), project_path) for iid in iids]

        # Filtered list: issues?labels=bug&state=opened
        kwargs: dict[str, Any] = {}
        if "labels" in params:
            kwargs["labels"] = params["labels"].split(",")
        if "state" in params:
            kwargs["state"] = params["state"]
        if "milestone" in params:
            kwargs["milestone"] = params["milestone"]
        if "assignee_username" in params:
            kwargs["assignee_username"] = params["assignee_username"]
        if "search" in params:
            kwargs["search"] = params["search"]

        kwargs["order_by"] = params.get("order_by", "created_at")
        kwargs["sort"] = params.get("sort", "desc")

        raw_issues = project.issues.list(per_page=MAX_ISSUES, get_all=False, **kwargs)
        return [self._issue_to_dict(issue, project_path) for issue in raw_issues]

    def _split_project_resource(self, parts: list[str]) -> tuple[str, str]:
        """Split URI parts into project path and resource path.

        Handles nested groups: ``group/subgroup/project/issues/42``.
        Strategy: find "issues" or "milestones" keyword to split.

        Args:
            parts: URI path split by ``/``.

        Returns:
            Tuple of (project_path, resource_path).

        Raises:
            ConnectorError: If the URI cannot be parsed.
        """
        for i, part in enumerate(parts):
            if part in ("issues", "milestones"):
                project_path = "/".join(parts[:i])
                resource_path = "/".join(parts[i:])
                return project_path, resource_path

        raise ConnectorError(
            reason=f"Could not parse GitLab URI path: {'/'.join(parts)}",
            suggestion=(
                "Expected format: gitlab://group/project/issues/42 or "
                "gitlab://group/project/milestones/3/issues"
            ),
        )

    def _issue_to_dict(self, issue: Any, project_path: str) -> dict[str, Any]:
        """Convert a python-gitlab Issue object to a serializable dict.

        The output format matches what GitlabIssuesParser expects.

        Args:
            issue: python-gitlab Issue object.
            project_path: Full project path for metadata.

        Returns:
            Serializable dict with issue data.
        """
        data: dict[str, Any] = {
            "iid": issue.iid,
            "id": issue.id,
            "title": issue.title,
            "description": issue.description or "",
            "state": issue.state,
            "labels": issue.labels,
            "milestone": (issue.milestone.get("title") if issue.milestone else None),
            "assignees": [a.get("username", "") for a in (issue.assignees or [])],
            "author": (issue.author.get("username", "") if issue.author else ""),
            "weight": getattr(issue, "weight", None),
            "due_date": issue.due_date,
            "created_at": str(issue.created_at),
            "updated_at": str(issue.updated_at),
            "web_url": issue.web_url,
            "confidential": issue.confidential,
            "task_completion_status": getattr(issue, "task_completion_status", None),
            "_project_path": project_path,
        }

        # Fetch discussion notes (non-system)
        if self._config.include_comments:
            max_notes = min(self._config.max_notes, MAX_NOTES_PER_ISSUE)
            try:
                notes = issue.notes.list(
                    per_page=max_notes,
                    order_by="created_at",
                )
                data["notes"] = [
                    {
                        "author": (n.author.get("username", "") if n.author else "unknown"),
                        "body": n.body or "",
                        "created_at": str(n.created_at),
                        "system": n.system,
                    }
                    for n in notes
                    if not n.system
                ]
            except Exception as e:
                logger.warning(
                    "gitlab_notes_fetch_failed",
                    iid=issue.iid,
                    error=str(e),
                )
                data["notes"] = []

        # Fetch linked merge requests if configured
        if self._config.include_merge_requests:
            try:
                mrs = issue.related_merge_requests()
                data["merge_requests"] = [
                    {
                        "iid": mr.get("iid"),
                        "title": mr.get("title", ""),
                        "state": mr.get("state", ""),
                        "web_url": mr.get("web_url", ""),
                    }
                    for mr in (mrs or [])
                ]
            except Exception:
                data["merge_requests"] = []

        return data
