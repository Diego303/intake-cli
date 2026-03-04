"""Tests for shared export helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

from intake.export._helpers import (
    count_requirements,
    load_acceptance_checks,
    parse_tasks,
    read_spec_file,
    summarize_content,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestReadSpecFile:
    def test_reads_existing_file(self, tmp_path: Path) -> None:
        """Reads content from an existing file."""
        (tmp_path / "test.md").write_text("hello world")
        result = read_spec_file(tmp_path, "test.md")
        assert result == "hello world"

    def test_returns_empty_for_missing(self, tmp_path: Path) -> None:
        """Returns empty string for missing files."""
        result = read_spec_file(tmp_path, "nonexistent.md")
        assert result == ""


class TestParseTasks:
    def test_parses_task_headings(self) -> None:
        """Extracts tasks from ### Task N: Title format."""
        content = (
            "# Tasks\n\n"
            "### Task 1: Setup project\n\nCreate project structure.\n\n"
            "**Status:** pending\n\n"
            "### Task 2: Implement login\n\nBuild login endpoint.\n"
        )
        tasks = parse_tasks(content)
        assert len(tasks) == 2
        assert tasks[0]["id"] == "1"
        assert tasks[0]["title"] == "Setup project"
        assert tasks[0]["status"] == "pending"
        assert tasks[1]["id"] == "2"
        assert tasks[1]["title"] == "Implement login"

    def test_parses_short_format(self) -> None:
        """Extracts tasks from ### N: Title format."""
        content = "### 1: Setup\n\nDescription.\n"
        tasks = parse_tasks(content)
        assert len(tasks) == 1
        assert tasks[0]["id"] == "1"
        assert tasks[0]["title"] == "Setup"

    def test_detects_status(self) -> None:
        """Detects **Status:** markers."""
        content = "### Task 1: Setup\n\n**Status:** done\n"
        tasks = parse_tasks(content)
        assert tasks[0]["status"] == "done"

    def test_empty_content(self) -> None:
        """Returns empty list for empty content."""
        assert parse_tasks("") == []
        assert parse_tasks("   ") == []


class TestLoadAcceptanceChecks:
    def test_loads_checks(self, tmp_path: Path) -> None:
        """Loads checks from acceptance.yaml."""
        (tmp_path / "acceptance.yaml").write_text(
            yaml.dump({"checks": [{"type": "command", "command": "pytest"}]})
        )
        checks = load_acceptance_checks(tmp_path)
        assert len(checks) == 1
        assert checks[0]["type"] == "command"

    def test_missing_file(self, tmp_path: Path) -> None:
        """Returns empty list for missing file."""
        assert load_acceptance_checks(tmp_path) == []

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        """Returns empty list for invalid YAML."""
        (tmp_path / "acceptance.yaml").write_text(":::bad yaml:::")
        assert load_acceptance_checks(tmp_path) == []

    def test_missing_checks_key(self, tmp_path: Path) -> None:
        """Returns empty list when checks key is missing."""
        (tmp_path / "acceptance.yaml").write_text(yaml.dump({"other": "data"}))
        assert load_acceptance_checks(tmp_path) == []


class TestSummarizeContent:
    def test_short_content_unchanged(self) -> None:
        """Short content is returned unchanged."""
        content = "line 1\nline 2\nline 3"
        assert summarize_content(content, max_lines=10) == content

    def test_long_content_truncated(self) -> None:
        """Long content is truncated with ellipsis."""
        content = "\n".join(f"line {i}" for i in range(100))
        result = summarize_content(content, max_lines=5)
        assert "line 0" in result
        assert "line 4" in result
        assert "95 more lines" in result


class TestCountRequirements:
    def test_counts_fr_and_nfr(self) -> None:
        """Counts FR- and NFR- requirement headings."""
        content = "### FR-001: Login\n\n### FR-002: Logout\n\n### NFR-001: Performance\n"
        assert count_requirements(content) == 3

    def test_counts_req_prefix(self) -> None:
        """Counts REQ- requirement headings."""
        content = "### REQ-001: Something\n\n### REQ-002: Else\n"
        assert count_requirements(content) == 2

    def test_empty_content(self) -> None:
        """Returns 0 for empty content."""
        assert count_requirements("") == 0
        assert count_requirements("# Requirements\n\nSome text.\n") == 0
