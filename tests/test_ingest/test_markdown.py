"""Tests for the Markdown parser."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from intake.ingest.base import ParseError
from intake.ingest.markdown import MarkdownParser

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def parser() -> MarkdownParser:
    return MarkdownParser()


class TestMarkdownParser:
    def test_can_parse_md_file(self, parser: MarkdownParser, markdown_fixture: Path) -> None:
        assert parser.can_parse(str(markdown_fixture)) is True

    def test_cannot_parse_txt_file(self, parser: MarkdownParser, plaintext_fixture: Path) -> None:
        assert parser.can_parse(str(plaintext_fixture)) is False

    def test_cannot_parse_nonexistent(self, parser: MarkdownParser) -> None:
        assert parser.can_parse("/nonexistent/file.md") is False

    def test_parse_extracts_text(self, parser: MarkdownParser, markdown_fixture: Path) -> None:
        result = parser.parse(str(markdown_fixture))
        assert result.format == "markdown"
        assert "OAuth2" in result.text
        assert "authentication" in result.text.lower()

    def test_parse_extracts_front_matter(
        self, parser: MarkdownParser, markdown_fixture: Path
    ) -> None:
        result = parser.parse(str(markdown_fixture))
        assert result.metadata.get("title") == "OAuth2 Authentication"
        assert result.metadata.get("author") == "PM Team"

    def test_parse_extracts_sections(self, parser: MarkdownParser, markdown_fixture: Path) -> None:
        result = parser.parse(str(markdown_fixture))
        assert result.has_structure is True
        titles = [s["title"] for s in result.sections]
        assert "OAuth2 Authentication System" in titles

    def test_parse_word_count(self, parser: MarkdownParser, markdown_fixture: Path) -> None:
        result = parser.parse(str(markdown_fixture))
        assert result.word_count > 50

    def test_parse_sets_source(self, parser: MarkdownParser, markdown_fixture: Path) -> None:
        result = parser.parse(str(markdown_fixture))
        assert result.source == str(markdown_fixture)

    def test_parse_nonexistent_raises(self, parser: MarkdownParser) -> None:
        with pytest.raises(ParseError, match="File not found"):
            parser.parse("/nonexistent/file.md")

    def test_parse_no_front_matter(self, parser: MarkdownParser, tmp_path: Path) -> None:
        md_file = tmp_path / "no_front_matter.md"
        md_file.write_text("# Simple\n\nJust some text.")
        result = parser.parse(str(md_file))
        assert result.metadata == {}
        assert "Simple" in result.text
