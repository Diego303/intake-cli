"""Tests for source URI parsing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from intake.utils.source_uri import SourceURI, parse_source

if TYPE_CHECKING:
    from pathlib import Path


class TestParseSource:
    def test_parse_stdin(self) -> None:
        uri = parse_source("-")
        assert uri.type == "stdin"
        assert uri.raw == "-"

    def test_parse_jira_single_issue(self) -> None:
        uri = parse_source("jira://PROJ-123")
        assert uri.type == "jira"
        assert uri.path == "PROJ-123"
        assert uri.params == {}

    def test_parse_jira_with_jql(self) -> None:
        uri = parse_source("jira://PROJ?jql=sprint%3D42")
        assert uri.type == "jira"
        assert uri.path == "PROJ"
        assert uri.params == {"jql": "sprint%3D42"}

    def test_parse_jira_multiple_issues(self) -> None:
        uri = parse_source("jira://PROJ-1,PROJ-2,PROJ-3")
        assert uri.type == "jira"
        assert uri.path == "PROJ-1,PROJ-2,PROJ-3"

    def test_parse_confluence_page_by_title(self) -> None:
        uri = parse_source("confluence://ENG/Auth-RFC")
        assert uri.type == "confluence"
        assert uri.path == "ENG/Auth-RFC"

    def test_parse_confluence_page_by_id(self) -> None:
        uri = parse_source("confluence://page/123456")
        assert uri.type == "confluence"
        assert uri.path == "page/123456"

    def test_parse_github_single_issue(self) -> None:
        uri = parse_source("github://org/repo/issues/42")
        assert uri.type == "github"
        assert uri.path == "org/repo/issues/42"

    def test_parse_github_filtered_issues(self) -> None:
        uri = parse_source("github://org/repo/issues?labels=bug&state=open")
        assert uri.type == "github"
        assert uri.path == "org/repo/issues"
        assert uri.params == {"labels": "bug", "state": "open"}

    def test_parse_http_url(self) -> None:
        uri = parse_source("https://wiki.company.com/rfc/auth")
        assert uri.type == "url"
        assert uri.path == "https://wiki.company.com/rfc/auth"

    def test_parse_http_url_without_s(self) -> None:
        uri = parse_source("http://example.com/page")
        assert uri.type == "url"

    def test_parse_existing_file(self, tmp_path: Path) -> None:
        f = tmp_path / "requirements.md"
        f.write_text("# Requirements")
        uri = parse_source(str(f))
        assert uri.type == "file"
        assert uri.path == str(f)

    def test_parse_file_by_extension(self) -> None:
        """Non-existing file with known extension is detected as file type."""
        uri = parse_source("requirements.pdf")
        assert uri.type == "file"

    def test_parse_file_with_path_separator(self) -> None:
        uri = parse_source("./path/to/something")
        assert uri.type == "file"

    def test_parse_free_text_fallback(self) -> None:
        uri = parse_source("Fix the login button color")
        assert uri.type == "text"
        assert uri.path == "Fix the login button color"

    def test_parse_strips_whitespace(self) -> None:
        uri = parse_source("  jira://PROJ-1  ")
        assert uri.type == "jira"
        assert uri.path == "PROJ-1"


class TestSourceURIDataclass:
    def test_default_params(self) -> None:
        uri = SourceURI(type="file", raw="test.md")
        assert uri.params == {}
        assert uri.path == ""

    def test_all_fields(self) -> None:
        uri = SourceURI(
            type="jira",
            raw="jira://X?a=1",
            path="X",
            params={"a": "1"},
        )
        assert uri.type == "jira"
        assert uri.raw == "jira://X?a=1"
        assert uri.path == "X"
        assert uri.params == {"a": "1"}
