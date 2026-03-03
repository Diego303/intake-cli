"""Tests for the Slack JSON export parser."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from intake.ingest.base import ParseError
from intake.ingest.slack import SlackParser

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def parser() -> SlackParser:
    return SlackParser()


@pytest.fixture
def slack_fixture(fixtures_dir: Path) -> Path:
    """Path to the Slack export JSON fixture."""
    return fixtures_dir / "slack_export.json"


class TestSlackParserCanParse:
    def test_can_parse_slack_json(self, parser: SlackParser, slack_fixture: Path) -> None:
        assert parser.can_parse(str(slack_fixture)) is True

    def test_cannot_parse_jira_json(self, parser: SlackParser, jira_fixture: Path) -> None:
        assert parser.can_parse(str(jira_fixture)) is False

    def test_cannot_parse_nonexistent(self, parser: SlackParser) -> None:
        assert parser.can_parse("/nonexistent/file.json") is False

    def test_cannot_parse_non_json(self, parser: SlackParser, tmp_path: Path) -> None:
        txt = tmp_path / "notes.txt"
        txt.write_text("not json")
        assert parser.can_parse(str(txt)) is False

    def test_cannot_parse_empty_array(self, parser: SlackParser, tmp_path: Path) -> None:
        empty = tmp_path / "empty.json"
        empty.write_text("[]")
        assert parser.can_parse(str(empty)) is False


class TestSlackParserParse:
    def test_parse_extracts_messages(self, parser: SlackParser, slack_fixture: Path) -> None:
        result = parser.parse(str(slack_fixture))
        assert result.metadata["message_count"] == "7"
        assert "notification system" in result.text
        assert "U01ALICE" in result.text

    def test_parse_identifies_threads(self, parser: SlackParser, slack_fixture: Path) -> None:
        result = parser.parse(str(slack_fixture))
        thread_count = int(result.metadata["thread_count"])
        # Fixture has 1 thread (2 replies to first message) + standalone messages
        assert thread_count >= 2
        assert result.has_structure is True

    def test_parse_detects_decisions(self, parser: SlackParser, slack_fixture: Path) -> None:
        result = parser.parse(str(slack_fixture))
        decision_count = int(result.metadata["decision_count"])
        # Fixture has: thumbsup reaction, "let's go with", "Decided:" keyword
        assert decision_count >= 2
        assert "Decisions" in result.text

    def test_parse_detects_action_items(self, parser: SlackParser, slack_fixture: Path) -> None:
        result = parser.parse(str(slack_fixture))
        action_count = int(result.metadata["action_item_count"])
        # Fixture has: "TODO" message, "Action item" message
        assert action_count >= 1
        assert "Action Items" in result.text

    def test_format_is_slack(self, parser: SlackParser, slack_fixture: Path) -> None:
        result = parser.parse(str(slack_fixture))
        assert result.format == "slack"
        assert result.metadata["source_type"] == "slack"

    def test_parse_includes_timestamps(self, parser: SlackParser, slack_fixture: Path) -> None:
        result = parser.parse(str(slack_fixture))
        # Timestamps are converted from epoch to readable format
        assert "2024-02-01" in result.text

    def test_parse_empty_messages_raises(self, parser: SlackParser, tmp_path: Path) -> None:
        bad = tmp_path / "empty_messages.json"
        bad.write_text('[{"type": "channel_join", "ts": "123"}]')
        with pytest.raises(ParseError, match="No messages found"):
            parser.parse(str(bad))

    def test_parse_invalid_json_raises(self, parser: SlackParser, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{broken json")
        with pytest.raises(ParseError, match="Invalid JSON"):
            parser.parse(str(bad))
