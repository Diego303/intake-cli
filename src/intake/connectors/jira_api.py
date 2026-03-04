"""Jira Cloud and Server REST API connector.

Fetches issues from Jira via its REST API and saves them as local
JSON files that the JiraParser can process.

Supported URI patterns:
- Single issue: ``jira://PROJ-123``
- Multiple issues: ``jira://PROJ-123,PROJ-124,PROJ-125``
- JQL query: ``jira://PROJ?jql=sprint%20%3D%2042``
- Sprint: ``jira://PROJ/sprint/42``

Requires: ``pip install intake-ai-cli[connectors]``

Auth via ``JIRA_API_TOKEN`` + ``JIRA_EMAIL`` env vars (or custom env var names
configured in ``.intake.yaml``).
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any

import structlog

from intake.config.schema import JiraConfig
from intake.connectors.base import ConnectorError
from intake.plugins.protocols import FetchedSource, PluginMeta

logger = structlog.get_logger()


class JiraConnector:
    """Connector for Jira Cloud and Server REST API.

    Implements the ConnectorPlugin protocol. Fetches issues via the
    atlassian-python-api library and writes them as JSON temp files
    in the format expected by JiraParser.
    """

    def __init__(self, config: JiraConfig | None = None) -> None:
        self._config = config or JiraConfig()
        self._client: Any = None

    @property
    def meta(self) -> PluginMeta:
        """Plugin metadata."""
        return PluginMeta(
            name="jira",
            version="1.0.0",
            description="Jira Cloud/Server API connector",
        )

    @property
    def uri_schemes(self) -> list[str]:
        """Supported URI schemes."""
        return ["jira://"]

    def can_handle(self, uri: str) -> bool:
        """Check if this connector handles the given URI."""
        return uri.startswith("jira://")

    async def fetch(self, uri: str) -> list[FetchedSource]:
        """Fetch Jira issues and save as JSON temp files.

        Args:
            uri: Jira source URI (e.g. ``jira://PROJ-123``).

        Returns:
            List of FetchedSource with local JSON file paths.

        Raises:
            ConnectorError: If the Jira API call fails.
        """
        self._ensure_client()

        path, params = self._parse_uri(uri)
        issues = self._resolve_issues(path, params)

        results: list[FetchedSource] = []
        for issue in issues:
            key = issue.get("key", "UNKNOWN")
            tmp = tempfile.NamedTemporaryFile(  # noqa: SIM115
                mode="w",
                suffix=".json",
                prefix=f"jira_{key}_",
                delete=False,
            )
            json.dump({"issues": [issue]}, tmp, indent=2)
            tmp.close()

            results.append(
                FetchedSource(
                    local_path=tmp.name,
                    original_uri=f"jira://{key}",
                    format_hint="jira",
                    metadata={
                        "key": key,
                        "summary": issue.get("fields", {}).get("summary", ""),
                    },
                )
            )

        logger.info("jira_fetched", uri=uri, issues=len(results))
        return results

    def validate_config(self) -> list[str]:
        """Check that Jira credentials are configured.

        Returns:
            List of error messages. Empty means valid.
        """
        errors: list[str] = []
        if not self._config.url:
            errors.append("Jira URL not configured. Set 'connectors.jira.url' in .intake.yaml.")
        if not os.environ.get(self._config.token_env):
            errors.append(
                f"Environment variable {self._config.token_env} is not set. "
                f"Set it to your Jira API token."
            )
        if self._config.auth_type == "token" and not os.environ.get(self._config.email_env):
            errors.append(
                f"Environment variable {self._config.email_env} is not set. "
                f"Set it to your Jira account email."
            )
        return errors

    def _ensure_client(self) -> None:
        """Lazily initialize the Jira API client."""
        if self._client is not None:
            return

        try:
            from atlassian import Jira
        except ImportError as e:
            raise ConnectorError(
                reason="Jira connector requires atlassian-python-api.",
                suggestion="Install with: pip install intake-ai-cli[connectors]",
            ) from e

        token = os.environ.get(self._config.token_env, "")
        email = os.environ.get(self._config.email_env, "")

        if not self._config.url:
            raise ConnectorError(
                reason="Jira URL is not configured.",
                suggestion="Set 'connectors.jira.url' in .intake.yaml.",
            )

        try:
            self._client = Jira(
                url=self._config.url,
                username=email,
                password=token,
                cloud=".atlassian.net" in self._config.url,
            )
        except Exception as e:
            raise ConnectorError(
                reason=f"Could not connect to Jira at {self._config.url}: {e}",
                suggestion=(
                    f"Check your {self._config.token_env} and "
                    f"{self._config.email_env} env vars, and verify "
                    "the URL in .intake.yaml (connectors.jira.url)."
                ),
            ) from e

    def _parse_uri(self, uri: str) -> tuple[str, dict[str, str]]:
        """Parse a Jira URI into path and query params."""
        remainder = uri.removeprefix("jira://")
        if "?" in remainder:
            path, query = remainder.split("?", 1)
            params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
            return path, params
        return remainder, {}

    def _resolve_issues(self, path: str, params: dict[str, str]) -> list[dict[str, Any]]:
        """Resolve a URI path to a list of Jira issue dicts.

        Args:
            path: URI path component (e.g. ``PROJ-123``, ``PROJ/sprint/42``).
            params: Query parameters (e.g. ``{"jql": "sprint = 42"}``).

        Returns:
            List of issue dicts in Jira REST API format.

        Raises:
            ConnectorError: If the API call fails.
        """
        assert self._client is not None

        try:
            return self._do_resolve(path, params)
        except ConnectorError:
            raise
        except Exception as e:
            raise ConnectorError(
                reason=f"Jira API call failed: {e}",
                suggestion=(
                    "Check your credentials, network connectivity, and "
                    "that the issue keys or JQL query are valid."
                ),
            ) from e

    def _do_resolve(self, path: str, params: dict[str, str]) -> list[dict[str, Any]]:
        """Internal issue resolution logic."""
        fields = ",".join(self._config.fields)

        # JQL query: jira://PROJ?jql=...
        if "jql" in params:
            data = self._client.jql(
                params["jql"],
                limit=50,
                fields=fields,
            )
            return list(data.get("issues", []))

        # Sprint: jira://PROJ/sprint/42
        if "/sprint/" in path:
            parts = path.split("/sprint/")
            sprint_id = parts[1]
            jql = f"sprint = {sprint_id} ORDER BY rank"
            data = self._client.jql(jql, limit=100, fields=fields)
            return list(data.get("issues", []))

        # Multiple issues: jira://PROJ-1,PROJ-2,PROJ-3
        if "," in path:
            keys = [k.strip() for k in path.split(",")]
            jql = f"key in ({','.join(keys)})"
            data = self._client.jql(jql, limit=len(keys), fields=fields)
            return list(data.get("issues", []))

        # Single issue: jira://PROJ-123
        issue = self._client.issue(path, fields=fields)
        if isinstance(issue, dict):
            return [issue]
        return []
