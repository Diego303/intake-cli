"""Tests for the architect exporter."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml

from intake.export.architect import ArchitectExporter

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def spec_dir(tmp_path: Path) -> Path:
    """Create a sample spec directory with all 6 files."""
    spec = tmp_path / "test-spec"
    spec.mkdir()

    (spec / "requirements.md").write_text(
        "# Requirements\n\n"
        "## Functional Requirements\n\n"
        "### FR-01: User login\n\nUsers can log in with email and password.\n\n"
        "### FR-02: User registration\n\nUsers can register a new account.\n"
    )
    (spec / "design.md").write_text(
        "# Design\n\n## Components\n\n- Auth service\n- User service\n"
    )
    (spec / "tasks.md").write_text(
        "# Tasks\n\n"
        "### Task 1: Set up project\n\nInitialize the project structure.\n\n"
        "### Task 2: Implement login\n\nCreate the login endpoint.\n\n"
        "### Task 3: Implement registration\n\nCreate the registration endpoint.\n"
    )
    (spec / "acceptance.yaml").write_text(yaml.dump({
        "checks": [
            {
                "id": "unit-tests",
                "name": "Unit tests pass",
                "type": "command",
                "command": "pytest tests/ -q",
                "required": True,
            },
            {
                "id": "login-endpoint",
                "name": "Login endpoint exists",
                "type": "files_exist",
                "paths": ["src/auth/login.py"],
                "required": True,
            },
        ],
    }))
    (spec / "context.md").write_text(
        "# Context\n\nProject: test-auth\nStack: python, fastapi\n"
    )
    (spec / "sources.md").write_text(
        "# Sources\n\n- requirements.md\n"
    )

    return spec


def test_export_creates_pipeline_yaml(spec_dir: Path, tmp_path: Path) -> None:
    """Exporter creates a pipeline.yaml."""
    output_dir = tmp_path / "output"
    exporter = ArchitectExporter()
    generated = exporter.export(str(spec_dir), str(output_dir))

    pipeline_path = output_dir / "pipeline.yaml"
    assert pipeline_path.exists()
    assert str(pipeline_path) in generated


def test_pipeline_has_steps_per_task(spec_dir: Path, tmp_path: Path) -> None:
    """Pipeline has one step per task plus verification."""
    output_dir = tmp_path / "output"
    exporter = ArchitectExporter()
    exporter.export(str(spec_dir), str(output_dir))

    pipeline = yaml.safe_load((output_dir / "pipeline.yaml").read_text())
    assert "steps" in pipeline
    # 3 tasks + 1 final verification
    assert len(pipeline["steps"]) == 4
    assert pipeline["steps"][-1]["name"] == "final-verification"


def test_pipeline_has_correct_name(spec_dir: Path, tmp_path: Path) -> None:
    """Pipeline name matches spec directory name."""
    output_dir = tmp_path / "output"
    exporter = ArchitectExporter()
    exporter.export(str(spec_dir), str(output_dir))

    pipeline = yaml.safe_load((output_dir / "pipeline.yaml").read_text())
    assert pipeline["name"] == "test-spec"


def test_export_copies_spec_files(spec_dir: Path, tmp_path: Path) -> None:
    """Exporter copies all spec files to output/spec/."""
    output_dir = tmp_path / "output"
    exporter = ArchitectExporter()
    exporter.export(str(spec_dir), str(output_dir))

    spec_out = output_dir / "spec"
    assert spec_out.exists()
    assert (spec_out / "requirements.md").exists()
    assert (spec_out / "acceptance.yaml").exists()


def test_export_returns_all_generated_paths(spec_dir: Path, tmp_path: Path) -> None:
    """Export returns paths for pipeline.yaml and all copied spec files."""
    output_dir = tmp_path / "output"
    exporter = ArchitectExporter()
    generated = exporter.export(str(spec_dir), str(output_dir))

    # 1 pipeline + 6 spec files
    assert len(generated) == 7


def test_task_parsing_from_markdown(spec_dir: Path, tmp_path: Path) -> None:
    """Tasks are correctly parsed from tasks.md headings."""
    output_dir = tmp_path / "output"
    exporter = ArchitectExporter()
    exporter.export(str(spec_dir), str(output_dir))

    pipeline = yaml.safe_load((output_dir / "pipeline.yaml").read_text())
    task_steps = [s for s in pipeline["steps"] if s["name"].startswith("task-")]
    assert len(task_steps) == 3
    assert task_steps[0]["name"] == "task-1"
    assert task_steps[1]["name"] == "task-2"


def test_final_verification_includes_command_checks(spec_dir: Path, tmp_path: Path) -> None:
    """Final verification step includes required command checks."""
    output_dir = tmp_path / "output"
    exporter = ArchitectExporter()
    exporter.export(str(spec_dir), str(output_dir))

    pipeline = yaml.safe_load((output_dir / "pipeline.yaml").read_text())
    final = pipeline["steps"][-1]
    assert "checks" in final
    assert "pytest tests/ -q" in final["checks"]


def test_export_empty_spec(tmp_path: Path) -> None:
    """Export handles an empty spec directory gracefully."""
    spec = tmp_path / "empty-spec"
    spec.mkdir()
    output_dir = tmp_path / "output"

    exporter = ArchitectExporter()
    exporter.export(str(spec), str(output_dir))

    # At least pipeline.yaml
    assert (output_dir / "pipeline.yaml").exists()
