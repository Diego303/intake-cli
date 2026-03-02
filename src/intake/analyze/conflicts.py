"""Conflict validation and enrichment.

Validates conflicts extracted by the LLM and filters out
low-quality or incomplete entries.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from intake.analyze.models import Conflict

logger = structlog.get_logger()


def validate_conflicts(conflicts: list[Conflict]) -> list[Conflict]:
    """Validate and filter extracted conflicts.

    Removes conflicts that lack essential fields (description,
    source references, or recommendation).

    Args:
        conflicts: Raw conflicts from the extraction phase.

    Returns:
        Filtered list of valid conflicts.
    """
    valid: list[Conflict] = []

    for conflict in conflicts:
        if _is_valid(conflict):
            valid.append(conflict)
        else:
            logger.debug(
                "conflict_filtered",
                id=conflict.id,
                reason="missing required fields",
            )

    filtered = len(conflicts) - len(valid)
    if filtered > 0:
        logger.info(
            "conflicts_validated",
            total=len(conflicts),
            valid=len(valid),
            filtered=filtered,
        )

    return valid


def _is_valid(conflict: Conflict) -> bool:
    """Check that a conflict has all required fields populated."""
    if not conflict.description.strip():
        return False
    if not conflict.source_a:
        return False
    if not conflict.source_b:
        return False
    return bool(conflict.recommendation.strip())
