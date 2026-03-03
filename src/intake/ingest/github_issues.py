"""Parser for GitHub Issues JSON exports.

Supports: JSON files exported from the GitHub REST API or ``gh`` CLI.
          Accepts both a single issue object and an array of issues.
Extracts: Issue titles, bodies, labels, milestones, comments, assignees,
          and cross-references between issues.
"""

from __future__ import annotations

import json
import re
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

# Matches GitHub-style issue cross-references: #123
_CROSS_REF_PATTERN: re.Pattern[str] = re.compile(r"#(\d+)")


class GithubIssuesParser:
    """Parser for GitHub Issues JSON exports.

    Supports:
    - Single issue object: ``{"number": 1, "title": "...", ...}``
    - Array of issues: ``[{"number": 1, ...}, {"number": 2, ...}]``

    Extracts:
    - Issue title, body, and state
    - Labels as metadata and inline badges
    - Milestone information
    - Assignee logins
    - Comments (if included in ``comments_data``)
    - Cross-references (``#NNN``) as relations
    """

    # ------------------------------------------------------------------
    # Protocol methods
    # ------------------------------------------------------------------

    def can_parse(self, source: str) -> bool:
        """Return True if *source* is a JSON file with GitHub Issues structure."""
        path = Path(source)
        if not path.exists() or not path.is_file() or path.suffix.lower() != ".json":
            return False
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return self._is_github_issues(data)
        except (json.JSONDecodeError, OSError):
            return False

    def parse(self, source: str) -> ParsedContent:
        """Parse a GitHub Issues JSON export into normalised content.

        Args:
            source: Path to the GitHub Issues JSON file.

        Returns:
            ParsedContent with format ``"github_issues"``, one section
            per issue, and relations for cross-references.

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
                suggestion="Verify the file is a valid GitHub Issues JSON export.",
            ) from exc

        issues = self._extract_issues(data)
        if not issues:
            raise ParseError(
                source=source,
                reason="No GitHub issues found in the file",
                suggestion=(
                    "Verify the JSON contains objects with 'number' and "
                    "'title' fields (single object or array)."
                ),
            )

        text_parts: list[str] = []
        sections: list[dict[str, str]] = []
        relations: list[dict[str, str]] = []
        all_labels: set[str] = set()

        for issue in issues:
            number = issue.get("number", 0)
            section_text = self._format_issue(issue)
            text_parts.append(section_text)

            title = issue.get("title", "Untitled")
            sections.append(
                {
                    "title": f"#{number}: {title}",
                    "content": section_text,
                }
            )

            # Collect labels
            for label in self._extract_label_names(issue):
                all_labels.add(label)

            # Collect cross-references as relations
            for ref_number in self._extract_cross_references(issue):
                relations.append(
                    {
                        "type": "references",
                        "source": f"#{number}",
                        "target": f"#{ref_number}",
                    }
                )

        full_text = "\n\n---\n\n".join(text_parts)

        metadata: dict[str, str] = {
            "source_type": "github_issues",
            "issue_count": str(len(issues)),
        }
        if all_labels:
            metadata["labels"] = ", ".join(sorted(all_labels))

        milestone = self._extract_milestone(issues)
        if milestone:
            metadata["milestone"] = milestone

        logger.info(
            "github_issues_parsed",
            source=source,
            issues=len(issues),
            labels=len(all_labels),
            relations=len(relations),
        )

        return ParsedContent(
            text=full_text,
            format="github_issues",
            source=source,
            metadata=metadata,
            sections=sections,
            relations=relations,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_github_issues(self, data: object) -> bool:
        """Return True if *data* matches the GitHub Issues structure."""
        if isinstance(data, dict):
            return "number" in data and (
                "html_url" in data or ("title" in data and "labels" in data)
            )
        if isinstance(data, list) and len(data) > 0:
            first = data[0]
            if isinstance(first, dict):
                return "number" in first and (
                    "html_url" in first or ("title" in first and "labels" in first)
                )
        return False

    def _extract_issues(self, data: object) -> list[dict[str, Any]]:
        """Normalise *data* into a list of issue dicts."""
        if isinstance(data, dict) and "number" in data:
            return [data]
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict) and "number" in item]
        return []

    def _format_issue(self, issue: dict[str, Any]) -> str:
        """Format a single GitHub issue as readable Markdown text."""
        number = issue.get("number", 0)
        title = issue.get("title", "Untitled")
        body = issue.get("body", "") or ""
        state = issue.get("state", "unknown")
        html_url = issue.get("html_url", "")

        lines: list[str] = [
            f"## #{number}: {title}",
            "",
            f"**State:** {state}",
        ]

        if html_url:
            lines.append(f"**URL:** {html_url}")

        labels = self._extract_label_names(issue)
        if labels:
            lines.append(f"**Labels:** {', '.join(labels)}")

        assignees = self._extract_assignee_logins(issue)
        if assignees:
            lines.append(f"**Assignees:** {', '.join(assignees)}")

        milestone_obj = issue.get("milestone")
        if isinstance(milestone_obj, dict):
            ms_title = milestone_obj.get("title", "")
            ms_due = milestone_obj.get("due_on", "")
            if ms_title:
                ms_text = ms_title
                if ms_due:
                    ms_text += f" (due {ms_due})"
                lines.append(f"**Milestone:** {ms_text}")

        lines.append("")

        if body:
            lines.append(body)

        comments = self._format_comments(issue)
        if comments:
            lines.append("")
            lines.append("### Comments")
            lines.append("")
            lines.append(comments)

        return "\n".join(lines)

    def _extract_label_names(self, issue: dict[str, Any]) -> list[str]:
        """Extract label name strings from an issue."""
        labels_raw = issue.get("labels", [])
        if not isinstance(labels_raw, list):
            return []
        names: list[str] = []
        for label in labels_raw:
            if isinstance(label, dict):
                name = label.get("name", "")
                if name:
                    names.append(name)
            elif isinstance(label, str):
                names.append(label)
        return names

    def _extract_assignee_logins(self, issue: dict[str, Any]) -> list[str]:
        """Extract assignee login strings from an issue."""
        assignees_raw = issue.get("assignees", [])
        if not isinstance(assignees_raw, list):
            return []
        logins: list[str] = []
        for assignee in assignees_raw:
            if isinstance(assignee, dict):
                login = assignee.get("login", "")
                if login:
                    logins.append(login)
            elif isinstance(assignee, str):
                logins.append(assignee)
        return logins

    def _format_comments(self, issue: dict[str, Any]) -> str:
        """Format issue comments as Markdown bullet points."""
        comments_data = issue.get("comments_data", [])
        if not isinstance(comments_data, list) or not comments_data:
            return ""
        lines: list[str] = []
        for comment in comments_data:
            if not isinstance(comment, dict):
                continue
            user = comment.get("user", {})
            login = user.get("login", "unknown") if isinstance(user, dict) else "unknown"
            body = comment.get("body", "")
            created = comment.get("created_at", "")
            prefix = f"**{login}**"
            if created:
                prefix += f" ({created})"
            lines.append(f"- {prefix}: {body}")
        return "\n".join(lines)

    def _extract_cross_references(self, issue: dict[str, Any]) -> list[str]:
        """Find ``#NNN`` cross-references in the issue body and comments.

        Returns a deduplicated list of referenced issue number strings,
        excluding self-references.
        """
        own_number = str(issue.get("number", 0))
        texts: list[str] = []

        body = issue.get("body", "") or ""
        texts.append(body)

        for comment in issue.get("comments_data", []):
            if isinstance(comment, dict):
                texts.append(comment.get("body", ""))

        refs: set[str] = set()
        for text in texts:
            for match in _CROSS_REF_PATTERN.finditer(text):
                ref = match.group(1)
                if ref != own_number:
                    refs.add(ref)

        return sorted(refs)

    def _extract_milestone(self, issues: list[dict[str, Any]]) -> str:
        """Extract the first non-null milestone title from a list of issues."""
        for issue in issues:
            milestone = issue.get("milestone")
            if isinstance(milestone, dict):
                title = str(milestone.get("title", ""))
                if title:
                    return title
        return ""
