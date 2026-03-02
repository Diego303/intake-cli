"""Tests for analyze/conflicts.py — conflict validation."""

from __future__ import annotations

from intake.analyze.conflicts import validate_conflicts
from intake.analyze.models import Conflict


def _make_conflict(
    id: str = "CONFLICT-01",
    description: str = "Auth method disagreement",
    source_a: dict[str, str] | None = None,
    source_b: dict[str, str] | None = None,
    recommendation: str = "Use JWT",
    severity: str = "medium",
) -> Conflict:
    """Create a test conflict."""
    return Conflict(
        id=id,
        description=description,
        source_a={"source": "Source 1", "says": "Use JWT"} if source_a is None else source_a,
        source_b={"source": "Source 2", "says": "Use sessions"} if source_b is None else source_b,
        recommendation=recommendation,
        severity=severity,
    )


class TestValidateConflicts:
    """Tests for validate_conflicts()."""

    def test_keeps_valid_conflict(self) -> None:
        conflicts = [_make_conflict()]
        result = validate_conflicts(conflicts)
        assert len(result) == 1

    def test_filters_empty_description(self) -> None:
        conflicts = [_make_conflict(description="")]
        result = validate_conflicts(conflicts)
        assert len(result) == 0

    def test_filters_empty_source_a(self) -> None:
        conflicts = [_make_conflict(source_a={})]
        result = validate_conflicts(conflicts)
        assert len(result) == 0

    def test_filters_empty_source_b(self) -> None:
        conflicts = [_make_conflict(source_b={})]
        result = validate_conflicts(conflicts)
        assert len(result) == 0

    def test_filters_empty_recommendation(self) -> None:
        conflicts = [_make_conflict(recommendation="")]
        result = validate_conflicts(conflicts)
        assert len(result) == 0

    def test_mixed_valid_and_invalid(self) -> None:
        conflicts = [
            _make_conflict(id="C-01"),
            _make_conflict(id="C-02", description=""),
            _make_conflict(id="C-03"),
        ]
        result = validate_conflicts(conflicts)
        assert len(result) == 2
        assert result[0].id == "C-01"
        assert result[1].id == "C-03"

    def test_empty_list(self) -> None:
        result = validate_conflicts([])
        assert result == []
