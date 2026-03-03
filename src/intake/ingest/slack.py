"""Parser for Slack JSON workspace exports.

Supports: Channel export files produced by Slack's data export feature.
          Each file is a JSON array of message objects.
Extracts: Messages grouped by thread, detected decisions, detected action items.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
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

# Reaction names that signal a decision was made.
DECISION_REACTIONS: frozenset[str] = frozenset(
    {
        "thumbsup",
        "+1",
        "white_check_mark",
        "heavy_check_mark",
        "ballot_box_with_check",
        "approved",
    }
)

# Case-insensitive patterns that indicate a decision in message text.
DECISION_KEYWORDS: re.Pattern[str] = re.compile(
    r"\b(decided|let'?s go with|approved|decision|agreed|confirmed)\b",
    re.IGNORECASE,
)

# Case-insensitive patterns that indicate an action item.
ACTION_ITEM_KEYWORDS: re.Pattern[str] = re.compile(
    r"\b(TODO|action item|will do|need to|action:|follow[- ]?up)\b",
    re.IGNORECASE,
)


class SlackParser:
    """Parser for Slack JSON workspace exports.

    Supports:
    - Channel export files (array of message objects)
    - Messages with ``type``, ``user``, ``text``, ``ts``
    - Threaded replies via ``thread_ts``
    - Reactions (used for decision detection)

    Extracts:
    - All messages formatted as ``[timestamp] user: text``
    - Sections grouped by thread (top-level messages that start threads)
    - Decisions (messages with approval reactions or decision keywords)
    - Action items (messages containing TODO / action item keywords)
    """

    # ------------------------------------------------------------------
    # Protocol methods
    # ------------------------------------------------------------------

    def can_parse(self, source: str) -> bool:
        """Return True if *source* is a JSON file with Slack export structure."""
        path = Path(source)
        if not path.exists() or not path.is_file() or path.suffix.lower() != ".json":
            return False
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return self._is_slack_export(data)
        except (json.JSONDecodeError, OSError):
            return False

    def parse(self, source: str) -> ParsedContent:
        """Parse a Slack JSON export into normalised content.

        Args:
            source: Path to a Slack channel export JSON file.

        Returns:
            ParsedContent with format ``"slack"``, thread-grouped sections,
            and metadata including decision and action-item counts.

        Raises:
            ParseError: If the file cannot be read, is not valid JSON,
                        or contains no messages.
        """
        path = validate_file_readable(source)
        raw = read_text_safe(source, path)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ParseError(
                source=source,
                reason=f"Invalid JSON: {exc}",
                suggestion="Verify the file is a valid Slack JSON export.",
            ) from exc

        if not isinstance(data, list) or len(data) == 0:
            raise ParseError(
                source=source,
                reason="Expected a non-empty JSON array of messages",
                suggestion="Provide a Slack channel export (array of message objects).",
            )

        messages = [m for m in data if isinstance(m, dict) and m.get("type") == "message"]
        if not messages:
            raise ParseError(
                source=source,
                reason="No messages found in Slack export",
                suggestion="Verify the JSON contains message objects with type='message'.",
            )

        threads = self._group_by_thread(messages)
        decisions = self._detect_decisions(messages)
        action_items = self._detect_action_items(messages)

        text_parts: list[str] = []
        sections: list[dict[str, str]] = []

        for thread_ts, thread_messages in threads.items():
            section_text = self._format_thread(thread_messages)
            text_parts.append(section_text)
            first_msg = thread_messages[0]
            preview = first_msg.get("text", "")[:80]
            sections.append(
                {
                    "title": f"Thread {thread_ts}: {preview}",
                    "content": section_text,
                }
            )

        full_text = "\n\n---\n\n".join(text_parts)

        if decisions:
            full_text += "\n\n---\n\n## Decisions\n\n"
            for msg in decisions:
                full_text += f"- {self._format_message(msg)}\n"

        if action_items:
            full_text += "\n\n---\n\n## Action Items\n\n"
            for msg in action_items:
                full_text += f"- {self._format_message(msg)}\n"

        metadata: dict[str, str] = {
            "source_type": "slack",
            "message_count": str(len(messages)),
            "thread_count": str(len(threads)),
            "decision_count": str(len(decisions)),
            "action_item_count": str(len(action_items)),
        }

        logger.info(
            "slack_parsed",
            source=source,
            messages=len(messages),
            threads=len(threads),
            decisions=len(decisions),
            action_items=len(action_items),
        )

        return ParsedContent(
            text=full_text,
            format="slack",
            source=source,
            metadata=metadata,
            sections=sections,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_slack_export(self, data: object) -> bool:
        """Return True if *data* looks like a Slack channel export."""
        if not isinstance(data, list) or len(data) == 0:
            return False
        first = data[0]
        return isinstance(first, dict) and first.get("type") == "message" and "ts" in first

    def _group_by_thread(self, messages: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """Group messages by ``thread_ts``.

        Messages without ``thread_ts`` are treated as their own thread,
        keyed by their ``ts``.
        """
        threads: dict[str, list[dict[str, Any]]] = {}
        for msg in messages:
            thread_key = msg.get("thread_ts", msg.get("ts", "0"))
            threads.setdefault(thread_key, []).append(msg)
        return threads

    def _detect_decisions(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Identify messages that represent decisions.

        A message is considered a decision if it has a decision-related
        reaction OR its text matches a decision keyword pattern.
        """
        results: list[dict[str, Any]] = []
        for msg in messages:
            if self._has_decision_reaction(msg) or DECISION_KEYWORDS.search(msg.get("text", "")):
                results.append(msg)
        return results

    def _has_decision_reaction(self, msg: dict[str, Any]) -> bool:
        """Check if a message has at least one decision-related reaction."""
        reactions = msg.get("reactions", [])
        if not isinstance(reactions, list):
            return False
        for reaction in reactions:
            name = reaction.get("name", "")
            if name in DECISION_REACTIONS:
                return True
        return False

    def _detect_action_items(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Identify messages that represent action items."""
        results: list[dict[str, Any]] = []
        for msg in messages:
            text = msg.get("text", "")
            if ACTION_ITEM_KEYWORDS.search(text):
                results.append(msg)
        return results

    def _format_thread(self, messages: list[dict[str, Any]]) -> str:
        """Format a list of thread messages as readable text."""
        lines: list[str] = []
        for msg in messages:
            lines.append(self._format_message(msg))
        return "\n".join(lines)

    def _format_message(self, msg: dict[str, Any]) -> str:
        """Format a single Slack message as ``[timestamp] user: text``."""
        ts = msg.get("ts", "0")
        timestamp = self._ts_to_readable(ts)
        user = msg.get("user", "unknown")
        text = msg.get("text", "")
        return f"[{timestamp}] {user}: {text}"

    def _ts_to_readable(self, ts: str) -> str:
        """Convert a Slack timestamp string to a human-readable format."""
        try:
            epoch = float(ts)
            dt = datetime.fromtimestamp(epoch, tz=UTC)
            return dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, OSError):
            return ts
