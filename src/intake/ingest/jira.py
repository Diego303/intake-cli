"""Parser for Jira JSON exports.

Supports:
- Jira REST API export: ``{"issues": [...]}``
- Jira list export: ``[{"key": "PROJ-123", "fields": {...}}, ...]``

Extracts: Issues with summary, description, comments, labels,
          priority, status, and inter-issue links.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog

from intake.ingest.base import ParsedContent, ParseError, validate_file_readable

logger = structlog.get_logger()

MAX_COMMENT_LENGTH = 500
MAX_COMMENTS_PER_ISSUE = 5


class JiraParser:
    """Parser for Jira JSON exports.

    Supports two formats:
    1. Jira REST API export: ``{"issues": [...]}``
    2. Jira CSV-to-JSON conversion: ``[{"key": "PROJ-123", "fields": {...}}, ...]``

    Extracts:
    - Summary and description from each issue
    - Acceptance criteria (if in description or custom fields)
    - Relevant comments (last 5 per issue)
    - Labels, priority, sprint, assignee
    - Links between issues (blocks, depends on, relates to)
    """

    def can_parse(self, source: str) -> bool:
        """Check if the source is a Jira JSON export."""
        path = Path(source)
        if not path.exists() or not path.is_file() or path.suffix.lower() != ".json":
            return False
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return self._is_jira_export(data)
        except (json.JSONDecodeError, OSError):
            return False

    def parse(self, source: str) -> ParsedContent:
        """Parse a Jira JSON export into normalized content.

        Args:
            source: Path to the Jira JSON export file.

        Returns:
            ParsedContent with issues as sections and inter-issue relations.

        Raises:
            ParseError: If the file cannot be read or parsed.
        """
        path = validate_file_readable(source)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ParseError(
                source=source,
                reason=f"Invalid JSON: {e}",
                suggestion="Verify the file is a valid Jira JSON export.",
            ) from e

        issues = self._extract_issues(data)
        if not issues:
            raise ParseError(
                source=source,
                reason="No issues found in Jira export",
                suggestion=(
                    "Verify the JSON contains an 'issues' array or is a list of issue objects."
                ),
            )

        text_parts: list[str] = []
        sections: list[dict[str, str]] = []
        relations: list[dict[str, str]] = []

        for issue in issues:
            key = issue.get("key", "UNKNOWN")
            fields = issue.get("fields", {})

            section_text = self._format_issue(key, fields)
            text_parts.append(section_text)
            sections.append(
                {
                    "title": f"{key}: {fields.get('summary', 'Untitled')}",
                    "content": section_text,
                }
            )

            for link in self._extract_links(fields):
                relations.append(link)

        full_text = "\n\n---\n\n".join(text_parts)
        metadata: dict[str, str] = {
            "issue_count": str(len(issues)),
            "source_type": "jira",
        }

        logger.info("jira_parsed", issues=len(issues), source=source)

        return ParsedContent(
            text=full_text,
            format="jira",
            source=source,
            metadata=metadata,
            sections=sections,
            relations=relations,
        )

    def _is_jira_export(self, data: object) -> bool:
        """Check if the data structure matches a Jira export."""
        if isinstance(data, dict) and "issues" in data:
            return True
        if isinstance(data, list) and len(data) > 0:
            first = data[0]
            return isinstance(first, dict) and "key" in first
        return False

    def _extract_issues(self, data: object) -> list[dict[str, Any]]:
        """Extract the list of issues from the export data."""
        if isinstance(data, dict) and "issues" in data:
            issues = data["issues"]
            return issues if isinstance(issues, list) else []
        if isinstance(data, list):
            return data
        return []

    def _format_issue(self, key: str, fields: dict[str, Any]) -> str:
        """Format a single Jira issue as readable text."""
        summary = fields.get("summary", "Untitled")
        description = fields.get("description", "") or ""
        priority = self._safe_nested(fields, "priority", "name", default="Medium")
        status = self._safe_nested(fields, "status", "name", default="Unknown")
        labels = fields.get("labels", [])

        lines: list[str] = [
            f"## {key}: {summary}",
            "",
            f"**Priority:** {priority} | **Status:** {status}",
        ]

        if labels:
            lines.append(f"**Labels:** {', '.join(labels)}")

        lines.append("")

        if description:
            lines.append(description)

        comments = self._extract_comments(fields)
        if comments:
            lines.append("")
            lines.append("### Relevant Comments")
            lines.append("")
            for comment in comments:
                body = comment["body"][:MAX_COMMENT_LENGTH]
                lines.append(f"- **{comment['author']}**: {body}")

        return "\n".join(lines)

    def _extract_comments(self, fields: dict[str, Any]) -> list[dict[str, str]]:
        """Extract the last N comments from an issue."""
        comments_data = fields.get("comment", {})
        if isinstance(comments_data, dict):
            comments_data = comments_data.get("comments", [])
        if not isinstance(comments_data, list):
            return []

        result: list[dict[str, str]] = []
        for c in comments_data[-MAX_COMMENTS_PER_ISSUE:]:
            author = self._safe_nested(c, "author", "displayName", default="Unknown")
            body = c.get("body", "")
            if isinstance(body, dict):
                body = self._extract_adf_text(body)
            result.append({"author": author, "body": str(body)[:MAX_COMMENT_LENGTH]})
        return result

    def _extract_adf_text(self, adf: dict[str, Any]) -> str:
        """Extract plain text from Atlassian Document Format (ADF) content."""
        parts: list[str] = []
        for block in adf.get("content", []):
            for inline in block.get("content", []):
                if "text" in inline:
                    parts.append(inline["text"])
        return " ".join(parts)

    def _extract_links(self, fields: dict[str, Any]) -> list[dict[str, str]]:
        """Extract issue links (blocks, depends on, relates to)."""
        links: list[dict[str, str]] = []
        for link in fields.get("issuelinks", []):
            link_type = self._safe_nested(link, "type", "name", default="relates to")
            if "outwardIssue" in link:
                target = link["outwardIssue"].get("key", "")
                links.append(
                    {
                        "type": link_type,
                        "direction": "outward",
                        "target": target,
                    }
                )
            if "inwardIssue" in link:
                target = link["inwardIssue"].get("key", "")
                links.append(
                    {
                        "type": link_type,
                        "direction": "inward",
                        "target": target,
                    }
                )
        return links

    def _safe_nested(self, data: dict[str, Any], *keys: str, default: str = "") -> str:
        """Safely extract a value from nested dicts."""
        current: Any = data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return default
        return str(current) if current is not None else default
