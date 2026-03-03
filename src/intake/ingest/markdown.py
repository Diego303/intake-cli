"""Parser for Markdown files.

Supports: .md files with standard Markdown formatting.
Extracts: Full text, sections by headings, metadata from YAML front matter.
"""

from __future__ import annotations

import re
from pathlib import Path

import structlog

from intake.ingest.base import ParsedContent, read_text_safe, validate_file_readable

logger = structlog.get_logger()

_FRONT_MATTER_PATTERN = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n",
    re.DOTALL,
)

_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


class MarkdownParser:
    """Parser for Markdown (.md) files.

    Supports:
    - Standard Markdown with headings, lists, code blocks
    - YAML front matter (``---`` delimited at top of file)
    - Section extraction by heading level

    Extracts:
    - Full cleaned text
    - Sections split by headings
    - Metadata from front matter (if present)
    """

    def can_parse(self, source: str) -> bool:
        """Check if this source is a parseable Markdown file."""
        path = Path(source)
        return path.exists() and path.is_file() and path.suffix.lower() in {".md", ".markdown"}

    def parse(self, source: str) -> ParsedContent:
        """Parse a Markdown file into normalized content.

        Args:
            source: Path to the Markdown file.

        Returns:
            ParsedContent with text, sections, and optional front matter metadata.

        Raises:
            ParseError: If the file cannot be read or is empty.
        """
        validate_file_readable(source)
        raw = read_text_safe(source, Path(source))

        metadata = self._extract_front_matter(raw)
        text = self._strip_front_matter(raw)
        sections = self._extract_sections(text)

        logger.info("markdown_parsed", source=source, sections=len(sections))

        return ParsedContent(
            text=text.strip(),
            format="markdown",
            source=source,
            metadata=metadata,
            sections=sections,
        )

    def _extract_front_matter(self, raw: str) -> dict[str, str]:
        """Extract YAML front matter from the top of the file."""
        match = _FRONT_MATTER_PATTERN.match(raw)
        if not match:
            return {}

        try:
            import yaml

            data = yaml.safe_load(match.group(1))
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except Exception:
            pass
        return {}

    def _strip_front_matter(self, raw: str) -> str:
        """Remove YAML front matter from the text."""
        return _FRONT_MATTER_PATTERN.sub("", raw, count=1)

    def _extract_sections(self, text: str) -> list[dict[str, str]]:
        """Split text into sections by Markdown headings."""
        sections: list[dict[str, str]] = []
        matches = list(_HEADING_PATTERN.finditer(text))

        if not matches:
            return sections

        for i, match in enumerate(matches):
            heading_level = len(match.group(1))
            heading_text = match.group(2).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()

            sections.append(
                {
                    "title": heading_text,
                    "level": str(heading_level),
                    "content": content,
                }
            )

        return sections
