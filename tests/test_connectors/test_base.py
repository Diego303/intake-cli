"""Tests for the connector registry."""

from __future__ import annotations

import pytest

from intake.connectors.base import (
    ConnectorError,
    ConnectorNotFoundError,
    ConnectorRegistry,
)
from intake.plugins.protocols import FetchedSource, PluginMeta

# ---------------------------------------------------------------------------
# Mock connector for tests
# ---------------------------------------------------------------------------


class MockConnector:
    """A mock connector for testing."""

    def __init__(self, scheme: str = "mock") -> None:
        self._scheme = scheme

    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(name=self._scheme, version="1.0.0", description="Mock connector")

    @property
    def uri_schemes(self) -> list[str]:
        return [f"{self._scheme}://"]

    def can_handle(self, uri: str) -> bool:
        return uri.startswith(f"{self._scheme}://")

    async def fetch(self, uri: str) -> list[FetchedSource]:
        return [
            FetchedSource(
                local_path="/tmp/mock.json",
                original_uri=uri,
                format_hint=self._scheme,
            )
        ]

    def validate_config(self) -> list[str]:
        return []


class MockFailingConnector(MockConnector):
    """A connector that reports config errors."""

    def validate_config(self) -> list[str]:
        return ["API key not set", "URL not configured"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestConnectorError:
    def test_message_without_suggestion(self) -> None:
        err = ConnectorError(reason="connection refused")
        assert "connection refused" in str(err)

    def test_message_with_suggestion(self) -> None:
        err = ConnectorError(reason="timeout", suggestion="increase timeout")
        assert "timeout" in str(err)
        assert "increase timeout" in str(err)


class TestConnectorNotFoundError:
    def test_includes_uri(self) -> None:
        err = ConnectorNotFoundError("notion://page/123")
        assert "notion://page/123" in str(err)
        assert err.uri == "notion://page/123"


class TestConnectorRegistry:
    def test_empty_registry(self) -> None:
        registry = ConnectorRegistry()
        assert registry.available_schemes == []
        assert registry.find_for_uri("jira://X") is None

    def test_register_and_find(self) -> None:
        registry = ConnectorRegistry()
        connector = MockConnector("jira")
        registry.register("jira", connector)

        assert "jira" in registry.available_schemes
        found = registry.find_for_uri("jira://PROJ-123")
        assert found is connector

    def test_find_returns_none_for_unknown(self) -> None:
        registry = ConnectorRegistry()
        registry.register("jira", MockConnector("jira"))
        assert registry.find_for_uri("github://org/repo") is None

    @pytest.mark.asyncio
    async def test_fetch_delegates_to_connector(self) -> None:
        registry = ConnectorRegistry()
        registry.register("mock", MockConnector("mock"))

        results = await registry.fetch("mock://test")
        assert len(results) == 1
        assert results[0].original_uri == "mock://test"
        assert results[0].format_hint == "mock"

    @pytest.mark.asyncio
    async def test_fetch_raises_for_unknown_scheme(self) -> None:
        registry = ConnectorRegistry()
        with pytest.raises(ConnectorNotFoundError):
            await registry.fetch("notion://page/1")

    def test_validate_all_reports_errors(self) -> None:
        registry = ConnectorRegistry()
        registry.register("good", MockConnector("good"))
        registry.register("bad", MockFailingConnector("bad"))

        errors = registry.validate_all()
        assert "good" not in errors
        assert "bad" in errors
        assert len(errors["bad"]) == 2

    def test_validate_all_empty_when_all_valid(self) -> None:
        registry = ConnectorRegistry()
        registry.register("a", MockConnector("a"))
        registry.register("b", MockConnector("b"))

        assert registry.validate_all() == {}

    def test_multiple_connectors(self) -> None:
        registry = ConnectorRegistry()
        registry.register("jira", MockConnector("jira"))
        registry.register("github", MockConnector("github"))

        assert registry.find_for_uri("jira://X") is not None
        assert registry.find_for_uri("github://X") is not None
        assert registry.find_for_uri("confluence://X") is None
