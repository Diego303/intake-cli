"""Tests for the Claude Code exporter."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml

from intake.export.claude_code import ClaudeCodeExporter
from intake.plugins.protocols import ExportResult

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def spec_dir(tmp_path: Path) -> Path:
    """Create a sample spec directory."""
    spec = tmp_path / "test-spec"
    spec.mkdir()

    (spec / "context.md").write_text("# Context\n\nStack: Python + FastAPI\n")
    (spec / "requirements.md").write_text(
        "# Requirements\n\n"
        "### FR-001: User login\n\nUser can log in with email/password.\n\n"
        "### FR-002: User logout\n\nUser can log out.\n"
    )
    (spec / "design.md").write_text("# Design\n\n## Architecture\nMonolith.\n")
    (spec / "tasks.md").write_text(
        "# Tasks\n\n"
        "### Task 1: Setup project\n\nCreate project structure.\n\n"
        "**Status:** pending\n\n"
        "### Task 2: Implement login\n\nBuild login endpoint.\n\n"
        "**Status:** pending\n"
    )
    (spec / "acceptance.yaml").write_text(
        yaml.dump(
            {
                "checks": [
                    {
                        "id": "tests",
                        "name": "Run tests",
                        "type": "command",
                        "command": "pytest tests/ -q",
                        "required": True,
                    },
                    {
                        "id": "lint",
                        "name": "Lint check",
                        "type": "command",
                        "command": "ruff check .",
                        "required": False,
                    },
                ],
            }
        )
    )
    (spec / "sources.md").write_text("# Sources\n\n- reqs.md\n")

    return spec


class TestClaudeCodeExportResult:
    def test_returns_export_result(self, spec_dir: Path, tmp_path: Path) -> None:
        """Export returns an ExportResult instance."""
        output = tmp_path / "output"
        exporter = ClaudeCodeExporter()
        result = exporter.export(str(spec_dir), str(output))

        assert isinstance(result, ExportResult)
        assert len(result.files_created) > 0
        assert result.primary_file.endswith("CLAUDE.md")

    def test_instructions_contain_summary(self, spec_dir: Path, tmp_path: Path) -> None:
        """Instructions mention task count and verify command."""
        output = tmp_path / "output"
        exporter = ClaudeCodeExporter()
        result = exporter.export(str(spec_dir), str(output))

        assert "2 task files" in result.instructions
        assert "verify.sh" in result.instructions


class TestClaudeCodeClaudeMd:
    def test_creates_claude_md(self, spec_dir: Path, tmp_path: Path) -> None:
        """Export creates CLAUDE.md."""
        output = tmp_path / "output"
        exporter = ClaudeCodeExporter()
        exporter.export(str(spec_dir), str(output))

        claude_md = output / "CLAUDE.md"
        assert claude_md.exists()

    def test_claude_md_contains_spec_section(self, spec_dir: Path, tmp_path: Path) -> None:
        """CLAUDE.md contains the intake spec section."""
        output = tmp_path / "output"
        exporter = ClaudeCodeExporter()
        exporter.export(str(spec_dir), str(output))

        content = (output / "CLAUDE.md").read_text()
        assert "## intake Spec" in content
        assert "test-spec" in content

    def test_claude_md_lists_tasks(self, spec_dir: Path, tmp_path: Path) -> None:
        """CLAUDE.md lists all tasks."""
        output = tmp_path / "output"
        exporter = ClaudeCodeExporter()
        exporter.export(str(spec_dir), str(output))

        content = (output / "CLAUDE.md").read_text()
        assert "Task 1" in content
        assert "Task 2" in content
        assert "Setup project" in content

    def test_append_to_existing_claude_md(self, spec_dir: Path, tmp_path: Path) -> None:
        """Export appends spec section to existing CLAUDE.md."""
        output = tmp_path / "output"
        output.mkdir()
        existing_content = "# My Project\n\nThis is my project.\n"
        (output / "CLAUDE.md").write_text(existing_content)

        exporter = ClaudeCodeExporter()
        exporter.export(str(spec_dir), str(output))

        content = (output / "CLAUDE.md").read_text()
        assert content.startswith("# My Project")
        assert "## intake Spec" in content

    def test_replace_existing_spec_section(self, spec_dir: Path, tmp_path: Path) -> None:
        """Export replaces existing intake spec section."""
        output = tmp_path / "output"
        output.mkdir()
        existing_content = (
            "# My Project\n\n"
            "## intake Spec\n\nOld content here.\n\n"
            "## Other Section\n\nKeep this.\n"
        )
        (output / "CLAUDE.md").write_text(existing_content)

        exporter = ClaudeCodeExporter()
        exporter.export(str(spec_dir), str(output))

        content = (output / "CLAUDE.md").read_text()
        assert "Old content here" not in content
        assert "## Other Section" in content
        assert "Keep this" in content
        assert "test-spec" in content


class TestClaudeCodeTaskFiles:
    def test_creates_task_files(self, spec_dir: Path, tmp_path: Path) -> None:
        """Export creates individual task files."""
        output = tmp_path / "output"
        exporter = ClaudeCodeExporter()
        exporter.export(str(spec_dir), str(output))

        tasks_dir = output / ".intake" / "tasks"
        assert tasks_dir.exists()
        assert (tasks_dir / "TASK-001.md").exists()
        assert (tasks_dir / "TASK-002.md").exists()

    def test_task_file_contains_details(self, spec_dir: Path, tmp_path: Path) -> None:
        """Task files contain task title and description."""
        output = tmp_path / "output"
        exporter = ClaudeCodeExporter()
        exporter.export(str(spec_dir), str(output))

        content = (output / ".intake" / "tasks" / "TASK-001.md").read_text()
        assert "Setup project" in content
        assert "Create project structure" in content


class TestClaudeCodeVerify:
    def test_creates_verify_sh(self, spec_dir: Path, tmp_path: Path) -> None:
        """Export creates verify.sh."""
        output = tmp_path / "output"
        exporter = ClaudeCodeExporter()
        exporter.export(str(spec_dir), str(output))

        verify = output / ".intake" / "verify.sh"
        assert verify.exists()

    def test_verify_contains_checks(self, spec_dir: Path, tmp_path: Path) -> None:
        """verify.sh contains acceptance check commands."""
        output = tmp_path / "output"
        exporter = ClaudeCodeExporter()
        exporter.export(str(spec_dir), str(output))

        content = (output / ".intake" / "verify.sh").read_text()
        assert "pytest tests/ -q" in content
        assert "ruff check ." in content
        assert "#!/usr/bin/env bash" in content

    def test_verify_is_executable(self, spec_dir: Path, tmp_path: Path) -> None:
        """verify.sh has executable permission."""
        import stat

        output = tmp_path / "output"
        exporter = ClaudeCodeExporter()
        exporter.export(str(spec_dir), str(output))

        verify = output / ".intake" / "verify.sh"
        mode = verify.stat().st_mode
        assert mode & stat.S_IEXEC


class TestClaudeCodeSpecSummary:
    def test_creates_spec_summary(self, spec_dir: Path, tmp_path: Path) -> None:
        """Export creates spec-summary.md."""
        output = tmp_path / "output"
        exporter = ClaudeCodeExporter()
        exporter.export(str(spec_dir), str(output))

        summary = output / ".intake" / "spec-summary.md"
        assert summary.exists()

    def test_spec_summary_content(self, spec_dir: Path, tmp_path: Path) -> None:
        """spec-summary.md contains requirements and task counts."""
        output = tmp_path / "output"
        exporter = ClaudeCodeExporter()
        exporter.export(str(spec_dir), str(output))

        content = (output / ".intake" / "spec-summary.md").read_text()
        assert "Requirements" in content
        assert "Tasks" in content
        assert "2" in content  # 2 requirements or tasks


class TestClaudeCodeSpecCopy:
    def test_copies_spec_files(self, spec_dir: Path, tmp_path: Path) -> None:
        """Export copies spec files to .intake/spec/."""
        output = tmp_path / "output"
        exporter = ClaudeCodeExporter()
        exporter.export(str(spec_dir), str(output))

        spec_out = output / ".intake" / "spec"
        assert spec_out.exists()
        assert (spec_out / "requirements.md").exists()
        assert (spec_out / "acceptance.yaml").exists()


class TestClaudeCodeEmptySpec:
    def test_empty_tasks(self, tmp_path: Path) -> None:
        """Export handles spec with no tasks."""
        spec = tmp_path / "empty-spec"
        spec.mkdir()
        (spec / "context.md").write_text("# Context\n")
        (spec / "requirements.md").write_text("# Requirements\n")
        (spec / "design.md").write_text("")
        (spec / "tasks.md").write_text("")
        (spec / "sources.md").write_text("")

        output = tmp_path / "output"
        exporter = ClaudeCodeExporter()
        result = exporter.export(str(spec), str(output))

        assert isinstance(result, ExportResult)
        assert (output / "CLAUDE.md").exists()
