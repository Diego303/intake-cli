"""Tests for the Confluence HTML export parser."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from intake.ingest.confluence import ConfluenceParser

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def parser() -> ConfluenceParser:
    return ConfluenceParser()


class TestConfluenceParser:
    def test_can_parse_confluence_html(
        self, parser: ConfluenceParser, confluence_fixture: Path
    ) -> None:
        assert parser.can_parse(str(confluence_fixture)) is True

    def test_cannot_parse_non_confluence_html(
        self, parser: ConfluenceParser, tmp_path: Path
    ) -> None:
        html = tmp_path / "plain.html"
        html.write_text("<html><body><h1>Hello</h1></body></html>")
        assert parser.can_parse(str(html)) is False

    def test_cannot_parse_nonexistent(self, parser: ConfluenceParser) -> None:
        assert parser.can_parse("/nonexistent/file.html") is False

    def test_parse_extracts_text(self, parser: ConfluenceParser, confluence_fixture: Path) -> None:
        result = parser.parse(str(confluence_fixture))
        assert result.format == "confluence"
        assert "Authentication" in result.text
        assert "OAuth2" in result.text

    def test_parse_extracts_title(self, parser: ConfluenceParser, confluence_fixture: Path) -> None:
        result = parser.parse(str(confluence_fixture))
        assert "title" in result.metadata

    def test_parse_extracts_sections(
        self, parser: ConfluenceParser, confluence_fixture: Path
    ) -> None:
        result = parser.parse(str(confluence_fixture))
        assert result.has_structure is True
        titles = [s["title"] for s in result.sections]
        assert any("Overview" in t for t in titles)
        assert any("Security" in t for t in titles)

    def test_parse_extracts_metadata(
        self, parser: ConfluenceParser, confluence_fixture: Path
    ) -> None:
        result = parser.parse(str(confluence_fixture))
        assert result.metadata["source_type"] == "confluence"
        assert "author" in result.metadata

    def test_parse_converts_tables(
        self, parser: ConfluenceParser, confluence_fixture: Path
    ) -> None:
        result = parser.parse(str(confluence_fixture))
        # Tables should be converted to Markdown
        assert "Component" in result.text or "Auth Server" in result.text
