"""Tests for the Kiro exporter."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml

from intake.export.kiro import KiroExporter
from intake.plugins.protocols import ExportResult

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def spec_dir(tmp_path: Path) -> Path:
    """Create a sample spec directory."""
    spec = tmp_path / "test-spec"
    spec.mkdir()

    (spec / "context.md").write_text("# Context\n\nStack: Node.js + Express\n")
    (spec / "requirements.md").write_text(
        "# Requirements\n\n"
        "## Functional Requirements\n\n"
        "### FR-001: User registration\n\nNew users can create an account.\n\n"
        "#### Acceptance Criteria\n\n"
        "- Email validation is performed\n"
        "- Password must be at least 8 characters\n\n"
        "### FR-002: User login\n\nUsers can log in with email/password.\n"
    )
    (spec / "design.md").write_text("# Design\n\n## Architecture\n\nREST API with Express.\n")
    (spec / "tasks.md").write_text(
        "# Tasks\n\n"
        "### Task 1: Setup project\n\nInitialize Node.js project.\n\n"
        "**Status:** pending\n\n"
        "### Task 2: Implement registration\n\nBuild registration endpoint.\n\n"
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
                        "command": "npm test",
                        "tags": "task-1",
                    },
                    {
                        "id": "lint",
                        "name": "Lint check",
                        "type": "command",
                        "command": "npm run lint",
                    },
                ],
            }
        )
    )
    (spec / "sources.md").write_text("# Sources\n\n- reqs.md\n")

    return spec


class TestKiroExportResult:
    def test_returns_export_result(self, spec_dir: Path, tmp_path: Path) -> None:
        """Export returns an ExportResult."""
        output = tmp_path / "output"
        exporter = KiroExporter()
        result = exporter.export(str(spec_dir), str(output))

        assert isinstance(result, ExportResult)
        assert len(result.files_created) > 0

    def test_primary_file_is_requirements(self, spec_dir: Path, tmp_path: Path) -> None:
        """Primary file is requirements.md."""
        output = tmp_path / "output"
        exporter = KiroExporter()
        result = exporter.export(str(spec_dir), str(output))

        assert result.primary_file.endswith("requirements.md")

    def test_instructions_mention_kiro(self, spec_dir: Path, tmp_path: Path) -> None:
        """Instructions mention Kiro."""
        output = tmp_path / "output"
        exporter = KiroExporter()
        result = exporter.export(str(spec_dir), str(output))

        assert "Kiro" in result.instructions


class TestKiroRequirements:
    def test_creates_requirements(self, spec_dir: Path, tmp_path: Path) -> None:
        """Export creates requirements.md."""
        output = tmp_path / "output"
        exporter = KiroExporter()
        exporter.export(str(spec_dir), str(output))

        assert (output / "requirements.md").exists()

    def test_requirements_contains_structured_reqs(
        self,
        spec_dir: Path,
        tmp_path: Path,
    ) -> None:
        """requirements.md has structured requirement blocks."""
        output = tmp_path / "output"
        exporter = KiroExporter()
        exporter.export(str(spec_dir), str(output))

        content = (output / "requirements.md").read_text()
        assert "FR-001" in content
        assert "User registration" in content
        assert "FR-002" in content

    def test_requirements_have_checkboxes(
        self,
        spec_dir: Path,
        tmp_path: Path,
    ) -> None:
        """requirements.md has acceptance criteria checkboxes."""
        output = tmp_path / "output"
        exporter = KiroExporter()
        exporter.export(str(spec_dir), str(output))

        content = (output / "requirements.md").read_text()
        assert "- [ ]" in content


class TestKiroDesign:
    def test_creates_design(self, spec_dir: Path, tmp_path: Path) -> None:
        """Export creates design.md."""
        output = tmp_path / "output"
        exporter = KiroExporter()
        exporter.export(str(spec_dir), str(output))

        assert (output / "design.md").exists()

    def test_design_contains_content(self, spec_dir: Path, tmp_path: Path) -> None:
        """design.md contains design content from spec."""
        output = tmp_path / "output"
        exporter = KiroExporter()
        exporter.export(str(spec_dir), str(output))

        content = (output / "design.md").read_text()
        assert "REST API" in content


class TestKiroTasks:
    def test_creates_tasks(self, spec_dir: Path, tmp_path: Path) -> None:
        """Export creates tasks.md."""
        output = tmp_path / "output"
        exporter = KiroExporter()
        exporter.export(str(spec_dir), str(output))

        assert (output / "tasks.md").exists()

    def test_tasks_contains_task_details(self, spec_dir: Path, tmp_path: Path) -> None:
        """tasks.md contains task titles and descriptions."""
        output = tmp_path / "output"
        exporter = KiroExporter()
        exporter.export(str(spec_dir), str(output))

        content = (output / "tasks.md").read_text()
        assert "Task 1" in content
        assert "Setup project" in content
        assert "Task 2" in content


class TestKiroSpecCopy:
    def test_copies_spec_files(self, spec_dir: Path, tmp_path: Path) -> None:
        """Export copies spec files to .intake/spec/."""
        output = tmp_path / "output"
        exporter = KiroExporter()
        exporter.export(str(spec_dir), str(output))

        spec_out = output / ".intake" / "spec"
        assert spec_out.exists()
        assert (spec_out / "requirements.md").exists()


class TestKiroMeta:
    def test_meta_name(self) -> None:
        """Exporter meta name is 'kiro'."""
        exporter = KiroExporter()
        assert exporter.meta.name == "kiro"


class TestKiroEmptySpec:
    def test_empty_requirements(self, tmp_path: Path) -> None:
        """Export handles spec with no structured requirements."""
        spec = tmp_path / "empty-spec"
        spec.mkdir()
        (spec / "context.md").write_text("")
        (spec / "requirements.md").write_text("# Requirements\n\nSome text.\n")
        (spec / "design.md").write_text("")
        (spec / "tasks.md").write_text("")
        (spec / "sources.md").write_text("")

        output = tmp_path / "output"
        exporter = KiroExporter()
        result = exporter.export(str(spec), str(output))

        assert isinstance(result, ExportResult)
        assert (output / "requirements.md").exists()
