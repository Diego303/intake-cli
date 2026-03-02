"""Tests for the verification engine."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml

from intake.verify.engine import (
    VerificationEngine,
    VerificationReport,
    VerifyError,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Create a project directory with sample files."""
    # Create some project files
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("def main():\n    print('hello')\n")
    (src_dir / "utils.py").write_text("import os\n\nPASSWORD = 'secret'\n")
    (tmp_path / "README.md").write_text("# Test Project\n")
    return tmp_path


@pytest.fixture
def acceptance_file(tmp_path: Path) -> Path:
    """Create a sample acceptance.yaml."""
    checks = {
        "checks": [
            {
                "id": "check-echo",
                "name": "Echo test",
                "type": "command",
                "command": "echo hello",
                "required": True,
                "tags": ["basic"],
            },
            {
                "id": "check-files",
                "name": "Files exist",
                "type": "files_exist",
                "paths": ["README.md", "src/main.py"],
                "required": True,
                "tags": ["structure"],
            },
            {
                "id": "check-pattern",
                "name": "Main function present",
                "type": "pattern_present",
                "glob": "src/*.py",
                "patterns": ["def main"],
                "required": True,
                "tags": ["code"],
            },
            {
                "id": "check-no-password",
                "name": "No hardcoded passwords",
                "type": "pattern_absent",
                "glob": "src/*.py",
                "patterns": ["PASSWORD\\s*="],
                "required": False,
                "tags": ["security"],
            },
        ],
    }
    path = tmp_path / "specs" / "test-spec"
    path.mkdir(parents=True)
    acceptance = path / "acceptance.yaml"
    acceptance.write_text(yaml.dump(checks))
    return acceptance


def test_run_all_checks(project_dir: Path, acceptance_file: Path) -> None:
    """All checks run and produce results."""
    engine = VerificationEngine(project_dir=str(project_dir))
    report = engine.run(acceptance_file=str(acceptance_file))

    assert isinstance(report, VerificationReport)
    assert report.total_checks == 4
    assert len(report.results) == 4


def test_command_check_passes(project_dir: Path, acceptance_file: Path) -> None:
    """Command check passes when exit code is 0."""
    engine = VerificationEngine(project_dir=str(project_dir))
    report = engine.run(str(acceptance_file))

    echo_result = next(r for r in report.results if r.id == "check-echo")
    assert echo_result.passed is True
    assert echo_result.duration_ms >= 0


def test_files_exist_check_passes(project_dir: Path, acceptance_file: Path) -> None:
    """Files exist check passes when all files are present."""
    engine = VerificationEngine(project_dir=str(project_dir))
    report = engine.run(str(acceptance_file))

    files_result = next(r for r in report.results if r.id == "check-files")
    assert files_result.passed is True


def test_files_exist_check_fails_for_missing(project_dir: Path, tmp_path: Path) -> None:
    """Files exist check fails when a file is missing."""
    checks = {
        "checks": [
            {
                "id": "missing-files",
                "name": "Missing check",
                "type": "files_exist",
                "paths": ["nonexistent.txt"],
                "required": True,
            },
        ],
    }
    spec_dir = tmp_path / "specs" / "test"
    spec_dir.mkdir(parents=True)
    path = spec_dir / "acceptance.yaml"
    path.write_text(yaml.dump(checks))

    engine = VerificationEngine(project_dir=str(project_dir))
    report = engine.run(str(path))

    assert report.results[0].passed is False
    assert "nonexistent.txt" in report.results[0].output


def test_pattern_present_check(project_dir: Path, tmp_path: Path) -> None:
    """Pattern present check passes when pattern is found in all matching files."""
    checks = {
        "checks": [
            {
                "id": "check-pattern",
                "name": "Main function present",
                "type": "pattern_present",
                "glob": "src/main.py",
                "patterns": ["def main"],
                "required": True,
            },
        ],
    }
    spec_dir = tmp_path / "specs" / "test"
    spec_dir.mkdir(parents=True)
    path = spec_dir / "acceptance.yaml"
    path.write_text(yaml.dump(checks))

    engine = VerificationEngine(project_dir=str(project_dir))
    report = engine.run(str(path))

    assert report.results[0].passed is True


def test_pattern_absent_check_detects_violation(project_dir: Path, acceptance_file: Path) -> None:
    """Pattern absent check fails when forbidden pattern is found."""
    engine = VerificationEngine(project_dir=str(project_dir))
    report = engine.run(str(acceptance_file))

    pwd_result = next(r for r in report.results if r.id == "check-no-password")
    assert pwd_result.passed is False
    assert "PASSWORD" in pwd_result.output


def test_filter_by_tags(project_dir: Path, acceptance_file: Path) -> None:
    """Filtering by tags only runs matching checks."""
    engine = VerificationEngine(project_dir=str(project_dir))
    report = engine.run(str(acceptance_file), tags=["security"])

    assert report.total_checks == 4  # total count is still all checks
    assert len(report.results) == 1
    assert report.results[0].id == "check-no-password"


def test_fail_fast_stops_at_first_required_failure(project_dir: Path, tmp_path: Path) -> None:
    """Fail-fast stops after the first required failure."""
    checks = {
        "checks": [
            {
                "id": "fail-cmd",
                "name": "Will fail",
                "type": "command",
                "command": "exit 1",
                "required": True,
            },
            {
                "id": "pass-cmd",
                "name": "Would pass",
                "type": "command",
                "command": "echo ok",
                "required": True,
            },
        ],
    }
    spec_dir = tmp_path / "specs" / "test"
    spec_dir.mkdir(parents=True)
    path = spec_dir / "acceptance.yaml"
    path.write_text(yaml.dump(checks))

    engine = VerificationEngine(project_dir=str(project_dir))
    report = engine.run(str(path), fail_fast=True)

    assert len(report.results) == 1
    assert report.results[0].id == "fail-cmd"
    assert report.skipped == 1


def test_missing_acceptance_file_raises(project_dir: Path) -> None:
    """Missing acceptance file raises VerifyError."""
    engine = VerificationEngine(project_dir=str(project_dir))
    with pytest.raises(VerifyError, match="not found"):
        engine.run("/nonexistent/acceptance.yaml")


def test_invalid_yaml_raises(project_dir: Path, tmp_path: Path) -> None:
    """Invalid YAML raises VerifyError."""
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("{invalid yaml: [")

    engine = VerificationEngine(project_dir=str(project_dir))
    with pytest.raises(VerifyError, match="Invalid YAML"):
        engine.run(str(bad_file))


def test_exit_code_zero_on_success(project_dir: Path, tmp_path: Path) -> None:
    """Exit code is 0 when all required checks pass."""
    checks = {
        "checks": [
            {
                "id": "ok",
                "name": "OK",
                "type": "command",
                "command": "echo ok",
                "required": True,
            },
        ],
    }
    spec_dir = tmp_path / "specs" / "test"
    spec_dir.mkdir(parents=True)
    path = spec_dir / "acceptance.yaml"
    path.write_text(yaml.dump(checks))

    engine = VerificationEngine(project_dir=str(project_dir))
    report = engine.run(str(path))

    assert report.exit_code == 0
    assert report.all_required_passed is True


def test_exit_code_one_on_failure(project_dir: Path, tmp_path: Path) -> None:
    """Exit code is 1 when a required check fails."""
    checks = {
        "checks": [
            {
                "id": "fail",
                "name": "Fail",
                "type": "command",
                "command": "exit 1",
                "required": True,
            },
        ],
    }
    spec_dir = tmp_path / "specs" / "test"
    spec_dir.mkdir(parents=True)
    path = spec_dir / "acceptance.yaml"
    path.write_text(yaml.dump(checks))

    engine = VerificationEngine(project_dir=str(project_dir))
    report = engine.run(str(path))

    assert report.exit_code == 1
    assert report.all_required_passed is False


def test_unknown_check_type_fails(project_dir: Path, tmp_path: Path) -> None:
    """Unknown check type produces a failure result."""
    checks = {
        "checks": [
            {
                "id": "bad-type",
                "name": "Bad type",
                "type": "nonexistent_type",
                "required": False,
            },
        ],
    }
    spec_dir = tmp_path / "specs" / "test"
    spec_dir.mkdir(parents=True)
    path = spec_dir / "acceptance.yaml"
    path.write_text(yaml.dump(checks))

    engine = VerificationEngine(project_dir=str(project_dir))
    report = engine.run(str(path))

    assert report.results[0].passed is False
    assert "Unknown check type" in report.results[0].output


def test_command_check_fails_on_nonzero_exit(project_dir: Path, tmp_path: Path) -> None:
    """Command check fails when exit code is non-zero."""
    checks = {
        "checks": [
            {
                "id": "bad-cmd",
                "name": "Failing command",
                "type": "command",
                "command": "exit 42",
                "required": True,
            },
        ],
    }
    spec_dir = tmp_path / "specs" / "test"
    spec_dir.mkdir(parents=True)
    path = spec_dir / "acceptance.yaml"
    path.write_text(yaml.dump(checks))

    engine = VerificationEngine(project_dir=str(project_dir))
    report = engine.run(str(path))

    assert report.results[0].passed is False


def test_pattern_present_fails_when_not_found(project_dir: Path, tmp_path: Path) -> None:
    """Pattern present fails when the pattern is not in any file."""
    checks = {
        "checks": [
            {
                "id": "missing-pattern",
                "name": "Missing pattern",
                "type": "pattern_present",
                "glob": "src/*.py",
                "patterns": ["class NonExistentClass"],
                "required": True,
            },
        ],
    }
    spec_dir = tmp_path / "specs" / "test"
    spec_dir.mkdir(parents=True)
    path = spec_dir / "acceptance.yaml"
    path.write_text(yaml.dump(checks))

    engine = VerificationEngine(project_dir=str(project_dir))
    report = engine.run(str(path))

    assert report.results[0].passed is False
    assert "not found" in report.results[0].output
