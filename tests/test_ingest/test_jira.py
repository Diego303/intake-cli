"""Tests for the Jira JSON export parser."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from intake.ingest.jira import JiraParser

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def parser() -> JiraParser:
    return JiraParser()


class TestJiraParser:
    def test_can_parse_jira_api_format(
        self, parser: JiraParser, jira_fixture: Path
    ) -> None:
        assert parser.can_parse(str(jira_fixture)) is True

    def test_can_parse_jira_list_format(
        self, parser: JiraParser, jira_multi_fixture: Path
    ) -> None:
        assert parser.can_parse(str(jira_multi_fixture)) is True

    def test_cannot_parse_non_jira_json(
        self, parser: JiraParser, tmp_path: Path
    ) -> None:
        plain_json = tmp_path / "plain.json"
        plain_json.write_text('{"foo": "bar"}')
        assert parser.can_parse(str(plain_json)) is False

    def test_cannot_parse_nonexistent(self, parser: JiraParser) -> None:
        assert parser.can_parse("/nonexistent/file.json") is False

    def test_parse_api_format_extracts_issues(
        self, parser: JiraParser, jira_fixture: Path
    ) -> None:
        result = parser.parse(str(jira_fixture))
        assert result.format == "jira"
        assert result.metadata["issue_count"] == "3"
        assert result.has_structure is True
        assert len(result.sections) == 3

    def test_parse_extracts_issue_keys(
        self, parser: JiraParser, jira_fixture: Path
    ) -> None:
        result = parser.parse(str(jira_fixture))
        titles = [s["title"] for s in result.sections]
        assert any("AUTH-101" in t for t in titles)
        assert any("AUTH-102" in t for t in titles)
        assert any("AUTH-103" in t for t in titles)

    def test_parse_extracts_comments(
        self, parser: JiraParser, jira_fixture: Path
    ) -> None:
        result = parser.parse(str(jira_fixture))
        assert "John PM" in result.text
        assert "CSRF" in result.text

    def test_parse_extracts_relations(
        self, parser: JiraParser, jira_fixture: Path
    ) -> None:
        result = parser.parse(str(jira_fixture))
        assert len(result.relations) > 0
        targets = [r["target"] for r in result.relations]
        assert "AUTH-103" in targets

    def test_parse_list_format(
        self, parser: JiraParser, jira_multi_fixture: Path
    ) -> None:
        result = parser.parse(str(jira_multi_fixture))
        assert result.format == "jira"
        assert result.metadata["issue_count"] == "2"
        assert "PAY-001" in result.text
        assert "PAY-002" in result.text

    def test_parse_preserves_priority(
        self, parser: JiraParser, jira_fixture: Path
    ) -> None:
        result = parser.parse(str(jira_fixture))
        assert "High" in result.text
        assert "Medium" in result.text
