"""Tests for analyze/dedup.py — requirement deduplication."""

from __future__ import annotations

from intake.analyze.dedup import _normalize, _similarity, deduplicate
from intake.analyze.models import AnalysisResult, Requirement


def _make_req(id: str, title: str, req_type: str = "functional") -> Requirement:
    """Create a test requirement with the given id and title."""
    return Requirement(
        id=id,
        type=req_type,
        title=title,
        description=f"Description for {title}",
        acceptance_criteria=["AC-1"],
        source="Source 1",
    )


class TestNormalize:
    """Tests for _normalize()."""

    def test_lowercases(self) -> None:
        assert _normalize("User LOGIN") == "user login"

    def test_strips_whitespace(self) -> None:
        assert _normalize("  user login  ") == "user login"

    def test_collapses_multiple_spaces(self) -> None:
        assert _normalize("user   login   feature") == "user login feature"


class TestSimilarity:
    """Tests for _similarity()."""

    def test_identical_strings(self) -> None:
        assert _similarity("user login", "user login") == 1.0

    def test_completely_different(self) -> None:
        assert _similarity("user login", "payment gateway") == 0.0

    def test_partial_overlap(self) -> None:
        score = _similarity("user login feature", "user login")
        assert 0.5 < score < 1.0

    def test_empty_strings(self) -> None:
        assert _similarity("", "") == 1.0

    def test_one_empty(self) -> None:
        assert _similarity("user login", "") == 0.0


class TestDeduplicate:
    """Tests for deduplicate()."""

    def test_removes_exact_duplicates(self) -> None:
        result = AnalysisResult(
            functional_requirements=[
                _make_req("FR-01", "User login"),
                _make_req("FR-02", "User login"),
            ]
        )
        removed = deduplicate(result)
        assert removed == 1
        assert len(result.functional_requirements) == 1
        assert result.functional_requirements[0].id == "FR-01"

    def test_removes_near_duplicates(self) -> None:
        result = AnalysisResult(
            functional_requirements=[
                _make_req("FR-01", "User login authentication feature"),
                _make_req("FR-02", "User login authentication"),
            ]
        )
        removed = deduplicate(result)
        assert removed == 1

    def test_keeps_distinct_requirements(self) -> None:
        result = AnalysisResult(
            functional_requirements=[
                _make_req("FR-01", "User login"),
                _make_req("FR-02", "Payment processing"),
            ]
        )
        removed = deduplicate(result)
        assert removed == 0
        assert len(result.functional_requirements) == 2

    def test_deduplicates_nonfunctional_separately(self) -> None:
        result = AnalysisResult(
            non_functional_requirements=[
                _make_req("NFR-01", "Response time under 200ms", "non_functional"),
                _make_req("NFR-02", "Response time under 200ms", "non_functional"),
            ]
        )
        removed = deduplicate(result)
        assert removed == 1
        assert len(result.non_functional_requirements) == 1

    def test_empty_list(self) -> None:
        result = AnalysisResult()
        removed = deduplicate(result)
        assert removed == 0

    def test_returns_total_removed_across_both_lists(self) -> None:
        result = AnalysisResult(
            functional_requirements=[
                _make_req("FR-01", "User login"),
                _make_req("FR-02", "User login"),
            ],
            non_functional_requirements=[
                _make_req("NFR-01", "Performance", "non_functional"),
                _make_req("NFR-02", "Performance", "non_functional"),
            ],
        )
        removed = deduplicate(result)
        assert removed == 2
