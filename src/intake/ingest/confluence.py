"""Parser for Confluence HTML exports.

Supports: HTML files exported from Confluence pages.
Extracts: Clean Markdown text, heading-based sections, page metadata.
"""

from __future__ import annotations

from pathlib import Path

import structlog

from intake.ingest.base import ParsedContent, ParseError, validate_file_readable

logger = structlog.get_logger()


class ConfluenceParser:
    """Parser for Confluence HTML exports.

    Supports:
    - HTML files exported from Confluence Cloud or Server
    - Standard HTML pages with Confluence-specific markup
    - Pages with tables, code blocks, and macros

    Extracts:
    - Clean Markdown text (converted from HTML via markdownify)
    - Heading-based sections
    - Page title and metadata
    """

    def can_parse(self, source: str) -> bool:
        """Check if this source is a Confluence HTML export."""
        path = Path(source)
        if not path.exists() or not path.is_file() or path.suffix.lower() not in {".html", ".htm"}:
            return False
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")[:2000]
            lower = content.lower()
            return "confluence" in lower or "atlassian" in lower
        except OSError:
            return False

    def parse(self, source: str) -> ParsedContent:
        """Parse a Confluence HTML export into normalized content.

        Args:
            source: Path to the Confluence HTML file.

        Returns:
            ParsedContent with Markdown text, sections, and metadata.

        Raises:
            ParseError: If the HTML cannot be read or processed.
        """
        validate_file_readable(source)
        path = Path(source)

        try:
            from bs4 import BeautifulSoup
            from markdownify import markdownify
        except ImportError as e:
            raise ParseError(
                source=source,
                reason="beautifulsoup4 and/or markdownify not installed",
                suggestion="Install with: pip install beautifulsoup4 markdownify",
            ) from e

        try:
            raw_html = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            raise ParseError(
                source=source,
                reason=f"Could not read file: {e}",
                suggestion="Check file permissions and path.",
            ) from e

        if not raw_html.strip():
            raise ParseError(
                source=source,
                reason="HTML file is empty",
                suggestion="Provide a Confluence HTML export with content.",
            )

        soup = BeautifulSoup(raw_html, "html.parser")

        title = self._extract_title(soup)
        content_element = self._find_main_content(soup)

        clean_html = str(content_element) if content_element else raw_html
        markdown_text = markdownify(clean_html, heading_style="ATX", strip=["script", "style"])
        markdown_text = self._clean_markdown(markdown_text)

        sections = self._extract_sections(markdown_text)
        metadata = self._extract_metadata(soup, title)

        logger.info(
            "confluence_parsed",
            source=source,
            title=title,
            sections=len(sections),
        )

        return ParsedContent(
            text=markdown_text.strip(),
            format="confluence",
            source=source,
            metadata=metadata,
            sections=sections,
        )

    def _extract_title(self, soup: object) -> str:
        """Extract the page title from the HTML."""
        from bs4 import BeautifulSoup, Tag

        if not isinstance(soup, BeautifulSoup):
            return ""

        title_tag = soup.find("title")
        if isinstance(title_tag, Tag) and title_tag.string:
            return title_tag.string.strip()

        h1 = soup.find("h1")
        if isinstance(h1, Tag):
            return h1.get_text(strip=True)

        return ""

    def _find_main_content(self, soup: object) -> object | None:
        """Find the main content area in a Confluence HTML export."""
        from bs4 import BeautifulSoup, Tag

        if not isinstance(soup, BeautifulSoup):
            return None

        selectors: list[dict[str, str]] = [
            {"id": "main-content"},
            {"class": "wiki-content"},
            {"class": "confluence-information-macro"},
            {"id": "content"},
            {"role": "main"},
        ]
        for selector in selectors:
            element = soup.find("div", attrs=selector)
            if isinstance(element, Tag):
                return element

        body = soup.find("body")
        if isinstance(body, Tag):
            return body

        return None

    def _clean_markdown(self, text: str) -> str:
        """Clean up markdown output from markdownify."""
        import re

        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\[([^\]]*)\]\(\s*\)", r"\1", text)
        return text.strip()

    def _extract_sections(self, markdown_text: str) -> list[dict[str, str]]:
        """Extract sections based on Markdown headings."""
        import re

        heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
        matches = list(heading_pattern.finditer(markdown_text))

        if not matches:
            return []

        sections: list[dict[str, str]] = []
        for i, match in enumerate(matches):
            heading_level = len(match.group(1))
            heading_text = match.group(2).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown_text)
            content = markdown_text[start:end].strip()

            sections.append(
                {
                    "title": heading_text,
                    "level": str(heading_level),
                    "content": content,
                }
            )

        return sections

    def _extract_metadata(self, soup: object, title: str) -> dict[str, str]:
        """Extract page metadata from HTML elements."""
        from bs4 import BeautifulSoup, Tag

        metadata: dict[str, str] = {
            "source_type": "confluence",
        }

        if title:
            metadata["title"] = title

        if not isinstance(soup, BeautifulSoup):
            return metadata

        for meta in soup.find_all("meta"):
            if not isinstance(meta, Tag):
                continue
            name = meta.get("name", "")
            content = meta.get("content", "")
            if name and content:
                name_str = str(name)
                content_str = str(content)
                if name_str in {"author", "creator", "date", "description"}:
                    metadata[name_str] = content_str

        return metadata
