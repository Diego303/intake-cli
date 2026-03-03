"""Complexity classification for parsed sources.

Classifies a set of parsed sources into one of three complexity modes:
- quick: Simple, single-source input (<500 words, no structure)
- standard: Moderate complexity (default)
- enterprise: Complex, multi-source input (4+ sources or >5000 words)

This module has no LLM dependency — classification is purely heuristic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

import structlog

if TYPE_CHECKING:
    from intake.ingest.base import ParsedContent

logger = structlog.get_logger()

# Complexity mode type alias.
ComplexityMode = Literal["quick", "standard", "enterprise"]

# Thresholds for complexity classification.
QUICK_MAX_WORDS = 500
ENTERPRISE_MIN_WORDS = 5000
ENTERPRISE_MIN_SOURCES = 4

# Format types that indicate structured content.
STRUCTURED_FORMATS = frozenset(
    {
        "jira",
        "confluence",
        "yaml",
        "github_issues",
        "slack",
    }
)


@dataclass
class ComplexityAssessment:
    """Result of complexity classification.

    Attributes:
        mode: Classified complexity mode.
        total_words: Combined word count across all sources.
        source_count: Number of input sources.
        has_multiple_formats: Whether sources span different formats.
        has_structured_content: Whether any source has structured sections.
        confidence: Confidence in the classification (0.0-1.0).
        reason: Human-readable explanation of why this mode was chosen.
    """

    mode: ComplexityMode
    total_words: int
    source_count: int
    has_multiple_formats: bool
    has_structured_content: bool
    confidence: float
    reason: str


def classify_complexity(sources: list[ParsedContent]) -> ComplexityAssessment:
    """Classify the complexity of a set of parsed sources.

    Uses heuristics based on word count, source count, format diversity,
    and structural content to determine the appropriate generation mode.

    Classification rules (evaluated in order):
    1. Enterprise: 4+ sources OR >5000 total words
    2. Quick: 1 source AND <500 words AND no structured content
    3. Standard: everything else

    Args:
        sources: List of parsed content from the ingest phase.

    Returns:
        ComplexityAssessment with the classified mode and supporting metrics.
    """
    source_count = len(sources)
    total_words = sum(s.word_count for s in sources)
    formats = {s.format for s in sources}
    has_multiple_formats = len(formats) > 1
    has_structured_content = any(s.has_structure or s.format in STRUCTURED_FORMATS for s in sources)

    mode: ComplexityMode
    confidence: float
    reason: str

    if source_count == 0:
        mode = "quick"
        confidence = 1.0
        reason = "No sources provided"
    elif source_count >= ENTERPRISE_MIN_SOURCES:
        mode = "enterprise"
        confidence = 0.9
        reason = f"{source_count} sources (threshold: {ENTERPRISE_MIN_SOURCES})"
    elif total_words > ENTERPRISE_MIN_WORDS:
        mode = "enterprise"
        confidence = 0.85
        reason = f"{total_words} words exceeds {ENTERPRISE_MIN_WORDS} word threshold"
    elif source_count == 1 and total_words < QUICK_MAX_WORDS and not has_structured_content:
        mode = "quick"
        confidence = 0.9
        reason = f"Single source with {total_words} words, no structured content"
    else:
        mode = "standard"
        confidence = 0.8
        reason = _build_standard_reason(
            source_count, total_words, has_multiple_formats, has_structured_content
        )

    assessment = ComplexityAssessment(
        mode=mode,
        total_words=total_words,
        source_count=source_count,
        has_multiple_formats=has_multiple_formats,
        has_structured_content=has_structured_content,
        confidence=confidence,
        reason=reason,
    )

    logger.info(
        "complexity_classified",
        mode=mode,
        total_words=total_words,
        source_count=source_count,
        confidence=confidence,
        reason=reason,
    )

    return assessment


def _build_standard_reason(
    source_count: int,
    total_words: int,
    has_multiple_formats: bool,
    has_structured_content: bool,
) -> str:
    """Build a human-readable reason string for standard mode.

    Args:
        source_count: Number of input sources.
        total_words: Combined word count.
        has_multiple_formats: Whether multiple formats are present.
        has_structured_content: Whether structured content is present.

    Returns:
        Descriptive reason string.
    """
    parts: list[str] = [
        f"{source_count} source(s)",
        f"{total_words} words",
    ]

    if has_multiple_formats:
        parts.append("mixed formats")
    if has_structured_content:
        parts.append("structured content")

    return "Standard complexity: " + ", ".join(parts)
