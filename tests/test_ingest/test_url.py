"""Tests for the URL parser."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import httpx
import pytest

from intake.ingest.base import ParseError
from intake.ingest.url import UrlParser

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def parser() -> UrlParser:
    return UrlParser()


@pytest.fixture
def sample_html(fixtures_dir: Path) -> str:
    """Read the sample webpage HTML fixture."""
    return (fixtures_dir / "sample_webpage.html").read_text(encoding="utf-8")


def _make_mock_response(
    text: str,
    content_type: str = "text/html; charset=utf-8",
    status_code: int = 200,
) -> MagicMock:
    """Create a mock httpx.Response object."""
    response = MagicMock(spec=httpx.Response)
    response.text = text
    response.status_code = status_code
    response.headers = {"content-type": content_type}
    response.raise_for_status = MagicMock()
    return response


class TestUrlParserCanParse:
    def test_can_parse_http_url(self, parser: UrlParser) -> None:
        assert parser.can_parse("http://example.com/docs") is True

    def test_can_parse_https_url(self, parser: UrlParser) -> None:
        assert parser.can_parse("https://example.com/api/docs") is True

    def test_cannot_parse_local_file(self, parser: UrlParser) -> None:
        assert parser.can_parse("/home/user/file.html") is False

    def test_cannot_parse_ftp_url(self, parser: UrlParser) -> None:
        assert parser.can_parse("ftp://files.example.com/doc.pdf") is False

    def test_cannot_parse_empty_string(self, parser: UrlParser) -> None:
        assert parser.can_parse("") is False

    def test_can_parse_url_with_whitespace(self, parser: UrlParser) -> None:
        assert parser.can_parse("  https://example.com  ") is True


class TestUrlParserParse:
    @patch("intake.ingest.url.httpx.get")
    def test_parse_html_page(
        self, mock_get: MagicMock, parser: UrlParser, sample_html: str
    ) -> None:
        mock_get.return_value = _make_mock_response(sample_html)

        result = parser.parse("https://example.com/docs")

        assert result.format == "url"
        assert result.metadata["url"] == "https://example.com/docs"
        assert "title" in result.metadata
        assert "API Documentation" in result.metadata["title"]

    @patch("intake.ingest.url.httpx.get")
    def test_parse_extracts_sections_from_headings(
        self, mock_get: MagicMock, parser: UrlParser, sample_html: str
    ) -> None:
        mock_get.return_value = _make_mock_response(sample_html)

        result = parser.parse("https://example.com/docs")

        assert result.has_structure is True
        titles = [s["title"] for s in result.sections]
        assert any("Authentication" in t for t in titles)
        assert any("Endpoints" in t for t in titles)
        assert any("Error Handling" in t for t in titles)

    @patch("intake.ingest.url.httpx.get")
    def test_parse_plain_text_response(self, mock_get: MagicMock, parser: UrlParser) -> None:
        mock_get.return_value = _make_mock_response(
            "This is a plain text document.\nLine two.",
            content_type="text/plain",
        )

        result = parser.parse("https://example.com/readme.txt")

        assert result.format == "url"
        assert "plain text document" in result.text

    @patch("intake.ingest.url.httpx.get")
    def test_parse_handles_connection_error(self, mock_get: MagicMock, parser: UrlParser) -> None:
        mock_get.side_effect = httpx.ConnectError("Connection refused")

        with pytest.raises(ParseError, match="Could not connect"):
            parser.parse("https://unreachable.example.com/page")

    @patch("intake.ingest.url.httpx.get")
    def test_parse_detects_github_source_type(
        self, mock_get: MagicMock, parser: UrlParser, sample_html: str
    ) -> None:
        mock_get.return_value = _make_mock_response(sample_html)

        result = parser.parse("https://github.com/org/repo/wiki/Design")

        assert result.metadata["source_type"] == "github"

    @patch("intake.ingest.url.httpx.get")
    def test_parse_detects_confluence_source_type(
        self, mock_get: MagicMock, parser: UrlParser, sample_html: str
    ) -> None:
        mock_get.return_value = _make_mock_response(sample_html)

        result = parser.parse("https://myteam.atlassian.net/wiki/spaces/PROJ/page")

        assert result.metadata["source_type"] == "confluence"

    @patch("intake.ingest.url.httpx.get")
    def test_parse_handles_timeout(self, mock_get: MagicMock, parser: UrlParser) -> None:
        mock_get.side_effect = httpx.ReadTimeout("read timed out")

        with pytest.raises(ParseError, match="timed out"):
            parser.parse("https://slow.example.com/page")

    @patch("intake.ingest.url.httpx.get")
    def test_parse_empty_page_raises(self, mock_get: MagicMock, parser: UrlParser) -> None:
        mock_get.return_value = _make_mock_response(
            "<html><body></body></html>",
            content_type="text/html",
        )

        with pytest.raises(ParseError, match="no extractable text"):
            parser.parse("https://example.com/empty")
