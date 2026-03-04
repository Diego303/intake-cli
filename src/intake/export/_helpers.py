"""Shared utilities for spec exporters.

Provides common functions for reading spec files, parsing tasks
from tasks.md, loading acceptance checks, and summarizing content.
These are used by multiple exporters to avoid code duplication.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import structlog
import yaml

if TYPE_CHECKING:
    from pathlib import Path

logger = structlog.get_logger()


def read_spec_file(spec_path: Path, filename: str) -> str:
    """Read a spec file, returning empty string if missing.

    Args:
        spec_path: Path to the spec directory.
        filename: Name of the file to read.

    Returns:
        File content or empty string.
    """
    fpath = spec_path / filename
    if not fpath.exists():
        return ""
    return fpath.read_text(errors="ignore")


def parse_tasks(tasks_content: str) -> list[dict[str, str]]:
    """Parse tasks.md content and extract structured tasks.

    Extracts task ID, title, description, and status from markdown
    headings matching: ``### Task N: Title`` or ``### N: Title``

    Args:
        tasks_content: Raw tasks.md content.

    Returns:
        List of task dicts with id, title, description, status keys.
    """
    if not tasks_content.strip():
        return []

    tasks: list[dict[str, str]] = []
    current_task: dict[str, str] | None = None
    description_lines: list[str] = []

    for line in tasks_content.splitlines():
        match = re.match(
            r"^###?\s+(?:Task\s+)?(\d+)[:.]\s*(.*)",
            line,
            re.IGNORECASE,
        )
        if match:
            if current_task is not None:
                current_task["description"] = "\n".join(description_lines).strip()
                tasks.append(current_task)

            current_task = {
                "id": match.group(1),
                "title": match.group(2).strip(),
                "description": "",
                "status": "pending",
            }
            description_lines = []
        elif current_task is not None:
            # Detect status from content
            status_match = re.match(
                r"\*\*Status:\*\*\s*(\w+)",
                line,
            )
            if status_match:
                current_task["status"] = status_match.group(1).lower()

            if re.match(r"^#{1,2}\s+", line):
                current_task["description"] = "\n".join(description_lines).strip()
                tasks.append(current_task)
                current_task = None
                description_lines = []
            else:
                description_lines.append(line)

    if current_task is not None:
        current_task["description"] = "\n".join(description_lines).strip()
        tasks.append(current_task)

    return tasks


def load_acceptance_checks(spec_path: Path) -> list[dict[str, object]]:
    """Load acceptance checks from acceptance.yaml.

    Args:
        spec_path: Path to the spec directory.

    Returns:
        List of check definitions.
    """
    acceptance_path = spec_path / "acceptance.yaml"
    if not acceptance_path.exists():
        return []
    try:
        with open(acceptance_path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError:
        return []
    if not isinstance(data, dict):
        return []
    checks = data.get("checks", [])
    return checks if isinstance(checks, list) else []


def summarize_content(content: str, max_lines: int = 30) -> str:
    """Summarize text content to fit in a limited context.

    Args:
        content: Full text content.
        max_lines: Maximum number of lines to keep.

    Returns:
        Truncated content with ellipsis if needed.
    """
    lines = content.splitlines()
    if len(lines) <= max_lines:
        return content
    remaining = len(lines) - max_lines
    return "\n".join(lines[:max_lines]) + f"\n\n... ({remaining} more lines)"


def count_requirements(requirements_content: str) -> int:
    """Count requirement entries in requirements.md.

    Counts headings that match ``### FR-NNN`` or ``### NFR-NNN`` patterns.

    Args:
        requirements_content: Raw requirements.md content.

    Returns:
        Number of requirements found.
    """
    if not requirements_content:
        return 0
    return len(re.findall(r"^###\s+(?:N?FR-\d+|REQ-\d+)", requirements_content, re.MULTILINE))
