"""Tests for the Cursor exporter."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml

from intake.export.cursor import CursorExporter
from intake.plugins.protocols import ExportResult

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def spec_dir(tmp_path: Path) -> Path:
    """Create a sample spec directory."""
    spec = tmp_path / "test-spec"
    spec.mkdir()

    (spec / "context.md").write_text("# Context\n\nStack: Python + Django\n")
    (spec / "requirements.md").write_text(
        "# Requirements\n\n"
        "### FR-001: User login\n\nUser can log in.\n\n"
        "### FR-002: User logout\n\nUser can log out.\n"
    )
    (spec / "design.md").write_text("# Design\n\n## Architecture\nMonolith.\n")
    (spec / "tasks.md").write_text(
        "# Tasks\n\n"
        "### Task 1: Setup project\n\nCreate project.\n\n"
        "**Status:** pending\n\n"
        "### Task 2: Implement login\n\nBuild login.\n\n"
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
                    },
                ],
            }
        )
    )
    (spec / "sources.md").write_text("# Sources\n\n- reqs.md\n")

    return spec


class TestCursorExportResult:
    def test_returns_export_result(self, spec_dir: Path, tmp_path: Path) -> None:
        """Export returns an ExportResult."""
        output = tmp_path / "output"
        exporter = CursorExporter()
        result = exporter.export(str(spec_dir), str(output))

        assert isinstance(result, ExportResult)
        assert len(result.files_created) > 0

    def test_primary_file_is_mdc(self, spec_dir: Path, tmp_path: Path) -> None:
        """Primary file is the .mdc rules file."""
        output = tmp_path / "output"
        exporter = CursorExporter()
        result = exporter.export(str(spec_dir), str(output))

        assert result.primary_file.endswith("intake-spec.mdc")

    def test_instructions_mention_cursor(self, spec_dir: Path, tmp_path: Path) -> None:
        """Instructions mention Cursor."""
        output = tmp_path / "output"
        exporter = CursorExporter()
        result = exporter.export(str(spec_dir), str(output))

        assert "Cursor" in result.instructions


class TestCursorRulesFile:
    def test_creates_rules_file(self, spec_dir: Path, tmp_path: Path) -> None:
        """Export creates .cursor/rules/intake-spec.mdc."""
        output = tmp_path / "output"
        exporter = CursorExporter()
        exporter.export(str(spec_dir), str(output))

        rules = output / ".cursor" / "rules" / "intake-spec.mdc"
        assert rules.exists()

    def test_rules_has_frontmatter(self, spec_dir: Path, tmp_path: Path) -> None:
        """Rules file starts with YAML frontmatter."""
        output = tmp_path / "output"
        exporter = CursorExporter()
        exporter.export(str(spec_dir), str(output))

        content = (output / ".cursor" / "rules" / "intake-spec.mdc").read_text()
        assert content.startswith("---")
        assert "alwaysApply: true" in content
        assert "description:" in content

    def test_rules_contains_spec_content(self, spec_dir: Path, tmp_path: Path) -> None:
        """Rules file contains spec context and tasks."""
        output = tmp_path / "output"
        exporter = CursorExporter()
        exporter.export(str(spec_dir), str(output))

        content = (output / ".cursor" / "rules" / "intake-spec.mdc").read_text()
        assert "Python + Django" in content
        assert "Task 1" in content
        assert "Setup project" in content

    def test_rules_contains_acceptance_checks(
        self,
        spec_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Rules file includes acceptance criteria."""
        output = tmp_path / "output"
        exporter = CursorExporter()
        exporter.export(str(spec_dir), str(output))

        content = (output / ".cursor" / "rules" / "intake-spec.mdc").read_text()
        assert "pytest tests/ -q" in content


class TestCursorSpecCopy:
    def test_copies_spec_files(self, spec_dir: Path, tmp_path: Path) -> None:
        """Export copies spec files to .intake/spec/."""
        output = tmp_path / "output"
        exporter = CursorExporter()
        exporter.export(str(spec_dir), str(output))

        spec_out = output / ".intake" / "spec"
        assert spec_out.exists()
        assert (spec_out / "requirements.md").exists()


class TestCursorMeta:
    def test_meta_name(self) -> None:
        """Exporter meta name is 'cursor'."""
        exporter = CursorExporter()
        assert exporter.meta.name == "cursor"
