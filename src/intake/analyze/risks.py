"""Risk assessment — parses LLM risk analysis into typed models.

Called after extraction when config.spec.risk_assessment is True.
"""

from __future__ import annotations

import structlog

from intake.analyze.models import RiskItem

logger = structlog.get_logger()


def parse_risks(raw: dict[str, object]) -> list[RiskItem]:
    """Parse the LLM risk assessment response into typed RiskItem list.

    Args:
        raw: Parsed JSON dict from the LLM risk assessment call.

    Returns:
        List of validated RiskItem instances.
    """
    items: list[RiskItem] = []

    for entry in _get_list(raw, "risks"):
        risk = _parse_risk_item(entry)
        if _is_valid(risk):
            items.append(risk)
        else:
            logger.debug(
                "risk_filtered",
                id=risk.id,
                reason="missing required fields",
            )

    logger.info("risks_parsed", count=len(items))
    return items


def _parse_risk_item(item: dict[str, object]) -> RiskItem:
    """Parse a single risk item from the LLM output."""
    req_ids = item.get("requirement_ids", [])
    if not isinstance(req_ids, list):
        req_ids = []

    return RiskItem(
        id=str(item.get("id", "")),
        requirement_ids=[str(r) for r in req_ids],
        description=str(item.get("description", "")),
        probability=str(item.get("probability", "medium")),
        impact=str(item.get("impact", "medium")),
        mitigation=str(item.get("mitigation", "")),
        category=str(item.get("category", "technical")),
    )


def _is_valid(risk: RiskItem) -> bool:
    """Check that a risk has all required fields populated."""
    if not risk.description.strip():
        return False
    return bool(risk.mitigation.strip())


def _get_list(data: dict[str, object], key: str) -> list[dict[str, object]]:
    """Safely extract a list from a dict, returning empty list on failure."""
    value = data.get(key, [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
