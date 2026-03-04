"""Tests for the spec updater."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from intake.feedback.analyzer import (
    FailureAnalysis,
    FeedbackResult,
    SpecAmendment,
)
from intake.feedback.spec_updater import SpecUpdateError, SpecUpdater

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def spec_dir(tmp_path: Path) -> Path:
    """Create a sample spec directory."""
    spec = tmp_path / "test-spec"
    spec.mkdir()
    (spec / "requirements.md").write_text(
        "# Requirements\n\n"
        "### FR-001: User login\n\nUser can log in with email.\n\n"
        "### FR-002: User logout\n\nUser can log out.\n"
    )
    (spec / "tasks.md").write_text("# Tasks\n\n### Task 1: Setup\n\n")
    return spec


def _make_result(
    target_file: str = "requirements.md",
    section: str = "FR-001",
    action: str = "modify",
    content: str = "### FR-001: User login\n\nUpdated login requirement.\n",
) -> FeedbackResult:
    """Create a FeedbackResult with one amendment."""
    return FeedbackResult(
        failures=[
            FailureAnalysis(
                check_name="Test check",
                root_cause="Issue found",
                suggestion="Fix it",
                spec_amendment=SpecAmendment(
                    target_file=target_file,
                    section=section,
                    action=action,
                    content=content,
                ),
            ),
        ],
    )


class TestSpecUpdaterInit:
    def test_valid_spec_dir(self, spec_dir: Path) -> None:
        """Updater initializes with valid spec directory."""
        updater = SpecUpdater(str(spec_dir))
        assert updater.spec_path == spec_dir

    def test_invalid_spec_dir(self, tmp_path: Path) -> None:
        """Updater raises error for nonexistent directory."""
        with pytest.raises(SpecUpdateError, match="not found"):
            SpecUpdater(str(tmp_path / "nonexistent"))


class TestSpecUpdaterPreview:
    def test_preview_modify(self, spec_dir: Path) -> None:
        """Preview for modify shows current and proposed content."""
        updater = SpecUpdater(str(spec_dir))
        result = _make_result()
        previews = updater.preview(result)

        assert len(previews) == 1
        assert previews[0].applicable is True
        assert "FR-001" in previews[0].current_content
        assert "Updated login" in previews[0].proposed_content

    def test_preview_add(self, spec_dir: Path) -> None:
        """Preview for add shows new content."""
        updater = SpecUpdater(str(spec_dir))
        result = _make_result(
            section="FR-003",
            action="add",
            content="### FR-003: Password reset\n\nUser can reset password.\n",
        )
        previews = updater.preview(result)

        assert len(previews) == 1
        assert previews[0].applicable is True

    def test_preview_remove(self, spec_dir: Path) -> None:
        """Preview for remove shows section to be removed."""
        updater = SpecUpdater(str(spec_dir))
        result = _make_result(action="remove")
        previews = updater.preview(result)

        assert len(previews) == 1
        assert previews[0].applicable is True

    def test_preview_missing_file(self, spec_dir: Path) -> None:
        """Preview for nonexistent file shows not applicable."""
        updater = SpecUpdater(str(spec_dir))
        result = _make_result(target_file="nonexistent.md", action="modify")
        previews = updater.preview(result)

        assert len(previews) == 1
        assert previews[0].applicable is False

    def test_preview_no_amendments(self, spec_dir: Path) -> None:
        """Preview returns empty for result with no amendments."""
        updater = SpecUpdater(str(spec_dir))
        result = FeedbackResult(
            failures=[
                FailureAnalysis(check_name="a", root_cause="x", suggestion="y"),
            ],
        )
        previews = updater.preview(result)
        assert len(previews) == 0


class TestSpecUpdaterApply:
    def test_apply_modify(self, spec_dir: Path) -> None:
        """Apply modify updates the section content."""
        updater = SpecUpdater(str(spec_dir))
        result = _make_result()
        apply_result = updater.apply(result)

        assert apply_result.applied == 1
        assert apply_result.skipped == 0

        content = (spec_dir / "requirements.md").read_text()
        assert "Updated login" in content

    def test_apply_add(self, spec_dir: Path) -> None:
        """Apply add appends new content."""
        updater = SpecUpdater(str(spec_dir))
        result = _make_result(
            section="FR-003",
            action="add",
            content="### FR-003: Password reset\n\nNew feature.\n",
        )
        apply_result = updater.apply(result)

        assert apply_result.applied == 1
        content = (spec_dir / "requirements.md").read_text()
        assert "FR-003" in content

    def test_apply_remove(self, spec_dir: Path) -> None:
        """Apply remove deletes the section."""
        updater = SpecUpdater(str(spec_dir))
        result = _make_result(action="remove")
        apply_result = updater.apply(result)

        assert apply_result.applied == 1
        content = (spec_dir / "requirements.md").read_text()
        assert "FR-001" not in content
        assert "FR-002" in content  # Other sections preserved

    def test_apply_skips_inapplicable(self, spec_dir: Path) -> None:
        """Apply skips amendments that cannot be applied."""
        updater = SpecUpdater(str(spec_dir))
        result = _make_result(
            target_file="nonexistent.md",
            action="modify",
        )
        apply_result = updater.apply(result)

        assert apply_result.skipped == 1
        assert apply_result.applied == 0

    def test_apply_add_creates_new_file(self, spec_dir: Path) -> None:
        """Apply add to nonexistent file creates it."""
        updater = SpecUpdater(str(spec_dir))
        result = _make_result(
            target_file="new_file.md",
            action="add",
            content="# New Content\n\nSome text.\n",
        )
        apply_result = updater.apply(result)

        assert apply_result.applied == 1
        new_file = spec_dir / "new_file.md"
        assert new_file.exists()
        assert "New Content" in new_file.read_text()
