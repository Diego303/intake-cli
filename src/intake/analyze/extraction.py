"""Phase A — Extract structured requirements from raw LLM output.

Parses the JSON response from EXTRACTION_PROMPT into typed dataclasses.
"""

from __future__ import annotations

import structlog

from intake.analyze.models import (
    AnalysisResult,
    Conflict,
    OpenQuestion,
    Requirement,
)

logger = structlog.get_logger()


def parse_extraction(raw: dict[str, object]) -> AnalysisResult:
    """Parse the LLM JSON response into a typed AnalysisResult.

    Args:
        raw: Parsed JSON dict from the LLM extraction call.

    Returns:
        AnalysisResult populated with requirements, conflicts, and questions.
    """
    result = AnalysisResult()

    for item in _get_list(raw, "functional_requirements"):
        result.functional_requirements.append(_parse_requirement(item, "functional"))

    for item in _get_list(raw, "non_functional_requirements"):
        result.non_functional_requirements.append(
            _parse_requirement(item, "non_functional")
        )

    for item in _get_list(raw, "conflicts"):
        result.conflicts.append(_parse_conflict(item))

    for item in _get_list(raw, "open_questions"):
        result.open_questions.append(_parse_open_question(item))

    logger.info(
        "extraction_parsed",
        functional=len(result.functional_requirements),
        non_functional=len(result.non_functional_requirements),
        conflicts=len(result.conflicts),
        questions=len(result.open_questions),
    )

    return result


def _parse_requirement(item: dict[str, object], req_type: str) -> Requirement:
    """Parse a single requirement from the LLM output."""
    return Requirement(
        id=str(item.get("id", "")),
        type=req_type,
        title=str(item.get("title", "")),
        description=str(item.get("description", "")),
        acceptance_criteria=_get_str_list(item, "acceptance_criteria"),
        source=str(item.get("source", "")),
        priority=str(item.get("priority", "medium")),
    )


def _parse_conflict(item: dict[str, object]) -> Conflict:
    """Parse a single conflict from the LLM output."""
    source_a = item.get("source_a", {})
    source_b = item.get("source_b", {})

    return Conflict(
        id=str(item.get("id", "")),
        description=str(item.get("description", "")),
        source_a=_to_str_dict(source_a) if isinstance(source_a, dict) else {},
        source_b=_to_str_dict(source_b) if isinstance(source_b, dict) else {},
        recommendation=str(item.get("recommendation", "")),
        severity=str(item.get("severity", "medium")),
    )


def _parse_open_question(item: dict[str, object]) -> OpenQuestion:
    """Parse a single open question from the LLM output."""
    return OpenQuestion(
        id=str(item.get("id", "")),
        question=str(item.get("question", "")),
        context=str(item.get("context", "")),
        source=str(item.get("source", "")),
        recommendation=str(item.get("recommendation", "")),
    )


def _get_list(data: dict[str, object], key: str) -> list[dict[str, object]]:
    """Safely extract a list of dicts from a dict, returning empty list on failure."""
    value = data.get(key, [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _get_str_list(data: dict[str, object], key: str) -> list[str]:
    """Safely extract a list of strings from a dict."""
    value = data.get(key, [])
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _to_str_dict(data: dict[str, object]) -> dict[str, str]:
    """Convert a dict with mixed values to a dict with string values."""
    return {str(k): str(v) for k, v in data.items()}
