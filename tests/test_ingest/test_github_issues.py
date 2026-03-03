"""Tests for the GitHub Issues JSON parser."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from intake.ingest.base import ParseError
from intake.ingest.github_issues import GithubIssuesParser

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def parser() -> GithubIssuesParser:
    return GithubIssuesParser()


@pytest.fixture
def github_issues_fixture(fixtures_dir: Path) -> Path:
    """Path to the GitHub Issues JSON fixture."""
    return fixtures_dir / "github_issues.json"


class TestGithubIssuesParserCanParse:
    def test_can_parse_github_issues(
        self, parser: GithubIssuesParser, github_issues_fixture: Path
    ) -> None:
        assert parser.can_parse(str(github_issues_fixture)) is True

    def test_cannot_parse_jira_json(self, parser: GithubIssuesParser, jira_fixture: Path) -> None:
        assert parser.can_parse(str(jira_fixture)) is False

    def test_cannot_parse_nonexistent(self, parser: GithubIssuesParser) -> None:
        assert parser.can_parse("/nonexistent/file.json") is False

    def test_cannot_parse_non_json(self, parser: GithubIssuesParser, tmp_path: Path) -> None:
        txt = tmp_path / "notes.txt"
        txt.write_text("not json")
        assert parser.can_parse(str(txt)) is False

    def test_can_parse_single_issue(self, parser: GithubIssuesParser, tmp_path: Path) -> None:
        single = tmp_path / "single_issue.json"
        single.write_text(
            '{"number": 1, "title": "Bug", "labels": [], "html_url": "https://github.com/x/y/1"}'
        )
        assert parser.can_parse(str(single)) is True


class TestGithubIssuesParserParse:
    def test_parse_extracts_issue_count(
        self, parser: GithubIssuesParser, github_issues_fixture: Path
    ) -> None:
        result = parser.parse(str(github_issues_fixture))
        assert result.metadata["issue_count"] == "3"
        assert result.has_structure is True
        assert len(result.sections) == 3

    def test_parse_extracts_labels(
        self, parser: GithubIssuesParser, github_issues_fixture: Path
    ) -> None:
        result = parser.parse(str(github_issues_fixture))
        labels = result.metadata.get("labels", "")
        assert "enhancement" in labels
        assert "bug" in labels
        assert "api" in labels
        assert "critical" in labels

    def test_parse_extracts_cross_references(
        self, parser: GithubIssuesParser, github_issues_fixture: Path
    ) -> None:
        result = parser.parse(str(github_issues_fixture))
        assert len(result.relations) > 0
        targets = [r["target"] for r in result.relations]
        assert "#42" in targets
        assert "#10" in targets

    def test_parse_includes_comments(
        self, parser: GithubIssuesParser, github_issues_fixture: Path
    ) -> None:
        result = parser.parse(str(github_issues_fixture))
        assert "bob-reviewer" in result.text
        assert "cursor-based pagination" in result.text
        assert "dave-dba" in result.text

    def test_format_is_github_issues(
        self, parser: GithubIssuesParser, github_issues_fixture: Path
    ) -> None:
        result = parser.parse(str(github_issues_fixture))
        assert result.format == "github_issues"
        assert result.metadata["source_type"] == "github_issues"

    def test_parse_extracts_milestone(
        self, parser: GithubIssuesParser, github_issues_fixture: Path
    ) -> None:
        result = parser.parse(str(github_issues_fixture))
        assert result.metadata.get("milestone") == "v2.0 Release"

    def test_parse_extracts_assignees(
        self, parser: GithubIssuesParser, github_issues_fixture: Path
    ) -> None:
        result = parser.parse(str(github_issues_fixture))
        assert "alice-dev" in result.text
        assert "carol-backend" in result.text

    def test_parse_extracts_issue_state(
        self, parser: GithubIssuesParser, github_issues_fixture: Path
    ) -> None:
        result = parser.parse(str(github_issues_fixture))
        assert "open" in result.text

    def test_parse_single_issue(self, parser: GithubIssuesParser, tmp_path: Path) -> None:
        single = tmp_path / "one_issue.json"
        single.write_text(
            '{"number": 99, "title": "Single bug", "body": "Fix this", '
            '"labels": [{"name": "bug"}], "state": "open", "assignees": [], '
            '"html_url": "https://github.com/x/y/99", "comments_data": []}'
        )
        result = parser.parse(str(single))
        assert result.metadata["issue_count"] == "1"
        assert "#99" in result.sections[0]["title"]

    def test_parse_no_issues_raises(self, parser: GithubIssuesParser, tmp_path: Path) -> None:
        bad = tmp_path / "no_issues.json"
        bad.write_text('{"some": "data"}')
        with pytest.raises(ParseError, match="No GitHub issues"):
            parser.parse(str(bad))

    def test_parse_invalid_json_raises(self, parser: GithubIssuesParser, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{broken json")
        with pytest.raises(ParseError, match="Invalid JSON"):
            parser.parse(str(bad))
