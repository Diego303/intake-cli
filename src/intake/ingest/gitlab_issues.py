"""Parser for GitLab Issues JSON exports.

Supports: JSON files produced by the GitLab connector or the GitLab API directly.
          Accepts a single issue object, an array of issues, or a wrapped
          ``{"issues": [...]}`` format.
Extracts: Issue titles, descriptions, labels, milestones, weights, assignees,
          task completion status, discussion notes, and linked merge requests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog

from intake.ingest.base import (
    ParsedContent,
    ParseError,
    read_text_safe,
    validate_file_readable,
)

logger = structlog.get_logger()

# Maximum length for a single discussion note body.
MAX_NOTE_LENGTH = 500


class GitlabIssuesParser:
    """Parser for GitLab Issues JSON exports.

    Supports:
    - Single issue object: ``{"iid": 1, "title": "...", ...}``
    - Array of issues: ``[{"iid": 1, ...}, {"iid": 2, ...}]``
    - Wrapped format: ``{"issues": [{"iid": 1, ...}]}``

    Extracts:
    - Issue title, description, and state
    - Labels, milestone, weight, assignees
    - Task completion status (checkbox progress)
    - Discussion notes (non-system)
    - Linked merge requests as relations
    """

    # ------------------------------------------------------------------
    # Protocol methods
    # ------------------------------------------------------------------

    def can_parse(self, source: str) -> bool:
        """Return True if *source* is a JSON file with GitLab Issues structure."""
        path = Path(source)
        if not path.exists() or not path.is_file() or path.suffix.lower() != ".json":
            return False
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return self._is_gitlab_issue(data)
        except (json.JSONDecodeError, OSError):
            return False

    def parse(self, source: str) -> ParsedContent:
        """Parse a GitLab Issues JSON export into normalised content.

        Args:
            source: Path to the GitLab Issues JSON file.

        Returns:
            ParsedContent with format ``"gitlab_issues"``, one section
            per issue, and relations for linked merge requests.

        Raises:
            ParseError: If the file cannot be read, is not valid JSON,
                        or contains no issues.
        """
        path = validate_file_readable(source)
        raw = read_text_safe(source, path)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ParseError(
                source=source,
                reason=f"Invalid JSON: {exc}",
                suggestion="Verify the file is a valid GitLab Issues JSON export.",
            ) from exc

        issues = self._normalize_input(data)
        if not issues:
            raise ParseError(
                source=source,
                reason="No GitLab issues found in the file",
                suggestion=(
                    "Verify the JSON contains objects with 'iid' and "
                    "'title' fields (single object or array)."
                ),
            )

        text_parts: list[str] = []
        sections: list[dict[str, str]] = []
        relations: list[dict[str, str]] = []
        metadata: dict[str, str] = {}

        for issue in issues:
            section_text = self._format_issue(issue)
            text_parts.append(section_text)

            iid = issue.get("iid", "?")
            title = issue.get("title", "Untitled")
            sections.append(
                {
                    "title": f"#{iid}: {title}",
                    "content": section_text,
                }
            )

            # Collect merge request relations
            for mr in issue.get("merge_requests", []):
                mr_iid = mr.get("iid", "?")
                relations.append(
                    {
                        "type": "merge_request",
                        "direction": "outward",
                        "target": f"!{mr_iid}",
                    }
                )

        full_text = "\n\n---\n\n".join(text_parts)
        metadata["source_type"] = "gitlab"
        metadata["issue_count"] = str(len(issues))
        if issues and issues[0].get("_project_path"):
            metadata["project"] = issues[0]["_project_path"]

        logger.info(
            "gitlab_issues_parsed",
            source=source,
            issues=len(issues),
            relations=len(relations),
        )

        return ParsedContent(
            text=full_text,
            format="gitlab_issues",
            source=source,
            metadata=metadata,
            sections=sections,
            relations=relations,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_gitlab_issue(self, data: object) -> bool:
        """Return True if *data* matches the GitLab Issues structure."""
        if isinstance(data, dict):
            # Wrapped format: {"issues": [...]}
            if "issues" in data and isinstance(data["issues"], list):
                items = data["issues"]
                if items and isinstance(items[0], dict):
                    return "iid" in items[0]
            return "iid" in data and ("web_url" in data or "title" in data)
        if isinstance(data, list) and len(data) > 0:
            first = data[0]
            if isinstance(first, dict):
                return "iid" in first and ("web_url" in first or "title" in first)
        return False

    def _normalize_input(self, data: object) -> list[dict[str, Any]]:
        """Normalise various input shapes to a list of issue dicts."""
        if isinstance(data, dict):
            if "iid" in data:
                return [data]
            if "issues" in data and isinstance(data["issues"], list):
                return [item for item in data["issues"] if isinstance(item, dict) and "iid" in item]
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict) and "iid" in item]
        return []

    def _format_issue(self, issue: dict[str, Any]) -> str:
        """Format a single GitLab issue as readable Markdown text."""
        iid = issue.get("iid", "?")
        title = issue.get("title", "Untitled")
        description = issue.get("description", "") or ""
        state = issue.get("state", "opened")
        milestone = issue.get("milestone")
        weight = issue.get("weight")
        labels = issue.get("labels", [])
        assignees = issue.get("assignees", [])
        project = issue.get("_project_path", "")

        lines: list[str] = [f"## #{iid}: {title}", ""]

        if project:
            lines.append(f"**Project:** {project}")

        state_line = f"**State:** {state}"
        if milestone:
            state_line += f" | **Milestone:** {milestone}"
        if weight is not None:
            state_line += f" | **Weight:** {weight}"
        lines.append(state_line)

        if labels:
            lines.append(f"**Labels:** {', '.join(str(lbl) for lbl in labels)}")
        if assignees:
            lines.append(f"**Assignees:** {', '.join(str(a) for a in assignees)}")

        # Task completion status
        task_status = issue.get("task_completion_status")
        if isinstance(task_status, dict):
            completed = task_status.get("completed_count", 0)
            total = task_status.get("count", 0)
            if total > 0:
                lines.append(f"**Tasks:** {completed}/{total} completed")

        lines.append("")

        if description:
            lines.append(description)

        # Discussion notes (non-system)
        notes = issue.get("notes", [])
        if notes:
            lines.append("")
            lines.append("### Discussion")
            lines.append("")
            for note in notes:
                if not isinstance(note, dict):
                    continue
                author = note.get("author", "unknown")
                body = (note.get("body", "") or "")[:MAX_NOTE_LENGTH]
                lines.append(f"- **{author}**: {body}")

        # Linked merge requests
        mrs = issue.get("merge_requests", [])
        if mrs:
            lines.append("")
            lines.append("### Linked Merge Requests")
            lines.append("")
            for mr in mrs:
                if not isinstance(mr, dict):
                    continue
                mr_iid = mr.get("iid", "?")
                mr_title = mr.get("title", "")
                mr_state = mr.get("state", "")
                lines.append(f"- !{mr_iid}: {mr_title} ({mr_state})")

        return "\n".join(lines)
