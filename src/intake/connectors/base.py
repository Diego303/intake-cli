"""Base connector registry and exceptions.

Connectors fetch content from remote sources (Jira, Confluence, GitHub, URLs)
and produce local temporary files that parsers can then process.

The connector registry maps URI schemes to connector instances and
orchestrates fetching operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from intake.plugins.protocols import ConnectorPlugin, FetchedSource

logger = structlog.get_logger()


class ConnectorError(Exception):
    """Base exception for connector errors."""

    def __init__(self, reason: str, suggestion: str = "") -> None:
        self.reason = reason
        self.suggestion = suggestion
        msg = f"Connector error: {reason}"
        if suggestion:
            msg += f"\n  Hint: {suggestion}"
        super().__init__(msg)


class ConnectorNotFoundError(ConnectorError):
    """No connector available for the given URI scheme."""

    def __init__(self, uri: str) -> None:
        self.uri = uri
        super().__init__(
            reason=f"No connector available for URI: {uri}",
            suggestion=(
                "Install the appropriate connector package, or check that "
                "the URI scheme is correct. Supported schemes can be listed "
                "with 'intake plugins list'."
            ),
        )


class ConnectorRegistry:
    """Registry of available source connectors.

    Maps URI schemes to connector instances. Populated by the plugin
    system during discovery, or manually via ``register()``.

    Example::

        registry = ConnectorRegistry()
        registry.register("jira", jira_connector)
        sources = await registry.fetch("jira://PROJ-123")
    """

    def __init__(self) -> None:
        self._connectors: dict[str, ConnectorPlugin] = {}

    def register(self, name: str, connector: ConnectorPlugin) -> None:
        """Register a connector by name.

        Args:
            name: Connector identifier (e.g. "jira", "confluence").
            connector: Connector instance.
        """
        self._connectors[name] = connector
        logger.debug(
            "connector_registered",
            name=name,
            schemes=connector.uri_schemes,
        )

    def find_for_uri(self, uri: str) -> ConnectorPlugin | None:
        """Find a connector that can handle the given URI.

        Args:
            uri: Source URI string.

        Returns:
            Connector instance, or None if no connector matches.
        """
        for connector in self._connectors.values():
            if connector.can_handle(uri):
                return connector
        return None

    async def fetch(self, uri: str) -> list[FetchedSource]:
        """Fetch a source URI using the appropriate connector.

        Args:
            uri: Source URI to fetch.

        Returns:
            List of FetchedSource objects with local temp file paths.

        Raises:
            ConnectorNotFoundError: If no connector handles this URI.
        """
        connector = self.find_for_uri(uri)
        if connector is None:
            raise ConnectorNotFoundError(uri)

        logger.info("connector_fetching", uri=uri, connector=connector.meta.name)
        return await connector.fetch(uri)

    def validate_all(self) -> dict[str, list[str]]:
        """Validate all connector configurations.

        Returns:
            Dict mapping connector names to lists of error messages.
            Only connectors with errors are included.
        """
        results: dict[str, list[str]] = {}
        for name, connector in self._connectors.items():
            errors = connector.validate_config()
            if errors:
                results[name] = errors
        return results

    @property
    def available_schemes(self) -> list[str]:
        """List of all registered connector names."""
        return sorted(self._connectors.keys())
