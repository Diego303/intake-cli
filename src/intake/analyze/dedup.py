"""Deduplication of requirements across multiple sources.

Uses title similarity (normalized lowercase comparison) to detect
duplicates within the same type (functional or non-functional).
Keeps the first occurrence and removes subsequent duplicates.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from intake.analyze.models import AnalysisResult, Requirement

logger = structlog.get_logger()

# Minimum similarity ratio (0.0-1.0) to consider two requirements as duplicates.
# Set at 0.75 for word-level Jaccard similarity (where small differences in
# token count have a large impact on the ratio).
SIMILARITY_THRESHOLD = 0.75


def deduplicate(result: AnalysisResult) -> int:
    """Remove duplicate requirements from the analysis result.

    Modifies the result in place by removing duplicates from both
    functional and non-functional requirement lists.

    Args:
        result: The analysis result to deduplicate.

    Returns:
        Number of duplicates removed.
    """
    fr_before = len(result.functional_requirements)
    nfr_before = len(result.non_functional_requirements)

    result.functional_requirements = _deduplicate_list(
        result.functional_requirements
    )
    result.non_functional_requirements = _deduplicate_list(
        result.non_functional_requirements
    )

    removed = (fr_before - len(result.functional_requirements)) + (
        nfr_before - len(result.non_functional_requirements)
    )

    if removed > 0:
        logger.info("dedup_complete", duplicates_removed=removed)

    return removed


def _deduplicate_list(requirements: list[Requirement]) -> list[Requirement]:
    """Remove duplicates from a list of requirements.

    Keeps the first occurrence of each unique requirement.
    Two requirements are considered duplicates if their normalized
    titles are similar above the threshold.
    """
    if not requirements:
        return requirements

    unique: list[Requirement] = []
    seen_titles: list[str] = []

    for req in requirements:
        normalized = _normalize(req.title)
        if not _is_duplicate(normalized, seen_titles):
            unique.append(req)
            seen_titles.append(normalized)

    return unique


def _is_duplicate(title: str, seen: list[str]) -> bool:
    """Check if a normalized title is similar to any previously seen title."""
    return any(_similarity(title, seen_title) >= SIMILARITY_THRESHOLD for seen_title in seen)


def _normalize(text: str) -> str:
    """Normalize text for comparison: lowercase, strip, collapse whitespace."""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _similarity(a: str, b: str) -> float:
    """Compute similarity ratio between two strings.

    Uses token overlap (Jaccard similarity on words) for a lightweight,
    dependency-free comparison.

    Returns:
        Float between 0.0 and 1.0 where 1.0 is identical.
    """
    if a == b:
        return 1.0

    tokens_a = set(a.split())
    tokens_b = set(b.split())

    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0

    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b

    return len(intersection) / len(union)
