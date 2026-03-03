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


class TestJsonSubtypeDetection:
    def test_detect_slack_export(self, tmp_path: Path) -> None:
        """JSON with message objects is detected as slack."""
        slack_file = tmp_path / "export.json"
        slack_file.write_text(
            json.dumps(
                [
                    {"type": "message", "user": "U1", "text": "hello", "ts": "1700000000.000"},
                ]
            )
        )
        registry = ParserRegistry()
        assert registry.detect_format(str(slack_file)) == "slack"

    def test_detect_github_issues_list(self, tmp_path: Path) -> None:
        """JSON with issue objects is detected as github_issues."""
        issues_file = tmp_path / "issues.json"
        issues_file.write_text(
            json.dumps(
                [
                    {
                        "number": 1,
                        "title": "Bug",
                        "html_url": "https://github.com/org/repo/issues/1",
                    },
                ]
            )
        )
        registry = ParserRegistry()
        assert registry.detect_format(str(issues_file)) == "github_issues"

    def test_detect_github_single_issue(self, tmp_path: Path) -> None:
        """Single GitHub issue object is detected as github_issues."""
        issue_file = tmp_path / "issue.json"
        issue_file.write_text(
            json.dumps(
                {
                    "number": 42,
                    "title": "Feature",
                    "html_url": "https://github.com/org/repo/issues/42",
                }
            )
        )
        registry = ParserRegistry()
        assert registry.detect_format(str(issue_file)) == "github_issues"

    def test_detect_github_issues_by_labels(self, tmp_path: Path) -> None:
        """GitHub issues with title + labels (no html_url) are detected."""
        issues_file = tmp_path / "issues.json"
        issues_file.write_text(
            json.dumps(
                [
                    {"number": 1, "title": "Bug", "labels": ["bug"]},
                ]
            )
        )
        registry = ParserRegistry()
        assert registry.detect_format(str(issues_file)) == "github_issues"

    def test_jira_takes_priority_over_github(self, tmp_path: Path) -> None:
        """Jira format (key + fields) takes priority over GitHub."""
        jira_file = tmp_path / "data.json"
        jira_file.write_text(
            json.dumps(
                [
                    {"key": "PROJ-1", "fields": {"summary": "Task"}, "number": 1},
                ]
            )
        )
        registry = ParserRegistry()
        assert registry.detect_format(str(jira_file)) == "jira"


class TestCreateDefaultRegistry:
    def test_creates_registry_with_all_parsers(self) -> None:
        registry = create_default_registry()
        expected = [
            "confluence",
            "docx",
            "github_issues",
            "image",
            "jira",
            "markdown",
            "pdf",
            "plaintext",
            "slack",
            "url",
            "yaml",
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

    def test_plugin_discovery_finds_parsers(self) -> None:
        """Plugin discovery via entry_points finds all built-in parsers."""
        registry = create_default_registry(use_plugins=True)
        assert len(registry.registered_formats) >= 11
        assert "markdown" in registry.registered_formats
        assert "slack" in registry.registered_formats
        assert "github_issues" in registry.registered_formats
        assert "url" in registry.registered_formats

    def test_manual_fallback_works(self) -> None:
        """Manual fallback creates the same set of parsers."""
        registry = create_default_registry(use_plugins=False)
        expected = [
            "confluence",
            "docx",
            "github_issues",
            "image",
            "jira",
            "markdown",
            "pdf",
            "plaintext",
            "slack",
            "url",
            "yaml",
        ]
        assert registry.registered_formats == expected

    def test_plugin_and_manual_produce_same_formats(self) -> None:
        """Plugin discovery and manual registration produce the same formats."""
        plugin_registry = create_default_registry(use_plugins=True)
        manual_registry = create_default_registry(use_plugins=False)
        assert plugin_registry.registered_formats == manual_registry.registered_formats
