"""Confluence Cloud and Server REST API connector.

Fetches pages from Confluence and saves them as local HTML files
that the ConfluenceParser can process.

Supported URI patterns:
- Page by ID: ``confluence://page/123456789``
- Page by space+title: ``confluence://SPACE/Page-Title``
- CQL search: ``confluence://search?cql=space.key%3DENG``

Requires: ``pip install intake-ai-cli[connectors]``
"""

from __future__ import annotations

import os
import tempfile
from typing import Any

import structlog

from intake.config.schema import ConfluenceConfig
from intake.connectors.base import ConnectorError
from intake.plugins.protocols import FetchedSource, PluginMeta

logger = structlog.get_logger()


class ConfluenceConnector:
    """Connector for Confluence Cloud and Server REST API.

    Implements the ConnectorPlugin protocol. Fetches pages via the
    atlassian-python-api library and writes them as HTML temp files
    in the format expected by ConfluenceParser.
    """

    def __init__(self, config: ConfluenceConfig | None = None) -> None:
        self._config = config or ConfluenceConfig()
        self._client: Any = None

    @property
    def meta(self) -> PluginMeta:
        """Plugin metadata."""
        return PluginMeta(
            name="confluence",
            version="1.0.0",
            description="Confluence Cloud/Server API connector",
        )

    @property
    def uri_schemes(self) -> list[str]:
        """Supported URI schemes."""
        return ["confluence://"]

    def can_handle(self, uri: str) -> bool:
        """Check if this connector handles the given URI."""
        return uri.startswith("confluence://")

    async def fetch(self, uri: str) -> list[FetchedSource]:
        """Fetch Confluence pages and save as HTML temp files.

        Args:
            uri: Confluence source URI (e.g. ``confluence://SPACE/Page-Title``).

        Returns:
            List of FetchedSource with local HTML file paths.

        Raises:
            ConnectorError: If the Confluence API call fails.
        """
        self._ensure_client()

        path, params = self._parse_uri(uri)
        pages = self._resolve_pages(path, params)

        results: list[FetchedSource] = []
        for page in pages:
            page_id = str(page.get("id", "unknown"))
            title = page.get("title", f"page-{page_id}")
            body_html = self._extract_body(page)

            safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in title)
            try:
                tmp = tempfile.NamedTemporaryFile(  # noqa: SIM115
                    mode="w",
                    suffix=".html",
                    prefix=f"confluence_{safe_title}_",
                    delete=False,
                    encoding="utf-8",
                )
                # Wrap in HTML with Confluence marker for parser auto-detection
                tmp.write(
                    f"<!-- Confluence page: {title} (id: {page_id}) -->\n"
                    f"<html><head><title>{title}</title></head>\n"
                    f"<body class='confluence-page'>\n{body_html}\n</body></html>"
                )
                tmp.close()
            except OSError as e:
                raise ConnectorError(
                    reason=f"Could not write temp file for page '{title}': {e}",
                    suggestion="Check disk space and permissions on the temp directory.",
                ) from e

            results.append(
                FetchedSource(
                    local_path=tmp.name,
                    original_uri=f"confluence://page/{page_id}",
                    format_hint="confluence",
                    metadata={"page_id": page_id, "title": title},
                )
            )

        logger.info("confluence_fetched", uri=uri, pages=len(results))
        return results

    def validate_config(self) -> list[str]:
        """Check that Confluence credentials are configured.

        Returns:
            List of error messages. Empty means valid.
        """
        errors: list[str] = []
        if not self._config.url:
            errors.append(
                "Confluence URL not configured. Set 'connectors.confluence.url' in .intake.yaml."
            )
        if not os.environ.get(self._config.token_env):
            errors.append(
                f"Environment variable {self._config.token_env} is not set. "
                f"Set it to your Confluence API token."
            )
        if not os.environ.get(self._config.email_env):
            errors.append(
                f"Environment variable {self._config.email_env} is not set. "
                f"Set it to your Confluence account email."
            )
        return errors

    def _ensure_client(self) -> None:
        """Lazily initialize the Confluence API client."""
        if self._client is not None:
            return

        try:
            from atlassian import Confluence
        except ImportError as e:
            raise ConnectorError(
                reason="Confluence connector requires atlassian-python-api.",
                suggestion="Install with: pip install intake-ai-cli[connectors]",
            ) from e

        if not self._config.url:
            raise ConnectorError(
                reason="Confluence URL is not configured.",
                suggestion=("Set 'connectors.confluence.url' in .intake.yaml."),
            )

        token = os.environ.get(self._config.token_env, "")
        email = os.environ.get(self._config.email_env, "")

        try:
            self._client = Confluence(
                url=self._config.url,
                username=email,
                password=token,
                cloud=".atlassian.net" in self._config.url,
            )
        except Exception as e:
            raise ConnectorError(
                reason=f"Could not connect to Confluence at {self._config.url}: {e}",
                suggestion=(
                    f"Check your {self._config.token_env} and "
                    f"{self._config.email_env} env vars, and verify "
                    "the URL in .intake.yaml (connectors.confluence.url)."
                ),
            ) from e

    def _parse_uri(self, uri: str) -> tuple[str, dict[str, str]]:
        """Parse a Confluence URI into path and query params."""
        remainder = uri.removeprefix("confluence://")
        if "?" in remainder:
            path, query = remainder.split("?", 1)
            params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
            return path, params
        return remainder, {}

    def _resolve_pages(self, path: str, params: dict[str, str]) -> list[dict[str, Any]]:
        """Resolve a URI path to a list of Confluence page dicts.

        Args:
            path: URI path (e.g. ``page/123456``, ``SPACE/Title``).
            params: Query parameters (e.g. ``{"cql": "..."}``).

        Returns:
            List of page dicts from the Confluence API.

        Raises:
            ConnectorError: If the API call fails.
        """
        assert self._client is not None
        expand = "body.storage,version,space"

        try:
            return self._do_resolve(path, params, expand)
        except ConnectorError:
            raise
        except Exception as e:
            raise ConnectorError(
                reason=f"Confluence API call failed: {e}",
                suggestion=(
                    "Check your credentials, network connectivity, and "
                    "that the page ID, space key, or CQL query is valid."
                ),
            ) from e

    def _do_resolve(
        self,
        path: str,
        params: dict[str, str],
        expand: str,
    ) -> list[dict[str, Any]]:
        """Internal page resolution logic."""
        # CQL search: confluence://search?cql=...
        if "cql" in params:
            results = self._client.cql(
                params["cql"],
                limit=20,
                expand=expand,
            )
            return list(results.get("results", []))

        # Page by ID: confluence://page/123456
        if path.startswith("page/"):
            page_id = path.removeprefix("page/")
            page = self._client.get_page_by_id(page_id, expand=expand)
            return [page] if page else []

        # Page by space/title: confluence://SPACE/Page-Title
        if "/" in path:
            space, title = path.split("/", 1)
            title = title.replace("-", " ")
            page = self._client.get_page_by_title(
                space,
                title,
                expand=expand,
            )
            if page:
                return [page] if isinstance(page, dict) else list(page)
            return []

        return []

    def _extract_body(self, page: dict[str, Any]) -> str:
        """Extract HTML body from a Confluence page dict."""
        body = page.get("body", {})
        # Prefer storage format, fall back to view format
        result: str = body.get("storage", {}).get("value", "") or body.get("view", {}).get(
            "value", ""
        )
        return result
