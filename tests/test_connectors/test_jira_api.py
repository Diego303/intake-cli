"""Tests for Jira API connector."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from intake.config.schema import JiraConfig
from intake.connectors.base import ConnectorError
from intake.connectors.jira_api import JiraConnector
from intake.plugins.protocols import FetchedSource, PluginMeta


@pytest.fixture
def jira_config() -> JiraConfig:
    return JiraConfig(
        url="https://mycompany.atlassian.net",
        token_env="JIRA_API_TOKEN",
        email_env="JIRA_EMAIL",
    )


@pytest.fixture
def connector(jira_config: JiraConfig) -> JiraConnector:
    return JiraConnector(config=jira_config)


@pytest.fixture
def mock_jira_client() -> MagicMock:
    """Create a mock Jira API client."""
    client = MagicMock()
    client.issue.return_value = {
        "key": "PROJ-123",
        "fields": {
            "summary": "Test issue",
            "description": "Test description",
            "priority": {"name": "High"},
            "status": {"name": "To Do"},
            "labels": ["backend"],
            "comment": {"comments": []},
            "issuelinks": [],
        },
    }
    client.jql.return_value = {
        "issues": [
            {
                "key": "PROJ-123",
                "fields": {
                    "summary": "Test issue",
                    "description": "Test description",
                    "priority": {"name": "High"},
                    "status": {"name": "To Do"},
                    "labels": [],
                    "comment": {"comments": []},
                    "issuelinks": [],
                },
            },
            {
                "key": "PROJ-124",
                "fields": {
                    "summary": "Another issue",
                    "description": "Another description",
                    "priority": {"name": "Medium"},
                    "status": {"name": "In Progress"},
                    "labels": [],
                    "comment": {"comments": []},
                    "issuelinks": [],
                },
            },
        ],
    }
    return client


class TestJiraConnectorProtocol:
    def test_meta(self, connector: JiraConnector) -> None:
        meta = connector.meta
        assert isinstance(meta, PluginMeta)
        assert meta.name == "jira"
        assert meta.version == "1.0.0"

    def test_uri_schemes(self, connector: JiraConnector) -> None:
        assert connector.uri_schemes == ["jira://"]

    def test_can_handle_jira_uri(self, connector: JiraConnector) -> None:
        assert connector.can_handle("jira://PROJ-123") is True
        assert connector.can_handle("jira://PROJ?jql=sprint=42") is True

    def test_cannot_handle_other_uris(self, connector: JiraConnector) -> None:
        assert connector.can_handle("github://org/repo") is False
        assert connector.can_handle("confluence://SPACE/page") is False
        assert connector.can_handle("https://example.com") is False


class TestJiraValidateConfig:
    def test_valid_config(self, connector: JiraConnector) -> None:
        with patch.dict(
            os.environ,
            {
                "JIRA_API_TOKEN": "test-token",
                "JIRA_EMAIL": "user@example.com",
            },
        ):
            errors = connector.validate_config()
            assert errors == []

    def test_missing_url(self) -> None:
        conn = JiraConnector(config=JiraConfig(url=""))
        with patch.dict(
            os.environ,
            {
                "JIRA_API_TOKEN": "test-token",
                "JIRA_EMAIL": "user@example.com",
            },
        ):
            errors = conn.validate_config()
            assert len(errors) == 1
            assert "URL" in errors[0]

    def test_missing_token(self, connector: JiraConnector) -> None:
        with patch.dict(os.environ, {"JIRA_EMAIL": "user@example.com"}, clear=False):
            # Ensure token env is not set
            env = os.environ.copy()
            env.pop("JIRA_API_TOKEN", None)
            with patch.dict(os.environ, env, clear=True):
                errors = connector.validate_config()
                assert any("JIRA_API_TOKEN" in e for e in errors)

    def test_missing_email(self, connector: JiraConnector) -> None:
        with patch.dict(os.environ, {"JIRA_API_TOKEN": "token"}, clear=False):
            env = os.environ.copy()
            env.pop("JIRA_EMAIL", None)
            with patch.dict(os.environ, env, clear=True):
                errors = connector.validate_config()
                assert any("JIRA_EMAIL" in e for e in errors)


class TestJiraFetch:
    @pytest.mark.asyncio
    async def test_fetch_single_issue(
        self,
        connector: JiraConnector,
        mock_jira_client: MagicMock,
    ) -> None:
        connector._client = mock_jira_client

        results = await connector.fetch("jira://PROJ-123")

        assert len(results) == 1
        assert isinstance(results[0], FetchedSource)
        assert results[0].format_hint == "jira"
        assert results[0].metadata["key"] == "PROJ-123"
        assert Path(results[0].local_path).exists()

        # Verify JSON content
        with open(results[0].local_path) as f:
            data = json.load(f)
        assert "issues" in data
        assert data["issues"][0]["key"] == "PROJ-123"

        # Cleanup
        Path(results[0].local_path).unlink()

    @pytest.mark.asyncio
    async def test_fetch_jql_query(
        self,
        connector: JiraConnector,
        mock_jira_client: MagicMock,
    ) -> None:
        connector._client = mock_jira_client

        results = await connector.fetch("jira://PROJ?jql=sprint=42")

        assert len(results) == 2
        mock_jira_client.jql.assert_called_once()
        assert results[0].metadata["key"] == "PROJ-123"
        assert results[1].metadata["key"] == "PROJ-124"

        # Cleanup
        for r in results:
            Path(r.local_path).unlink()

    @pytest.mark.asyncio
    async def test_fetch_multiple_issues(
        self,
        connector: JiraConnector,
        mock_jira_client: MagicMock,
    ) -> None:
        connector._client = mock_jira_client

        results = await connector.fetch("jira://PROJ-1,PROJ-2")

        assert len(results) == 2
        call_args = mock_jira_client.jql.call_args
        assert "key in" in call_args[0][0]

        # Cleanup
        for r in results:
            Path(r.local_path).unlink()

    @pytest.mark.asyncio
    async def test_fetch_sprint(
        self,
        connector: JiraConnector,
        mock_jira_client: MagicMock,
    ) -> None:
        connector._client = mock_jira_client

        results = await connector.fetch("jira://PROJ/sprint/42")

        assert len(results) == 2
        call_args = mock_jira_client.jql.call_args
        assert "sprint = 42" in call_args[0][0]

        # Cleanup
        for r in results:
            Path(r.local_path).unlink()

    @pytest.mark.asyncio
    async def test_fetch_api_failure(
        self,
        connector: JiraConnector,
        mock_jira_client: MagicMock,
    ) -> None:
        connector._client = mock_jira_client
        mock_jira_client.issue.side_effect = Exception("API Error")

        with pytest.raises(ConnectorError, match="Jira API call failed"):
            await connector.fetch("jira://PROJ-999")


class TestJiraTempFileError:
    @pytest.mark.asyncio
    async def test_fetch_raises_connector_error_on_temp_file_failure(
        self,
        connector: JiraConnector,
        mock_jira_client: MagicMock,
    ) -> None:
        connector._client = mock_jira_client

        with (
            patch(
                "intake.connectors.jira_api.tempfile.NamedTemporaryFile",
                side_effect=OSError("disk full"),
            ),
            pytest.raises(ConnectorError, match="Could not write temp file"),
        ):
            await connector.fetch("jira://PROJ-123")


class TestJiraEnsureClient:
    def test_import_error_gives_helpful_message(
        self,
        connector: JiraConnector,
    ) -> None:
        with (
            patch.dict(
                os.environ,
                {
                    "JIRA_API_TOKEN": "token",
                    "JIRA_EMAIL": "email@test.com",
                },
            ),
            patch(
                "intake.connectors.jira_api.JiraConnector._ensure_client",
                side_effect=ConnectorError(
                    reason="Jira connector requires atlassian-python-api.",
                    suggestion="Install with: pip install intake-ai-cli[connectors]",
                ),
            ),
            pytest.raises(ConnectorError, match="atlassian-python-api"),
        ):
            connector._ensure_client()
