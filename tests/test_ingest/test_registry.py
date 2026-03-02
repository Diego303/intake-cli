"""Tests for the parser registry and format auto-detection."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from intake.ingest.base import UnsupportedFormatError
from intake.ingest.registry import ParserRegistry, create_default_registry

if TYPE_CHECKING:
    from pathlib import Path


class TestParserRegistry:
    def test_detect_format_markdown(self, markdown_fixture: Path) -> None:
        registry = ParserRegistry()
        assert registry.detect_format(str(markdown_fixture)) == "markdown"

    def test_detect_format_plaintext(self, plaintext_fixture: Path) -> None:
        registry = ParserRegistry()
        assert registry.detect_format(str(plaintext_fixture)) == "plaintext"

    def test_detect_format_yaml(self, yaml_fixture: Path) -> None:
        registry = ParserRegistry()
        assert registry.detect_format(str(yaml_fixture)) == "yaml"

    def test_detect_format_stdin(self) -> None:
        registry = ParserRegistry()
        assert registry.detect_format("-") == "plaintext"

    def test_detect_format_nonexistent_falls_to_plaintext(self) -> None:
        registry = ParserRegistry()
        assert registry.detect_format("/no/file") == "plaintext"

    def test_detect_json_jira_api_format(self, jira_fixture: Path) -> None:
        registry = ParserRegistry()
        assert registry.detect_format(str(jira_fixture)) == "jira"

    def test_detect_json_jira_list_format(self, jira_multi_fixture: Path) -> None:
        registry = ParserRegistry()
        assert registry.detect_format(str(jira_multi_fixture)) == "jira"

    def test_detect_json_non_jira(self, tmp_path: Path) -> None:
        json_file = tmp_path / "plain.json"
        json_file.write_text(json.dumps({"foo": "bar"}))
        registry = ParserRegistry()
        assert registry.detect_format(str(json_file)) == "yaml"

    def test_detect_html_confluence(self, confluence_fixture: Path) -> None:
        registry = ParserRegistry()
        assert registry.detect_format(str(confluence_fixture)) == "confluence"

    def test_detect_html_non_confluence(self, tmp_path: Path) -> None:
        html_file = tmp_path / "plain.html"
        html_file.write_text("<html><body>Hello</body></html>")
        registry = ParserRegistry()
        assert registry.detect_format(str(html_file)) == "html"

    def test_detect_image(self, image_fixture: Path) -> None:
        registry = ParserRegistry()
        assert registry.detect_format(str(image_fixture)) == "image"

    def test_register_and_parse(self, markdown_fixture: Path) -> None:
        from intake.ingest.markdown import MarkdownParser

        registry = ParserRegistry()
        registry.register("markdown", MarkdownParser())
        result = registry.parse(str(markdown_fixture))
        assert result.format == "markdown"

    def test_parse_unsupported_format_without_fallback(self) -> None:
        registry = ParserRegistry()
        with pytest.raises(UnsupportedFormatError):
            registry.parse("-")

    def test_registered_formats(self) -> None:
        from intake.ingest.markdown import MarkdownParser
        from intake.ingest.plaintext import PlaintextParser

        registry = ParserRegistry()
        registry.register("markdown", MarkdownParser())
        registry.register("plaintext", PlaintextParser())
        assert "markdown" in registry.registered_formats
        assert "plaintext" in registry.registered_formats


class TestCreateDefaultRegistry:
    def test_creates_registry_with_all_parsers(self) -> None:
        registry = create_default_registry()
        expected = [
            "confluence", "docx", "image", "jira",
            "markdown", "pdf", "plaintext", "yaml",
        ]
        assert registry.registered_formats == expected

    def test_default_registry_parses_markdown(self, markdown_fixture: Path) -> None:
        registry = create_default_registry()
        result = registry.parse(str(markdown_fixture))
        assert result.format == "markdown"

    def test_default_registry_parses_jira(self, jira_fixture: Path) -> None:
        registry = create_default_registry()
        result = registry.parse(str(jira_fixture))
        assert result.format == "jira"
