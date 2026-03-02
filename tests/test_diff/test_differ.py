"""Tests for the spec differ."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml

from intake.diff.differ import DiffEntry, DiffError, SpecDiff, SpecDiffer

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def spec_a(tmp_path: Path) -> Path:
    """Create a first version spec directory."""
    spec = tmp_path / "spec-v1"
    spec.mkdir()

    (spec / "requirements.md").write_text(
        "# Requirements\n\n"
        "### FR-01: User login\n\nUsers can log in.\n\n"
        "### FR-02: User logout\n\nUsers can log out.\n\n"
        "### NFR-01: Performance\n\nResponse time < 200ms.\n"
    )
    (spec / "tasks.md").write_text(
        "# Tasks\n\n"
        "### Task 1: Setup project\n\nInitialize.\n\n"
        "### Task 2: Login endpoint\n\nCreate login.\n"
    )
    (spec / "acceptance.yaml").write_text(yaml.dump({
        "checks": [
            {"id": "tests", "name": "Run tests", "type": "command", "command": "pytest"},
            {"id": "lint", "name": "Lint", "type": "command", "command": "ruff check"},
        ],
    }))

    return spec


@pytest.fixture
def spec_b(tmp_path: Path) -> Path:
    """Create a second version spec directory with changes."""
    spec = tmp_path / "spec-v2"
    spec.mkdir()

    (spec / "requirements.md").write_text(
        "# Requirements\n\n"
        "### FR-01: User login\n\nUsers can log in with email and password.\n\n"
        "### FR-03: Password reset\n\nUsers can reset their password.\n\n"
        "### NFR-01: Performance\n\nResponse time < 200ms.\n"
    )
    (spec / "tasks.md").write_text(
        "# Tasks\n\n"
        "### Task 1: Setup project\n\nInitialize.\n\n"
        "### Task 2: Login endpoint\n\nCreate login.\n\n"
        "### Task 3: Password reset\n\nCreate reset flow.\n"
    )
    (spec / "acceptance.yaml").write_text(yaml.dump({
        "checks": [
            {"id": "tests", "name": "Run tests", "type": "command", "command": "pytest"},
            {"id": "security", "name": "Security scan", "type": "command", "command": "bandit"},
        ],
    }))

    return spec


def test_diff_detects_added_requirements(spec_a: Path, spec_b: Path) -> None:
    """Differ detects requirements added in spec_b."""
    differ = SpecDiffer()
    result = differ.diff(str(spec_a), str(spec_b))

    added = [c for c in result.added if c.section == "requirements"]
    assert any(c.item_id == "FR-03" for c in added)


def test_diff_detects_removed_requirements(spec_a: Path, spec_b: Path) -> None:
    """Differ detects requirements removed in spec_b."""
    differ = SpecDiffer()
    result = differ.diff(str(spec_a), str(spec_b))

    removed = [c for c in result.removed if c.section == "requirements"]
    assert any(c.item_id == "FR-02" for c in removed)


def test_diff_detects_modified_requirements(spec_a: Path, spec_b: Path) -> None:
    """Differ detects modified requirements."""
    differ = SpecDiffer()
    result = differ.diff(str(spec_a), str(spec_b))

    modified = [c for c in result.modified if c.section == "requirements"]
    assert any(c.item_id == "FR-01" for c in modified)


def test_diff_detects_added_tasks(spec_a: Path, spec_b: Path) -> None:
    """Differ detects tasks added in spec_b."""
    differ = SpecDiffer()
    result = differ.diff(str(spec_a), str(spec_b))

    added = [c for c in result.added if c.section == "tasks"]
    assert any(c.item_id == "3" for c in added)


def test_diff_detects_acceptance_changes(spec_a: Path, spec_b: Path) -> None:
    """Differ detects changes in acceptance checks."""
    differ = SpecDiffer()
    result = differ.diff(str(spec_a), str(spec_b))

    acceptance_changes = [c for c in result.changes if c.section == "acceptance"]
    added_ids = [c.item_id for c in acceptance_changes if c.change_type == "added"]
    removed_ids = [c.item_id for c in acceptance_changes if c.change_type == "removed"]

    assert "security" in added_ids
    assert "lint" in removed_ids


def test_diff_has_changes(spec_a: Path, spec_b: Path) -> None:
    """has_changes is True when differences exist."""
    differ = SpecDiffer()
    result = differ.diff(str(spec_a), str(spec_b))

    assert result.has_changes is True


def test_diff_identical_specs(spec_a: Path) -> None:
    """No changes when comparing a spec to itself."""
    differ = SpecDiffer()
    result = differ.diff(str(spec_a), str(spec_a))

    assert result.has_changes is False
    assert len(result.changes) == 0


def test_diff_filter_by_section(spec_a: Path, spec_b: Path) -> None:
    """Can filter diff to specific sections."""
    differ = SpecDiffer()
    result = differ.diff(str(spec_a), str(spec_b), sections=["requirements"])

    sections = {c.section for c in result.changes}
    assert sections == {"requirements"}


def test_diff_nonexistent_spec_raises(tmp_path: Path) -> None:
    """DiffError raised for nonexistent spec directory."""
    differ = SpecDiffer()
    with pytest.raises(DiffError, match="not found"):
        differ.diff("/nonexistent/path", str(tmp_path))


def test_diff_missing_file_handled(tmp_path: Path) -> None:
    """Diff handles missing spec files gracefully."""
    spec_a = tmp_path / "spec-a"
    spec_a.mkdir()
    spec_b = tmp_path / "spec-b"
    spec_b.mkdir()

    (spec_b / "requirements.md").write_text(
        "# Requirements\n\n### FR-01: Login\nLogin feature.\n"
    )

    differ = SpecDiffer()
    result = differ.diff(str(spec_a), str(spec_b))

    assert len(result.added) == 1
    assert result.added[0].item_id == "FR-01"


def test_spec_diff_properties() -> None:
    """SpecDiff properties filter by change type correctly."""
    diff = SpecDiff(
        spec_a="a",
        spec_b="b",
        changes=[
            DiffEntry(section="requirements", change_type="added", item_id="FR-01"),
            DiffEntry(section="requirements", change_type="removed", item_id="FR-02"),
            DiffEntry(section="tasks", change_type="modified", item_id="1"),
        ],
    )

    assert len(diff.added) == 1
    assert len(diff.removed) == 1
    assert len(diff.modified) == 1
    assert diff.has_changes is True


def test_spec_diff_empty() -> None:
    """Empty SpecDiff has no changes."""
    diff = SpecDiff(spec_a="a", spec_b="b")
    assert diff.has_changes is False
    assert diff.added == []
    assert diff.removed == []
    assert diff.modified == []
