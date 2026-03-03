"""Parser for HTTP/HTTPS URLs.

Supports: Any publicly accessible web page.
Extracts: Clean Markdown text from HTML, heading-based sections,
          page title, and detected source type (confluence, jira, github, generic).
"""

from __future__ import annotations

import re

import httpx
import structlog

from intake.ingest.base import ParsedContent, ParseError

logger = structlog.get_logger()

REQUEST_TIMEOUT_SECONDS = 30.0

# Patterns to detect the origin of a URL.
_SOURCE_TYPE_PATTERNS: list[tuple[str, str]] = [
    (r"atlassian\.net|confluence", "confluence"),
    (r"jira\.|atlassian\.net/browse", "jira"),
    (r"github\.com", "github"),
    (r"gitlab\.com", "gitlab"),
    (r"notion\.so", "notion"),
]


class UrlParser:
    """Parser for HTTP/HTTPS URLs.

    Fetches web pages using *httpx* (synchronous), converts HTML to
    Markdown via *markdownify*, and returns a normalised
    ``ParsedContent``.

    Supports:
    - Generic HTML pages
    - Confluence / Jira / GitHub web UI pages (detected by URL pattern)
    - Plain-text responses (returned as-is)

    Extracts:
    - Page title (``<title>`` or first ``<h1>``)
    - Heading-based sections
    - Detected source type metadata
    """

    # ------------------------------------------------------------------
    # Protocol methods
    # ------------------------------------------------------------------

    def can_parse(self, source: str) -> bool:
        """Return True if *source* looks like an HTTP or HTTPS URL."""
        lower = source.lower().strip()
        return lower.startswith("http://") or lower.startswith("https://")

    def parse(self, source: str) -> ParsedContent:
        """Fetch *source* URL and convert to normalised content.

        Args:
            source: A fully-qualified HTTP/HTTPS URL.

        Returns:
            ParsedContent with format ``"url"``, Markdown text,
            heading-based sections, and metadata.

        Raises:
            ParseError: If the request fails or produces no usable content.
        """
        response = self._fetch(source)
        content_type = response.headers.get("content-type", "")

        if "html" in content_type:
            text, title, sections = self._parse_html(response.text, source)
        else:
            text = response.text.strip()
            title = ""
            sections = []

        if not text:
            raise ParseError(
                source=source,
                reason="Fetched page contains no extractable text",
                suggestion="Verify the URL returns readable HTML or plain text.",
            )

        source_type = self._detect_source_type(source)
        metadata: dict[str, str] = {
            "source_type": source_type,
            "url": source,
        }
        if title:
            metadata["title"] = title

        logger.info(
            "url_parsed",
            source=source,
            source_type=source_type,
            sections=len(sections),
            word_count=len(text.split()),
        )

        return ParsedContent(
            text=text,
            format="url",
            source=source,
            metadata=metadata,
            sections=sections,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch(self, source: str) -> httpx.Response:
        """Perform an HTTP GET and return the response.

        Raises:
            ParseError: On any network or HTTP error.
        """
        try:
            response = httpx.get(
                source,
                follow_redirects=True,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise ParseError(
                source=source,
                reason=f"Could not connect to URL: {exc}",
                suggestion="Check that the URL is correct and the server is reachable.",
            ) from exc
        except httpx.TimeoutException as exc:
            raise ParseError(
                source=source,
                reason=f"Request timed out after {REQUEST_TIMEOUT_SECONDS}s",
                suggestion="Try again later or increase the timeout.",
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise ParseError(
                source=source,
                reason=f"HTTP {exc.response.status_code}: {exc.response.reason_phrase}",
                suggestion="Verify the URL is accessible and does not require authentication.",
            ) from exc
        except httpx.HTTPError as exc:
            raise ParseError(
                source=source,
                reason=f"HTTP request failed: {exc}",
                suggestion="Check the URL and your network connection.",
            ) from exc

        return response

    def _parse_html(self, html: str, source: str) -> tuple[str, str, list[dict[str, str]]]:
        """Convert raw HTML to Markdown and extract structure.

        Returns:
            Tuple of (markdown_text, page_title, sections).
        """
        from bs4 import BeautifulSoup, Tag
        from markdownify import markdownify

        soup = BeautifulSoup(html, "html.parser")

        # Extract title
        title = ""
        title_tag = soup.find("title")
        if isinstance(title_tag, Tag) and title_tag.string:
            title = title_tag.string.strip()
        if not title:
            h1 = soup.find("h1")
            if isinstance(h1, Tag):
                title = h1.get_text(strip=True)

        # Remove script/style tags before conversion
        for tag in soup.find_all(["script", "style", "nav", "footer"]):
            if isinstance(tag, Tag):
                tag.decompose()

        # Find main content area
        main = soup.find("main") or soup.find("article") or soup.find("body")
        content_html = str(main) if main else html

        markdown_text = markdownify(content_html, heading_style="ATX", strip=["script", "style"])
        markdown_text = self._clean_markdown(markdown_text)

        sections = self._extract_sections(markdown_text)

        return markdown_text, title, sections

    def _clean_markdown(self, text: str) -> str:
        """Normalise Markdown whitespace and remove empty links."""
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\[([^\]]*)\]\(\s*\)", r"\1", text)
        return text.strip()

    def _extract_sections(self, markdown_text: str) -> list[dict[str, str]]:
        """Split Markdown into heading-based sections."""
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

    def _detect_source_type(self, url: str) -> str:
        """Detect the origin service from the URL pattern."""
        lower = url.lower()
        for pattern, source_type in _SOURCE_TYPE_PATTERNS:
            if re.search(pattern, lower):
                logger.debug("url_source_type_detected", url=url, source_type=source_type)
                return source_type
        return "generic"
