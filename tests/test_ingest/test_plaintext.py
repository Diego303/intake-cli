"""Tests for the Plaintext parser."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from intake.ingest.base import ParseError
from intake.ingest.plaintext import PlaintextParser

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def parser() -> PlaintextParser:
    return PlaintextParser()


class TestPlaintextParser:
    def test_can_parse_txt_file(
        self, parser: PlaintextParser, plaintext_fixture: Path
    ) -> None:
        assert parser.can_parse(str(plaintext_fixture)) is True

    def test_can_parse_stdin(self, parser: PlaintextParser) -> None:
        assert parser.can_parse("-") is True

    def test_cannot_parse_nonexistent(self, parser: PlaintextParser) -> None:
        assert parser.can_parse("/nonexistent/file.txt") is False

    def test_parse_extracts_text(
        self, parser: PlaintextParser, plaintext_fixture: Path
    ) -> None:
        result = parser.parse(str(plaintext_fixture))
        assert result.format == "plaintext"
        assert "password reset" in result.text.lower()

    def test_parse_extracts_paragraphs(
        self, parser: PlaintextParser, plaintext_fixture: Path
    ) -> None:
        result = parser.parse(str(plaintext_fixture))
        assert result.has_structure is True
        assert len(result.sections) > 0

    def test_parse_metadata_has_source_type(
        self, parser: PlaintextParser, plaintext_fixture: Path
    ) -> None:
        result = parser.parse(str(plaintext_fixture))
        assert result.metadata["source_type"] == "file"

    def test_parse_nonexistent_raises(self, parser: PlaintextParser) -> None:
        with pytest.raises(ParseError, match="File not found"):
            parser.parse("/nonexistent/file.txt")

    def test_parse_empty_file(self, parser: PlaintextParser, tmp_path: Path) -> None:
        from intake.ingest.base import EmptySourceError
        empty = tmp_path / "empty.txt"
        empty.write_text("")
        with pytest.raises(EmptySourceError):
            parser.parse(str(empty))
