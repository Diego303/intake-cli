"""Tests for GitLab API connector."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from intake.config.schema import GitlabConfig
from intake.connectors.base import ConnectorError
from intake.connectors.gitlab_api import GitlabConnector
from intake.plugins.protocols import FetchedSource, PluginMeta


@pytest.fixture
def gitlab_config() -> GitlabConfig:
    return GitlabConfig(url="https://gitlab.example.com", token_env="GITLAB_TOKEN")


@pytest.fixture
def connector(gitlab_config: GitlabConfig) -> GitlabConnector:
    return GitlabConnector(config=gitlab_config)


def _make_mock_issue(
    iid: int = 42,
    issue_id: int = 100,
    title: str = "Fix SSO login",
    description: str = "SSO login fails when using SAML.",
    state: str = "opened",
    labels: list[str] | None = None,
) -> MagicMock:
    """Create a mock python-gitlab Issue."""
    issue = MagicMock()
    issue.iid = iid
    issue.id = issue_id
    issue.title = title
    issue.description = description
    issue.state = state
    issue.labels = labels or ["bug", "priority::high"]
    issue.milestone = {"title": "v2.0"}
    issue.assignees = [{"username": "jdoe"}]
    issue.author = {"username": "admin"}
    issue.weight = 3
    issue.due_date = "2025-03-01"
    issue.created_at = "2025-01-15T10:00:00Z"
    issue.updated_at = "2025-01-16T14:00:00Z"
    issue.web_url = f"https://gitlab.example.com/group/project/-/issues/{iid}"
    issue.confidential = False
    issue.task_completion_status = {"count": 3, "completed_count": 1}

    # Notes
    note = MagicMock()
    note.author = {"username": "developer"}
    note.body = "I can reproduce this."
    note.created_at = "2025-01-15T11:00:00Z"
    note.system = False
    issue.notes = MagicMock()
    issue.notes.list.return_value = [note]

    # MRs
    issue.related_merge_requests.return_value = []

    return issue


@pytest.fixture
def mock_gitlab_client() -> MagicMock:
    """Create a mock python-gitlab client."""
    client = MagicMock()
    project = MagicMock()

    issue1 = _make_mock_issue(42, 100, "Fix SSO login")
    issue2 = _make_mock_issue(43, 101, "Add dark mode")

    project.issues.get.side_effect = lambda n: {42: issue1, 43: issue2}[n]
    project.issues.list.return_value = [issue1, issue2]

    client.projects.get.return_value = project
    return client


class TestGitlabProtocol:
    """Tests for GitlabConnector protocol conformance."""

    def test_meta(self, connector: GitlabConnector) -> None:
        meta = connector.meta
        assert isinstance(meta, PluginMeta)
        assert meta.name == "gitlab"

    def test_uri_schemes(self, connector: GitlabConnector) -> None:
        assert connector.uri_schemes == ["gitlab://"]

    def test_can_handle_gitlab_uri(self, connector: GitlabConnector) -> None:
        assert connector.can_handle("gitlab://group/project/issues/42") is True

    def test_rejects_non_gitlab_uri(self, connector: GitlabConnector) -> None:
        assert connector.can_handle("github://org/repo/issues/1") is False


class TestGitlabValidateConfig:
    """Tests for GitlabConnector.validate_config()."""

    def test_valid_config(self, connector: GitlabConnector) -> None:
        with patch.dict(os.environ, {"GITLAB_TOKEN": "glpat-test123"}):
            errors = connector.validate_config()
            assert errors == []

    def test_missing_token(self, connector: GitlabConnector) -> None:
        with patch.dict(os.environ, {}, clear=True):
            errors = connector.validate_config()
            assert len(errors) == 1
            assert "GITLAB_TOKEN" in errors[0]

    def test_missing_url(self) -> None:
        config = GitlabConfig(url="")
        conn = GitlabConnector(config=config)
        with patch.dict(os.environ, {}, clear=True):
            errors = conn.validate_config()
            assert any("URL" in e for e in errors)


class TestGitlabFetch:
    """Tests for GitlabConnector.fetch()."""

    @pytest.mark.asyncio
    async def test_fetch_single_issue(
        self,
        connector: GitlabConnector,
        mock_gitlab_client: MagicMock,
    ) -> None:
        connector._client = mock_gitlab_client

        results = await connector.fetch("gitlab://group/project/issues/42")

        assert len(results) == 1
        assert isinstance(results[0], FetchedSource)
        assert results[0].format_hint == "gitlab_issues"
        assert results[0].metadata["iid"] == "42"
        assert results[0].metadata["title"] == "Fix SSO login"
        assert results[0].metadata["source_type"] == "gitlab"

        # Verify JSON content
        with open(results[0].local_path) as f:
            data = json.load(f)
        assert data["iid"] == 42
        assert data["title"] == "Fix SSO login"

        # Cleanup
        Path(results[0].local_path).unlink()

    @pytest.mark.asyncio
    async def test_fetch_multiple_issues(
        self,
        connector: GitlabConnector,
        mock_gitlab_client: MagicMock,
    ) -> None:
        connector._client = mock_gitlab_client

        results = await connector.fetch("gitlab://group/project/issues/42,43")

        assert len(results) == 2
        assert results[0].metadata["iid"] == "42"
        assert results[1].metadata["iid"] == "43"

        # Cleanup
        for r in results:
            Path(r.local_path).unlink()

    @pytest.mark.asyncio
    async def test_fetch_filtered_issues(
        self,
        connector: GitlabConnector,
        mock_gitlab_client: MagicMock,
    ) -> None:
        connector._client = mock_gitlab_client

        results = await connector.fetch("gitlab://group/project/issues?labels=bug&state=opened")

        assert len(results) == 2

        # Cleanup
        for r in results:
            Path(r.local_path).unlink()

    @pytest.mark.asyncio
    async def test_fetch_milestone_issues(
        self,
        connector: GitlabConnector,
        mock_gitlab_client: MagicMock,
    ) -> None:
        connector._client = mock_gitlab_client

        # Setup milestone mock
        project = mock_gitlab_client.projects.get.return_value
        milestone = MagicMock()
        issue = _make_mock_issue(42, 100, "Milestone Issue")
        milestone.issues.return_value = [issue]
        project.milestones.get.return_value = milestone

        results = await connector.fetch("gitlab://group/project/milestones/3/issues")

        assert len(results) == 1

        # Cleanup
        for r in results:
            Path(r.local_path).unlink()

    @pytest.mark.asyncio
    async def test_fetch_project_not_found(
        self,
        connector: GitlabConnector,
        mock_gitlab_client: MagicMock,
    ) -> None:
        connector._client = mock_gitlab_client
        mock_gitlab_client.projects.get.side_effect = Exception("Not Found")

        with pytest.raises(ConnectorError, match="Could not access"):
            await connector.fetch("gitlab://org/nonexistent/issues/1")


class TestGitlabParseUri:
    """Tests for URI parsing."""

    def test_simple_uri(self, connector: GitlabConnector) -> None:
        path, params = connector._parse_uri("gitlab://group/project/issues/42")
        assert path == "group/project/issues/42"
        assert params == {}

    def test_uri_with_params(self, connector: GitlabConnector) -> None:
        path, params = connector._parse_uri("gitlab://group/project/issues?labels=bug&state=opened")
        assert path == "group/project/issues"
        assert params == {"labels": "bug", "state": "opened"}

    def test_nested_group_uri(self, connector: GitlabConnector) -> None:
        path, params = connector._parse_uri("gitlab://org/team/subgroup/project/issues/10")
        assert path == "org/team/subgroup/project/issues/10"
        assert params == {}


class TestGitlabSplitProject:
    """Tests for _split_project_resource()."""

    def test_simple_project_issues(self, connector: GitlabConnector) -> None:
        parts = ["group", "project", "issues", "42"]
        project, resource = connector._split_project_resource(parts)
        assert project == "group/project"
        assert resource == "issues/42"

    def test_nested_group(self, connector: GitlabConnector) -> None:
        parts = ["org", "team", "subgroup", "project", "issues", "10"]
        project, resource = connector._split_project_resource(parts)
        assert project == "org/team/subgroup/project"
        assert resource == "issues/10"

    def test_milestones_resource(self, connector: GitlabConnector) -> None:
        parts = ["group", "project", "milestones", "3", "issues"]
        project, resource = connector._split_project_resource(parts)
        assert project == "group/project"
        assert resource == "milestones/3/issues"

    def test_invalid_uri_raises_error(self, connector: GitlabConnector) -> None:
        parts = ["group", "project", "unknown"]
        with pytest.raises(ConnectorError, match="Could not parse"):
            connector._split_project_resource(parts)


class TestGitlabIssueToDict:
    """Tests for _issue_to_dict() serialization."""

    def test_serializes_basic_fields(self, connector: GitlabConnector) -> None:
        mock_issue = _make_mock_issue(
            iid=99,
            title="Test serialization",
            description="Some body text",
            labels=["feature"],
        )
        result = connector._issue_to_dict(mock_issue, "group/project")

        assert result["iid"] == 99
        assert result["title"] == "Test serialization"
        assert result["description"] == "Some body text"
        assert result["state"] == "opened"
        assert result["labels"] == ["feature"]
        assert result["_project_path"] == "group/project"

    def test_serializes_notes(self, connector: GitlabConnector) -> None:
        mock_issue = _make_mock_issue()
        result = connector._issue_to_dict(mock_issue, "group/project")

        assert "notes" in result
        assert len(result["notes"]) == 1
        assert result["notes"][0]["author"] == "developer"

    def test_serializes_milestone(self, connector: GitlabConnector) -> None:
        mock_issue = _make_mock_issue()
        result = connector._issue_to_dict(mock_issue, "group/project")

        assert result["milestone"] == "v2.0"

    def test_serializes_assignees(self, connector: GitlabConnector) -> None:
        mock_issue = _make_mock_issue()
        result = connector._issue_to_dict(mock_issue, "group/project")

        assert result["assignees"] == ["jdoe"]


class TestGitlabEnsureClient:
    """Tests for client initialization errors."""

    def test_missing_python_gitlab_raises_error(self, connector: GitlabConnector) -> None:
        with (
            patch.dict(os.environ, {"GITLAB_TOKEN": "test"}),
            patch.dict("sys.modules", {"gitlab": None}),
            pytest.raises(ConnectorError, match="python-gitlab"),
        ):
            connector._ensure_client()

    def test_missing_token_raises_error(self, connector: GitlabConnector) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("builtins.__import__", side_effect=ImportError("no gitlab")),
            pytest.raises(ConnectorError),
        ):
            connector._ensure_client()


class TestGitlabTempFileError:
    """Tests for temp file write failure."""

    @pytest.mark.asyncio
    async def test_fetch_raises_on_temp_file_failure(
        self,
        connector: GitlabConnector,
        mock_gitlab_client: MagicMock,
    ) -> None:
        connector._client = mock_gitlab_client

        with (
            patch(
                "intake.connectors.gitlab_api.tempfile.NamedTemporaryFile",
                side_effect=OSError("disk full"),
            ),
            pytest.raises(ConnectorError, match="Could not write temp file"),
        ):
            await connector.fetch("gitlab://group/project/issues/42")
