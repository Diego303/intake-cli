"""Tests for the generic exporter."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml

from intake.export.generic import GenericExporter

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def spec_dir(tmp_path: Path) -> Path:
    """Create a sample spec directory."""
    spec = tmp_path / "test-spec"
    spec.mkdir()

    (spec / "requirements.md").write_text("# Requirements\n\n## FR-01: Login\nUser can log in.\n")
    (spec / "design.md").write_text("# Design\n\n## Architecture\nMicroservices.\n")
    (spec / "tasks.md").write_text("# Tasks\n\n### 1: Setup project\n")
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
    (spec / "context.md").write_text("# Context\n\nStack: python\n")
    (spec / "sources.md").write_text("# Sources\n\n- reqs.md\n")

    return spec


def test_export_creates_spec_md(spec_dir: Path, tmp_path: Path) -> None:
    """Exporter creates a SPEC.md."""
    output_dir = tmp_path / "output"
    exporter = GenericExporter()
    generated = exporter.export(str(spec_dir), str(output_dir))

    spec_md = output_dir / "SPEC.md"
    assert spec_md.exists()
    assert str(spec_md) in generated


def test_spec_md_contains_all_sections(spec_dir: Path, tmp_path: Path) -> None:
    """SPEC.md contains content from all spec files."""
    output_dir = tmp_path / "output"
    exporter = GenericExporter()
    exporter.export(str(spec_dir), str(output_dir))

    content = (output_dir / "SPEC.md").read_text()
    assert "Requirements" in content
    assert "Design" in content
    assert "Tasks" in content
    assert "Context" in content
    assert "Sources" in content


def test_export_creates_verify_sh(spec_dir: Path, tmp_path: Path) -> None:
    """Exporter creates a verify.sh script."""
    output_dir = tmp_path / "output"
    exporter = GenericExporter()
    generated = exporter.export(str(spec_dir), str(output_dir))

    verify_sh = output_dir / "verify.sh"
    assert verify_sh.exists()
    assert str(verify_sh) in generated


def test_verify_sh_contains_commands(spec_dir: Path, tmp_path: Path) -> None:
    """verify.sh contains the command checks from acceptance.yaml."""
    output_dir = tmp_path / "output"
    exporter = GenericExporter()
    exporter.export(str(spec_dir), str(output_dir))

    content = (output_dir / "verify.sh").read_text()
    assert "pytest tests/ -q" in content
    assert "ruff check ." in content
    assert "Run tests" in content


def test_verify_sh_is_executable(spec_dir: Path, tmp_path: Path) -> None:
    """verify.sh has executable permission."""
    import stat

    output_dir = tmp_path / "output"
    exporter = GenericExporter()
    exporter.export(str(spec_dir), str(output_dir))

    verify_sh = output_dir / "verify.sh"
    mode = verify_sh.stat().st_mode
    assert mode & stat.S_IEXEC


def test_export_copies_spec_files(spec_dir: Path, tmp_path: Path) -> None:
    """Exporter copies spec files to output/spec/."""
    output_dir = tmp_path / "output"
    exporter = GenericExporter()
    exporter.export(str(spec_dir), str(output_dir))

    spec_out = output_dir / "spec"
    assert spec_out.exists()
    assert (spec_out / "requirements.md").exists()


def test_export_returns_all_paths(spec_dir: Path, tmp_path: Path) -> None:
    """Export returns all generated file paths."""
    output_dir = tmp_path / "output"
    exporter = GenericExporter()
    generated = exporter.export(str(spec_dir), str(output_dir))

    # SPEC.md + verify.sh + 6 spec files
    assert len(generated) == 8


def test_verify_sh_header(spec_dir: Path, tmp_path: Path) -> None:
    """verify.sh has a proper bash shebang and spec name."""
    output_dir = tmp_path / "output"
    exporter = GenericExporter()
    exporter.export(str(spec_dir), str(output_dir))

    content = (output_dir / "verify.sh").read_text()
    assert content.startswith("#!/usr/bin/env bash")
    assert "test-spec" in content
