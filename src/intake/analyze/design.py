"""Design phase — parses LLM design output into typed models.

Converts the DESIGN_PROMPT JSON response into DesignResult with
components, file actions, tech decisions, tasks, and acceptance checks.
"""

from __future__ import annotations

import structlog

from intake.analyze.models import (
    AcceptanceCheck,
    DesignResult,
    FileAction,
    TaskItem,
    TechDecision,
)

logger = structlog.get_logger()


def parse_design(raw: dict[str, object]) -> DesignResult:
    """Parse the LLM design response into a typed DesignResult.

    Args:
        raw: Parsed JSON dict from the LLM design call.

    Returns:
        DesignResult populated with components, files, tasks, and checks.
    """
    result = DesignResult()

    # Components
    components = raw.get("components", [])
    if isinstance(components, list):
        result.components = [str(c) for c in components]

    # Files to create
    for item in _get_list(raw, "files_to_create"):
        result.files_to_create.append(
            FileAction(
                path=str(item.get("path", "")),
                description=str(item.get("description", "")),
                action="create",
            )
        )

    # Files to modify
    for item in _get_list(raw, "files_to_modify"):
        result.files_to_modify.append(
            FileAction(
                path=str(item.get("path", "")),
                description=str(item.get("description", item.get("changes", ""))),
                action="modify",
            )
        )

    # Tech decisions
    for item in _get_list(raw, "tech_decisions"):
        result.tech_decisions.append(
            TechDecision(
                decision=str(item.get("decision", "")),
                justification=str(item.get("justification", "")),
                requirement=str(item.get("requirement", "")),
            )
        )

    # Tasks
    for item in _get_list(raw, "tasks"):
        result.tasks.append(_parse_task(item))

    # Acceptance checks
    for item in _get_list(raw, "acceptance_checks"):
        result.acceptance_checks.append(_parse_check(item))

    # Dependencies
    deps = raw.get("dependencies", [])
    if isinstance(deps, list):
        result.dependencies = [str(d) for d in deps]

    logger.info(
        "design_parsed",
        components=len(result.components),
        files_create=len(result.files_to_create),
        files_modify=len(result.files_to_modify),
        tasks=len(result.tasks),
        checks=len(result.acceptance_checks),
    )

    return result


def _parse_task(item: dict[str, object]) -> TaskItem:
    """Parse a single task from the LLM output."""
    files = item.get("files", [])
    deps = item.get("dependencies", [])
    checks = item.get("checks", [])

    raw_id = item.get("id", 0)
    raw_minutes = item.get("estimated_minutes", 15)
    return TaskItem(
        id=int(raw_id) if isinstance(raw_id, (int, float, str)) else 0,
        title=str(item.get("title", "")),
        description=str(item.get("description", "")),
        files=[str(f) for f in files] if isinstance(files, list) else [],
        dependencies=[int(d) for d in deps] if isinstance(deps, list) else [],
        checks=[str(c) for c in checks] if isinstance(checks, list) else [],
        estimated_minutes=int(raw_minutes) if isinstance(raw_minutes, (int, float, str)) else 15,
    )


def _parse_check(item: dict[str, object]) -> AcceptanceCheck:
    """Parse a single acceptance check from the LLM output."""
    tags = item.get("tags", [])
    paths = item.get("paths", [])
    patterns = item.get("patterns", [])

    return AcceptanceCheck(
        id=str(item.get("id", "")),
        name=str(item.get("name", "")),
        type=str(item.get("type", "command")),
        required=bool(item.get("required", True)),
        tags=[str(t) for t in tags] if isinstance(tags, list) else [],
        command=str(item.get("command", "")),
        paths=[str(p) for p in paths] if isinstance(paths, list) else [],
        glob=str(item.get("glob", "")),
        patterns=[str(p) for p in patterns] if isinstance(patterns, list) else [],
    )


def _get_list(data: dict[str, object], key: str) -> list[dict[str, object]]:
    """Safely extract a list from a dict, returning empty list on failure."""
    value = data.get(key, [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
