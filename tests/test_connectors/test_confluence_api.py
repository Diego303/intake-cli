"""Tests for Confluence API connector."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from intake.config.schema import ConfluenceConfig
from intake.connectors.base import ConnectorError
from intake.connectors.confluence_api import ConfluenceConnector
from intake.plugins.protocols import FetchedSource, PluginMeta


@pytest.fixture
def confluence_config() -> ConfluenceConfig:
    return ConfluenceConfig(
        url="https://mycompany.atlassian.net/wiki",
        token_env="CONFLUENCE_API_TOKEN",
        email_env="CONFLUENCE_EMAIL",
    )


@pytest.fixture
def connector(confluence_config: ConfluenceConfig) -> ConfluenceConnector:
    return ConfluenceConnector(config=confluence_config)


@pytest.fixture
def mock_confluence_client() -> MagicMock:
    """Create a mock Confluence API client."""
    client = MagicMock()
    sample_page = {
        "id": "123456",
        "title": "Auth RFC",
        "body": {
            "storage": {
                "value": "<h1>Auth RFC</h1><p>OAuth2 design document.</p>",
            },
        },
        "space": {"key": "ENG"},
        "version": {"number": 2},
    }
    client.get_page_by_id.return_value = sample_page
    client.get_page_by_title.return_value = sample_page
    client.cql.return_value = {"results": [sample_page]}
    return client


class TestConfluenceProtocol:
    def test_meta(self, connector: ConfluenceConnector) -> None:
        meta = connector.meta
        assert isinstance(meta, PluginMeta)
        assert meta.name == "confluence"

    def test_uri_schemes(self, connector: ConfluenceConnector) -> None:
        assert connector.uri_schemes == ["confluence://"]

    def test_can_handle(self, connector: ConfluenceConnector) -> None:
        assert connector.can_handle("confluence://ENG/Page-Title") is True
        assert connector.can_handle("confluence://page/123") is True
        assert connector.can_handle("jira://PROJ-123") is False


class TestConfluenceValidateConfig:
    def test_valid_config(self, connector: ConfluenceConnector) -> None:
        with patch.dict(
            os.environ,
            {
                "CONFLUENCE_API_TOKEN": "token",
                "CONFLUENCE_EMAIL": "user@test.com",
            },
        ):
            errors = connector.validate_config()
            assert errors == []

    def test_missing_url(self) -> None:
        conn = ConfluenceConnector(config=ConfluenceConfig(url=""))
        with patch.dict(
            os.environ,
            {
                "CONFLUENCE_API_TOKEN": "token",
                "CONFLUENCE_EMAIL": "email@test.com",
            },
        ):
            errors = conn.validate_config()
            assert len(errors) == 1
            assert "URL" in errors[0]

    def test_missing_token(self, connector: ConfluenceConnector) -> None:
        env = {"CONFLUENCE_EMAIL": "email@test.com"}
        with patch.dict(os.environ, env, clear=True):
            errors = connector.validate_config()
            assert any("CONFLUENCE_API_TOKEN" in e for e in errors)


class TestConfluenceFetch:
    @pytest.mark.asyncio
    async def test_fetch_page_by_id(
        self,
        connector: ConfluenceConnector,
        mock_confluence_client: MagicMock,
    ) -> None:
        connector._client = mock_confluence_client

        results = await connector.fetch("confluence://page/123456")

        assert len(results) == 1
        assert isinstance(results[0], FetchedSource)
        assert results[0].format_hint == "confluence"
        assert results[0].metadata["page_id"] == "123456"
        assert results[0].metadata["title"] == "Auth RFC"

        # Verify file content contains HTML
        content = Path(results[0].local_path).read_text()
        assert "Auth RFC" in content
        assert "confluence-page" in content

        # Cleanup
        Path(results[0].local_path).unlink()

    @pytest.mark.asyncio
    async def test_fetch_page_by_space_title(
        self,
        connector: ConfluenceConnector,
        mock_confluence_client: MagicMock,
    ) -> None:
        connector._client = mock_confluence_client

        results = await connector.fetch("confluence://ENG/Auth-RFC")

        assert len(results) == 1
        mock_confluence_client.get_page_by_title.assert_called_once()
        call_args = mock_confluence_client.get_page_by_title.call_args
        assert call_args[0][0] == "ENG"
        assert call_args[0][1] == "Auth RFC"  # Hyphens replaced with spaces

        # Cleanup
        Path(results[0].local_path).unlink()

    @pytest.mark.asyncio
    async def test_fetch_cql_search(
        self,
        connector: ConfluenceConnector,
        mock_confluence_client: MagicMock,
    ) -> None:
        connector._client = mock_confluence_client

        results = await connector.fetch("confluence://search?cql=space.key=ENG")

        assert len(results) == 1
        mock_confluence_client.cql.assert_called_once()

        # Cleanup
        Path(results[0].local_path).unlink()

    @pytest.mark.asyncio
    async def test_fetch_unknown_path_returns_empty(
        self,
        connector: ConfluenceConnector,
        mock_confluence_client: MagicMock,
    ) -> None:
        connector._client = mock_confluence_client

        results = await connector.fetch("confluence://justAString")

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_fetch_api_failure(
        self,
        connector: ConfluenceConnector,
        mock_confluence_client: MagicMock,
    ) -> None:
        connector._client = mock_confluence_client
        mock_confluence_client.get_page_by_id.side_effect = Exception("Connection timeout")

        with pytest.raises(ConnectorError, match="Confluence API call failed"):
            await connector.fetch("confluence://page/999")
