"""Tests for GitHub API connector."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from intake.config.schema import GithubConfig
from intake.connectors.base import ConnectorError
from intake.connectors.github_api import GithubConnector
from intake.plugins.protocols import FetchedSource, PluginMeta


@pytest.fixture
def github_config() -> GithubConfig:
    return GithubConfig(token_env="GITHUB_TOKEN")


@pytest.fixture
def connector(github_config: GithubConfig) -> GithubConnector:
    return GithubConnector(config=github_config)


def _make_mock_issue(
    number: int = 42,
    title: str = "Fix login bug",
    body: str = "The login form crashes on submit.",
    state: str = "open",
    labels: list[str] | None = None,
) -> MagicMock:
    """Create a mock PyGithub Issue."""
    issue = MagicMock()
    issue.number = number
    issue.title = title
    issue.body = body
    issue.state = state
    issue.created_at = "2025-01-15T10:00:00Z"
    issue.updated_at = "2025-01-16T14:00:00Z"
    issue.milestone = None
    issue.assignees = []

    mock_label = MagicMock()
    mock_label.name = labels[0] if labels else "bug"
    issue.labels = [mock_label] if labels else []

    comment = MagicMock()
    comment.user = MagicMock()
    comment.user.login = "developer"
    comment.body = "I can reproduce this."
    comment.created_at = "2025-01-15T11:00:00Z"
    issue.get_comments.return_value = [comment]

    return issue


@pytest.fixture
def mock_github_client() -> MagicMock:
    """Create a mock PyGithub client."""
    client = MagicMock()
    repo = MagicMock()

    issue1 = _make_mock_issue(42, "Fix login bug")
    issue2 = _make_mock_issue(43, "Add dark mode")

    repo.get_issue.side_effect = lambda n: {42: issue1, 43: issue2}.get(n, issue1)
    repo.get_issues.return_value = [issue1, issue2]
    repo.get_label.return_value = MagicMock(name="bug")
    repo.get_milestones.return_value = []

    client.get_repo.return_value = repo
    return client


class TestGithubProtocol:
    def test_meta(self, connector: GithubConnector) -> None:
        meta = connector.meta
        assert isinstance(meta, PluginMeta)
        assert meta.name == "github"

    def test_uri_schemes(self, connector: GithubConnector) -> None:
        assert connector.uri_schemes == ["github://"]

    def test_can_handle(self, connector: GithubConnector) -> None:
        assert connector.can_handle("github://org/repo/issues/42") is True
        assert connector.can_handle("jira://PROJ-123") is False


class TestGithubValidateConfig:
    def test_valid_config(self, connector: GithubConnector) -> None:
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test123"}):
            errors = connector.validate_config()
            assert errors == []

    def test_missing_token(self, connector: GithubConnector) -> None:
        env = {}
        with patch.dict(os.environ, env, clear=True):
            errors = connector.validate_config()
            assert len(errors) == 1
            assert "GITHUB_TOKEN" in errors[0]


class TestGithubFetch:
    @pytest.mark.asyncio
    async def test_fetch_single_issue(
        self,
        connector: GithubConnector,
        mock_github_client: MagicMock,
    ) -> None:
        connector._client = mock_github_client

        results = await connector.fetch("github://org/repo/issues/42")

        assert len(results) == 1
        assert isinstance(results[0], FetchedSource)
        assert results[0].format_hint == "github_issues"
        assert results[0].metadata["number"] == "42"
        assert results[0].metadata["title"] == "Fix login bug"

        # Verify JSON content
        with open(results[0].local_path) as f:
            data = json.load(f)
        assert data["number"] == 42
        assert data["title"] == "Fix login bug"
        assert len(data["comments"]) == 1

        # Cleanup
        Path(results[0].local_path).unlink()

    @pytest.mark.asyncio
    async def test_fetch_multiple_issues(
        self,
        connector: GithubConnector,
        mock_github_client: MagicMock,
    ) -> None:
        connector._client = mock_github_client

        results = await connector.fetch("github://org/repo/issues/42,43")

        assert len(results) == 2
        assert results[0].metadata["number"] == "42"
        assert results[1].metadata["number"] == "43"

        # Cleanup
        for r in results:
            Path(r.local_path).unlink()

    @pytest.mark.asyncio
    async def test_fetch_filtered_issues(
        self,
        connector: GithubConnector,
        mock_github_client: MagicMock,
    ) -> None:
        connector._client = mock_github_client

        results = await connector.fetch("github://org/repo/issues?labels=bug&state=open")

        assert len(results) == 2

        # Cleanup
        for r in results:
            Path(r.local_path).unlink()

    @pytest.mark.asyncio
    async def test_fetch_invalid_uri(
        self,
        connector: GithubConnector,
        mock_github_client: MagicMock,
    ) -> None:
        connector._client = mock_github_client

        with pytest.raises(ConnectorError, match="Invalid GitHub URI"):
            await connector.fetch("github://incomplete")

    @pytest.mark.asyncio
    async def test_fetch_repo_not_found(
        self,
        connector: GithubConnector,
        mock_github_client: MagicMock,
    ) -> None:
        connector._client = mock_github_client
        mock_github_client.get_repo.side_effect = Exception("Not Found")

        with pytest.raises(ConnectorError, match="Could not access repository"):
            await connector.fetch("github://org/nonexistent/issues/1")


class TestGithubTempFileError:
    @pytest.mark.asyncio
    async def test_fetch_raises_connector_error_on_temp_file_failure(
        self,
        connector: GithubConnector,
        mock_github_client: MagicMock,
    ) -> None:
        connector._client = mock_github_client

        with (
            patch(
                "intake.connectors.github_api.tempfile.NamedTemporaryFile",
                side_effect=OSError("disk full"),
            ),
            pytest.raises(ConnectorError, match="Could not write temp file"),
        ):
            await connector.fetch("github://org/repo/issues/42")


class TestGithubIssueToDict:
    def test_serialization(self, connector: GithubConnector) -> None:
        mock_issue = _make_mock_issue(
            number=99,
            title="Test serialization",
            body="Some body text",
            labels=["feature"],
        )
        result = connector._issue_to_dict(mock_issue)

        assert result["number"] == 99
        assert result["title"] == "Test serialization"
        assert result["body"] == "Some body text"
        assert result["state"] == "open"
        assert len(result["comments"]) == 1
        assert result["comments"][0]["author"] == "developer"
