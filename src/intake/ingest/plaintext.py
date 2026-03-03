"""Parser for plain text files and stdin.

Supports: .txt files, free text, Slack thread dumps, stdin ('-').
Extracts: Full text content, basic paragraph-level sections.
"""

from __future__ import annotations

import sys
from pathlib import Path

import structlog

from intake.ingest.base import (
    EmptySourceError,
    ParsedContent,
    read_text_safe,
    validate_file_readable,
)

logger = structlog.get_logger()


class PlaintextParser:
    """Parser for plain text content.

    Supports:
    - .txt files
    - Free-form text content
    - Stdin input (source='-')
    - Slack-style thread dumps

    Extracts:
    - Full text content
    - Paragraph-level sections (split by double newlines)
    """

    def can_parse(self, source: str) -> bool:
        """Check if this source is a parseable plaintext file or stdin."""
        if source == "-":
            return True
        path = Path(source)
        return path.exists() and path.is_file() and path.suffix.lower() in {".txt", ""}

    def parse(self, source: str) -> ParsedContent:
        """Parse a plaintext file or stdin.

        Args:
            source: Path to the text file, or '-' for stdin.

        Returns:
            ParsedContent with text and paragraph sections.

        Raises:
            ParseError: If the file cannot be read or is empty.
        """
        text = self._read_source(source)
        if not text.strip():
            raise EmptySourceError(source)
        sections = self._extract_paragraphs(text)

        logger.info(
            "plaintext_parsed",
            source=source,
            paragraphs=len(sections),
            words=len(text.split()),
        )

        return ParsedContent(
            text=text.strip(),
            format="plaintext",
            source=source,
            metadata={"source_type": "stdin" if source == "-" else "file"},
            sections=sections,
        )

    def _read_source(self, source: str) -> str:
        """Read text from a file path or stdin."""
        if source == "-":
            return sys.stdin.read()

        validate_file_readable(source)
        return read_text_safe(source, Path(source))

    def _extract_paragraphs(self, text: str) -> list[dict[str, str]]:
        """Split text into paragraph-level sections."""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        sections: list[dict[str, str]] = []
        for i, paragraph in enumerate(paragraphs, 1):
            first_line = paragraph.split("\n", maxsplit=1)[0][:80]
            sections.append(
                {
                    "title": f"Paragraph {i}: {first_line}",
                    "content": paragraph,
                }
            )
        return sections
