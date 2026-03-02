"""Open questions validation and enrichment.

Validates open questions extracted by the LLM and filters out
low-quality or incomplete entries.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from intake.analyze.models import OpenQuestion

logger = structlog.get_logger()


def validate_questions(questions: list[OpenQuestion]) -> list[OpenQuestion]:
    """Validate and filter extracted open questions.

    Removes questions that lack essential fields (question text,
    context, or recommendation).

    Args:
        questions: Raw questions from the extraction phase.

    Returns:
        Filtered list of valid open questions.
    """
    valid: list[OpenQuestion] = []

    for question in questions:
        if _is_valid(question):
            valid.append(question)
        else:
            logger.debug(
                "question_filtered",
                id=question.id,
                reason="missing required fields",
            )

    filtered = len(questions) - len(valid)
    if filtered > 0:
        logger.info(
            "questions_validated",
            total=len(questions),
            valid=len(valid),
            filtered=filtered,
        )

    return valid


def _is_valid(question: OpenQuestion) -> bool:
    """Check that a question has all required fields populated."""
    if not question.question.strip():
        return False
    return bool(question.context.strip())
