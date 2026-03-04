"""Tests for the Copilot exporter."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml

from intake.export.copilot import CopilotExporter
from intake.plugins.protocols import ExportResult

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def spec_dir(tmp_path: Path) -> Path:
    """Create a sample spec directory."""
    spec = tmp_path / "test-spec"
    spec.mkdir()

    (spec / "context.md").write_text("# Context\n\nStack: Go + Gin\n")
    (spec / "requirements.md").write_text(
        "# Requirements\n\n"
        "### FR-001: Health check\n\nAPI has a health check endpoint.\n\n"
        "### FR-002: CRUD users\n\nBasic CRUD for users.\n"
    )
    (spec / "design.md").write_text("# Design\n\n## Architecture\nREST API.\n")
    (spec / "tasks.md").write_text(
        "# Tasks\n\n"
        "### Task 1: Setup project\n\nInitialize Go module.\n\n"
        "**Status:** pending\n\n"
        "### Task 2: Implement health check\n\nAdd /health endpoint.\n\n"
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
                        "command": "go test ./...",
                    },
                ],
            }
        )
    )
    (spec / "sources.md").write_text("# Sources\n\n- reqs.md\n")

    return spec


class TestCopilotExportResult:
    def test_returns_export_result(self, spec_dir: Path, tmp_path: Path) -> None:
        """Export returns an ExportResult."""
        output = tmp_path / "output"
        exporter = CopilotExporter()
        result = exporter.export(str(spec_dir), str(output))

        assert isinstance(result, ExportResult)
        assert len(result.files_created) > 0

    def test_primary_file_is_copilot_instructions(
        self,
        spec_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Primary file is copilot-instructions.md."""
        output = tmp_path / "output"
        exporter = CopilotExporter()
        result = exporter.export(str(spec_dir), str(output))

        assert result.primary_file.endswith("copilot-instructions.md")

    def test_instructions_mention_copilot(
        self,
        spec_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Instructions mention Copilot."""
        output = tmp_path / "output"
        exporter = CopilotExporter()
        result = exporter.export(str(spec_dir), str(output))

        assert "Copilot" in result.instructions


class TestCopilotInstructionsFile:
    def test_creates_instructions_file(self, spec_dir: Path, tmp_path: Path) -> None:
        """Export creates .github/copilot-instructions.md."""
        output = tmp_path / "output"
        exporter = CopilotExporter()
        exporter.export(str(spec_dir), str(output))

        instructions = output / ".github" / "copilot-instructions.md"
        assert instructions.exists()

    def test_instructions_contain_context(
        self,
        spec_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Instructions file contains project context."""
        output = tmp_path / "output"
        exporter = CopilotExporter()
        exporter.export(str(spec_dir), str(output))

        content = (output / ".github" / "copilot-instructions.md").read_text()
        assert "Go + Gin" in content

    def test_instructions_contain_tasks(
        self,
        spec_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Instructions file lists tasks."""
        output = tmp_path / "output"
        exporter = CopilotExporter()
        exporter.export(str(spec_dir), str(output))

        content = (output / ".github" / "copilot-instructions.md").read_text()
        assert "Task 1" in content
        assert "Setup project" in content
        assert "Task 2" in content

    def test_instructions_contain_acceptance_checks(
        self,
        spec_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Instructions file includes acceptance check commands."""
        output = tmp_path / "output"
        exporter = CopilotExporter()
        exporter.export(str(spec_dir), str(output))

        content = (output / ".github" / "copilot-instructions.md").read_text()
        assert "go test ./..." in content

    def test_instructions_contain_spec_name(
        self,
        spec_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Instructions file references the spec name."""
        output = tmp_path / "output"
        exporter = CopilotExporter()
        exporter.export(str(spec_dir), str(output))

        content = (output / ".github" / "copilot-instructions.md").read_text()
        assert "test-spec" in content


class TestCopilotSpecCopy:
    def test_copies_spec_files(self, spec_dir: Path, tmp_path: Path) -> None:
        """Export copies spec files to .intake/spec/."""
        output = tmp_path / "output"
        exporter = CopilotExporter()
        exporter.export(str(spec_dir), str(output))

        spec_out = output / ".intake" / "spec"
        assert spec_out.exists()
        assert (spec_out / "requirements.md").exists()


class TestCopilotMeta:
    def test_meta_name(self) -> None:
        """Exporter meta name is 'copilot'."""
        exporter = CopilotExporter()
        assert exporter.meta.name == "copilot"


class TestCopilotEmptySpec:
    def test_handles_empty_spec(self, tmp_path: Path) -> None:
        """Export handles spec with minimal content."""
        spec = tmp_path / "empty-spec"
        spec.mkdir()
        (spec / "context.md").write_text("")
        (spec / "requirements.md").write_text("")
        (spec / "design.md").write_text("")
        (spec / "tasks.md").write_text("")
        (spec / "sources.md").write_text("")

        output = tmp_path / "output"
        exporter = CopilotExporter()
        result = exporter.export(str(spec), str(output))

        assert isinstance(result, ExportResult)
        assert (output / ".github" / "copilot-instructions.md").exists()
