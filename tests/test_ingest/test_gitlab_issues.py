"""Tests for the GitLab Issues JSON parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from intake.ingest.base import ParseError
from intake.ingest.gitlab_issues import GitlabIssuesParser

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def parser() -> GitlabIssuesParser:
    """Create a GitlabIssuesParser instance."""
    return GitlabIssuesParser()


@pytest.fixture
def single_issue_path() -> Path:
    """Path to a single GitLab issue fixture."""
    return FIXTURES_DIR / "gitlab_issue_single.json"


@pytest.fixture
def multi_issues_path() -> Path:
    """Path to multiple GitLab issues fixture."""
    return FIXTURES_DIR / "gitlab_issues.json"


class TestCanParse:
    """Tests for GitlabIssuesParser.can_parse()."""

    def test_accepts_single_gitlab_issue(
        self, parser: GitlabIssuesParser, single_issue_path: Path
    ) -> None:
        assert parser.can_parse(str(single_issue_path)) is True

    def test_accepts_multiple_gitlab_issues(
        self, parser: GitlabIssuesParser, multi_issues_path: Path
    ) -> None:
        assert parser.can_parse(str(multi_issues_path)) is True

    def test_rejects_non_json_file(self, parser: GitlabIssuesParser, tmp_path: Path) -> None:
        txt_file = tmp_path / "notes.txt"
        txt_file.write_text("some text")
        assert parser.can_parse(str(txt_file)) is False

    def test_rejects_nonexistent_file(self, parser: GitlabIssuesParser) -> None:
        assert parser.can_parse("/nonexistent/file.json") is False

    def test_rejects_github_issues_json(self, parser: GitlabIssuesParser, tmp_path: Path) -> None:
        """GitHub issues have 'number' not 'iid'."""
        github_file = tmp_path / "github.json"
        github_file.write_text('[{"number": 1, "title": "Test", "labels": []}]')
        assert parser.can_parse(str(github_file)) is False

    def test_rejects_empty_json_array(self, parser: GitlabIssuesParser, tmp_path: Path) -> None:
        empty_file = tmp_path / "empty.json"
        empty_file.write_text("[]")
        assert parser.can_parse(str(empty_file)) is False


class TestParse:
    """Tests for GitlabIssuesParser.parse()."""

    def test_parses_single_issue(self, parser: GitlabIssuesParser, single_issue_path: Path) -> None:
        result = parser.parse(str(single_issue_path))
        assert result.format == "gitlab_issues"
        assert result.metadata["issue_count"] == "1"
        assert result.metadata["source_type"] == "gitlab"
        assert result.metadata["project"] == "mygroup/myproject"
        assert len(result.sections) == 1
        assert "#42" in result.sections[0]["title"]

    def test_parses_multiple_issues(
        self, parser: GitlabIssuesParser, multi_issues_path: Path
    ) -> None:
        result = parser.parse(str(multi_issues_path))
        assert result.format == "gitlab_issues"
        assert result.metadata["issue_count"] == "3"
        assert len(result.sections) == 3

    def test_extracts_labels(self, parser: GitlabIssuesParser, single_issue_path: Path) -> None:
        result = parser.parse(str(single_issue_path))
        assert "bug" in result.text
        assert "priority::high" in result.text
        assert "SSO" in result.text

    def test_extracts_milestone(self, parser: GitlabIssuesParser, single_issue_path: Path) -> None:
        result = parser.parse(str(single_issue_path))
        assert "v2.0" in result.text

    def test_extracts_assignees(self, parser: GitlabIssuesParser, single_issue_path: Path) -> None:
        result = parser.parse(str(single_issue_path))
        assert "jdoe" in result.text
        assert "asmith" in result.text

    def test_extracts_discussion_notes(
        self, parser: GitlabIssuesParser, single_issue_path: Path
    ) -> None:
        result = parser.parse(str(single_issue_path))
        assert "Discussion" in result.text
        assert "OAuth callback handler" in result.text

    def test_extracts_merge_request_relations(
        self, parser: GitlabIssuesParser, single_issue_path: Path
    ) -> None:
        result = parser.parse(str(single_issue_path))
        assert len(result.relations) == 1
        assert result.relations[0]["type"] == "merge_request"
        assert result.relations[0]["target"] == "!101"

    def test_extracts_task_completion_status(
        self, parser: GitlabIssuesParser, single_issue_path: Path
    ) -> None:
        result = parser.parse(str(single_issue_path))
        assert "1/3 completed" in result.text

    def test_extracts_weight(self, parser: GitlabIssuesParser, single_issue_path: Path) -> None:
        result = parser.parse(str(single_issue_path))
        assert "Weight" in result.text

    def test_has_structure(self, parser: GitlabIssuesParser, single_issue_path: Path) -> None:
        result = parser.parse(str(single_issue_path))
        assert result.has_structure is True

    def test_raises_on_invalid_json(self, parser: GitlabIssuesParser, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{invalid json")
        with pytest.raises(ParseError, match="Invalid JSON"):
            parser.parse(str(bad_file))

    def test_raises_on_no_issues(self, parser: GitlabIssuesParser, tmp_path: Path) -> None:
        empty_file = tmp_path / "empty.json"
        empty_file.write_text('{"other": "data"}')
        with pytest.raises(ParseError, match="No GitLab issues found"):
            parser.parse(str(empty_file))

    def test_wrapped_format(self, parser: GitlabIssuesParser, tmp_path: Path) -> None:
        """Test {"issues": [...]} format from connector."""
        wrapped = tmp_path / "wrapped.json"
        wrapped.write_text(
            '{"issues": [{"iid": 10, "title": "Wrapped Issue", '
            '"description": "Test", "state": "opened"}]}'
        )
        result = parser.parse(str(wrapped))
        assert result.metadata["issue_count"] == "1"
        assert "Wrapped Issue" in result.text
