"""Central parser registry with format auto-detection.

Automatically detects the format of a source by:
1. File extension mapping
2. Content inspection (magic bytes, structural patterns)
3. Fallback to plain text
"""

from __future__ import annotations

import json
from pathlib import Path

import structlog

from intake.ingest.base import ParsedContent, ParseError, Parser, UnsupportedFormatError
from intake.utils.file_detect import EXTENSION_MAP

logger = structlog.get_logger()

PLAINTEXT_FALLBACK = "plaintext"


class ParserRegistry:
    """Central parser registry with format auto-detection.

    Maintains a mapping of format names to parser instances and
    provides auto-detection of source formats for transparent dispatch.
    """

    def __init__(self) -> None:
        self._parsers: dict[str, Parser] = {}

    def register(self, name: str, parser: Parser) -> None:
        """Register a parser for a given format name.

        Args:
            name: Format identifier (e.g. "markdown", "jira", "pdf").
            parser: Parser instance that handles this format.
        """
        self._parsers[name] = parser
        logger.debug("parser_registered", name=name)

    @property
    def registered_formats(self) -> list[str]:
        """List of all registered format names."""
        return sorted(self._parsers.keys())

    def detect_format(self, source: str) -> str:
        """Detect the format of a source.

        Detection order:
        1. Stdin marker ('-') -> plaintext
        2. File extension mapping
        3. JSON subtype detection (jira vs generic yaml)
        4. HTML subtype detection (confluence vs generic html)
        5. Fallback to plaintext

        Args:
            source: Path to the file or '-' for stdin.

        Returns:
            Format identifier string.
        """
        if source == "-":
            return PLAINTEXT_FALLBACK

        path = Path(source)

        if not path.exists():
            logger.warning("source_not_found", source=source)
            return PLAINTEXT_FALLBACK

        ext = path.suffix.lower()
        fmt = EXTENSION_MAP.get(ext)

        if fmt is None:
            return PLAINTEXT_FALLBACK

        if fmt == "json":
            return self._detect_json_subtype(path)

        if fmt == "html":
            return self._detect_html_subtype(path)

        return fmt

    def parse(self, source: str) -> ParsedContent:
        """Auto-detect format and parse the source.

        Args:
            source: Path to the file or '-' for stdin.

        Returns:
            ParsedContent from the appropriate parser.

        Raises:
            ParseError: If the source does not exist.
            UnsupportedFormatError: If no parser is registered for the detected format.
        """
        if source != "-":
            path = Path(source)
            if not path.exists():
                raise ParseError(
                    source=source,
                    reason="File not found",
                    suggestion="Check the file path and try again.",
                )

        fmt = self.detect_format(source)
        parser = self._parsers.get(fmt)

        if parser is None:
            fallback = self._parsers.get(PLAINTEXT_FALLBACK)
            if fallback is not None:
                logger.warning(
                    "no_parser_for_format",
                    format=fmt,
                    source=source,
                    fallback=PLAINTEXT_FALLBACK,
                )
                return fallback.parse(source)
            raise UnsupportedFormatError(source=source, detected_format=fmt)

        logger.info("parsing_source", source=source, format=fmt)
        return parser.parse(source)

    def _detect_json_subtype(self, path: Path) -> str:
        """Detect if a JSON file is a Jira export or structured YAML/JSON.

        Checks for Jira-specific patterns:
        - ``{"issues": [...]}`` format (Jira REST API export)
        - ``[{"key": "PROJ-123", "fields": {...}}, ...]`` format (list of issues)

        Args:
            path: Path to the JSON file.

        Returns:
            "jira" if Jira patterns are detected, "yaml" otherwise.
        """
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict) and "issues" in data:
                logger.debug("json_subtype_detected", path=str(path), subtype="jira")
                return "jira"

            if isinstance(data, list) and len(data) > 0:
                first = data[0]
                if isinstance(first, dict) and "key" in first and "fields" in first:
                    logger.debug("json_subtype_detected", path=str(path), subtype="jira")
                    return "jira"

            return "yaml"
        except (json.JSONDecodeError, OSError):
            return "yaml"

    def _detect_html_subtype(self, path: Path) -> str:
        """Detect if an HTML file is a Confluence export.

        Inspects the first 2000 characters for Confluence/Atlassian markers.

        Args:
            path: Path to the HTML file.

        Returns:
            "confluence" if Confluence markers are found, "html" otherwise.
        """
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")[:2000]
            content_lower = content.lower()
            if "confluence" in content_lower or "atlassian" in content_lower:
                logger.debug("html_subtype_detected", path=str(path), subtype="confluence")
                return "confluence"
            return "html"
        except OSError:
            return "html"


def create_default_registry() -> ParserRegistry:
    """Create a ParserRegistry with all built-in parsers registered.

    Returns:
        A fully configured ParserRegistry ready to use.
    """
    from intake.ingest.confluence import ConfluenceParser
    from intake.ingest.docx import DocxParser
    from intake.ingest.image import ImageParser
    from intake.ingest.jira import JiraParser
    from intake.ingest.markdown import MarkdownParser
    from intake.ingest.pdf import PdfParser
    from intake.ingest.plaintext import PlaintextParser
    from intake.ingest.yaml_input import YamlInputParser

    registry = ParserRegistry()
    registry.register("markdown", MarkdownParser())
    registry.register("plaintext", PlaintextParser())
    registry.register("yaml", YamlInputParser())
    registry.register("pdf", PdfParser())
    registry.register("docx", DocxParser())
    registry.register("jira", JiraParser())
    registry.register("confluence", ConfluenceParser())
    registry.register("image", ImageParser())

    logger.info("default_registry_created", formats=registry.registered_formats)
    return registry
