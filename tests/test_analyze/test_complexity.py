"""Tests for complexity classification."""

from __future__ import annotations

from intake.analyze.complexity import (
    ENTERPRISE_MIN_SOURCES,
    ENTERPRISE_MIN_WORDS,
    QUICK_MAX_WORDS,
    ComplexityAssessment,
    classify_complexity,
)
from intake.ingest.base import ParsedContent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_source(
    word_count: int = 100,
    fmt: str = "markdown",
    sections: int = 0,
) -> ParsedContent:
    """Create a ParsedContent with a specific word count."""
    words = " ".join(["word"] * word_count)
    section_list = [{"title": f"Section {i}", "content": "text"} for i in range(sections)]
    return ParsedContent(
        text=words,
        format=fmt,
        source=f"test_{fmt}.md",
        sections=section_list,
    )


# ---------------------------------------------------------------------------
# Tests — classify_complexity
# ---------------------------------------------------------------------------


class TestClassifyComplexity:
    def test_empty_sources_returns_quick(self) -> None:
        result = classify_complexity([])
        assert result.mode == "quick"
        assert result.total_words == 0
        assert result.source_count == 0
        assert result.confidence == 1.0

    def test_single_short_plaintext_is_quick(self) -> None:
        sources = [_make_source(word_count=100, fmt="plaintext")]
        result = classify_complexity(sources)
        assert result.mode == "quick"
        assert result.total_words == 100
        assert result.source_count == 1
        assert not result.has_structured_content

    def test_single_short_with_structure_is_standard(self) -> None:
        """Structured content bumps from quick to standard."""
        sources = [_make_source(word_count=100, fmt="markdown", sections=3)]
        result = classify_complexity(sources)
        assert result.mode == "standard"
        assert result.has_structured_content

    def test_single_short_jira_is_standard(self) -> None:
        """Jira format is inherently structured."""
        sources = [_make_source(word_count=100, fmt="jira")]
        result = classify_complexity(sources)
        assert result.mode == "standard"
        assert result.has_structured_content

    def test_boundary_quick_at_threshold(self) -> None:
        """Exactly at the quick threshold should still be quick (< not <=)."""
        sources = [_make_source(word_count=QUICK_MAX_WORDS - 1, fmt="plaintext")]
        result = classify_complexity(sources)
        assert result.mode == "quick"

    def test_boundary_quick_at_limit_is_standard(self) -> None:
        """At exactly QUICK_MAX_WORDS, should be standard."""
        sources = [_make_source(word_count=QUICK_MAX_WORDS, fmt="plaintext")]
        result = classify_complexity(sources)
        assert result.mode == "standard"

    def test_two_sources_moderate_words_is_standard(self) -> None:
        sources = [
            _make_source(word_count=300, fmt="markdown"),
            _make_source(word_count=400, fmt="pdf"),
        ]
        result = classify_complexity(sources)
        assert result.mode == "standard"
        assert result.has_multiple_formats

    def test_many_sources_is_enterprise(self) -> None:
        sources = [_make_source(word_count=200) for _ in range(ENTERPRISE_MIN_SOURCES)]
        result = classify_complexity(sources)
        assert result.mode == "enterprise"
        assert result.source_count == ENTERPRISE_MIN_SOURCES

    def test_high_word_count_is_enterprise(self) -> None:
        sources = [_make_source(word_count=ENTERPRISE_MIN_WORDS + 1)]
        result = classify_complexity(sources)
        assert result.mode == "enterprise"
        assert result.total_words > ENTERPRISE_MIN_WORDS

    def test_enterprise_by_source_count_takes_priority(self) -> None:
        """Even with few words, many sources triggers enterprise."""
        sources = [_make_source(word_count=50) for _ in range(5)]
        result = classify_complexity(sources)
        assert result.mode == "enterprise"

    def test_multiple_formats_detected(self) -> None:
        sources = [
            _make_source(fmt="markdown"),
            _make_source(fmt="jira"),
        ]
        result = classify_complexity(sources)
        assert result.has_multiple_formats

    def test_single_format_not_multiple(self) -> None:
        sources = [
            _make_source(fmt="markdown"),
            _make_source(fmt="markdown"),
        ]
        result = classify_complexity(sources)
        assert not result.has_multiple_formats

    def test_structured_format_detected(self) -> None:
        """Structured formats (jira, confluence, yaml, etc.) are detected."""
        for fmt in ["jira", "confluence", "yaml", "github_issues", "slack"]:
            sources = [_make_source(fmt=fmt)]
            result = classify_complexity(sources)
            assert result.has_structured_content, f"{fmt} should be structured"

    def test_reason_is_populated(self) -> None:
        result = classify_complexity([_make_source(word_count=50, fmt="plaintext")])
        assert len(result.reason) > 0

    def test_confidence_is_between_0_and_1(self) -> None:
        for sources in [
            [],
            [_make_source(word_count=50, fmt="plaintext")],
            [_make_source(word_count=1000, fmt="markdown", sections=5)],
            [_make_source(word_count=200) for _ in range(5)],
        ]:
            result = classify_complexity(sources)
            assert 0.0 <= result.confidence <= 1.0


# ---------------------------------------------------------------------------
# Tests — ComplexityAssessment dataclass
# ---------------------------------------------------------------------------


class TestComplexityAssessment:
    def test_dataclass_creation(self) -> None:
        assessment = ComplexityAssessment(
            mode="standard",
            total_words=1000,
            source_count=2,
            has_multiple_formats=True,
            has_structured_content=False,
            confidence=0.8,
            reason="test",
        )
        assert assessment.mode == "standard"
        assert assessment.total_words == 1000
        assert assessment.source_count == 2
        assert assessment.has_multiple_formats is True
        assert assessment.has_structured_content is False
        assert assessment.confidence == 0.8
        assert assessment.reason == "test"
