"""Central parser registry with format auto-detection.

Automatically detects the format of a source by:
1. File extension mapping
2. Content inspection (magic bytes, structural patterns)
3. Fallback to plain text

Supports both V1 parsers (via manual registration) and V2 parsers
(via plugin discovery from entry points).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from intake.ingest.base import ParsedContent, ParseError, Parser, UnsupportedFormatError
from intake.utils.file_detect import EXTENSION_MAP

if TYPE_CHECKING:
    from intake.plugins.discovery import PluginRegistry

logger = structlog.get_logger()

PLAINTEXT_FALLBACK = "plaintext"


class ParserRegistry:
    """Central parser registry with format auto-detection.

    Maintains a mapping of format names to parser instances and
    provides auto-detection of source formats for transparent dispatch.

    Can be optionally backed by a ``PluginRegistry`` for automatic
    parser discovery via Python entry points.
    """

    def __init__(self, plugin_registry: PluginRegistry | None = None) -> None:
        self._parsers: dict[str, Parser] = {}
        self._plugin_registry = plugin_registry

    def register(self, name: str, parser: Parser) -> None:
        """Register a parser for a given format name.

        Args:
            name: Format identifier (e.g. "markdown", "jira", "pdf").
            parser: Parser instance that handles this format.
        """
        self._parsers[name] = parser
        logger.debug("parser_registered", name=name)

    def discover_parsers(self) -> int:
        """Discover and register parsers from the plugin registry.

        Loads parser plugins from entry points and registers them.
        Only registers parsers that are not already manually registered.

        Returns:
            Number of parsers discovered and registered.
        """
        if self._plugin_registry is None:
            return 0

        parsers = self._plugin_registry.get_parsers()
        count = 0
        for name, parser_instance in parsers.items():
            if name not in self._parsers and parser_instance is not None:
                self._parsers[name] = parser_instance  # type: ignore[assignment]
                count += 1
                logger.debug("parser_discovered", name=name)

        logger.info("parsers_discovered", count=count)
        return count

    @property
    def registered_formats(self) -> list[str]:
        """List of all registered format names."""
        return sorted(self._parsers.keys())

    def detect_format(self, source: str) -> str:
        """Detect the format of a source.

        Detection order:
        1. Stdin marker ('-') -> plaintext
        2. File extension mapping
        3. JSON subtype detection (jira, github_issues, slack, or yaml)
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
        """Detect the specific format of a JSON file.

        Detection order (most specific first):
        1. Jira export (``{"issues": [...]}`` or list with ``key`` + ``fields``)
        2. GitLab Issues (objects with ``iid`` + ``title``)
        3. GitHub Issues (objects with ``number`` + ``html_url``, or ``title`` + ``labels`` list)
        4. Slack export (array of objects with ``type: "message"`` + ``ts``)
        5. Generic structured YAML/JSON

        Args:
            path: Path to the JSON file.

        Returns:
            Detected format identifier.
        """
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            # --- Jira detection ---
            if isinstance(data, dict) and "issues" in data:
                # Could be Jira or GitLab wrapped format
                issues_list = data["issues"]
                if isinstance(issues_list, list) and len(issues_list) > 0:
                    first_issue = issues_list[0]
                    if isinstance(first_issue, dict) and "iid" in first_issue:
                        logger.debug(
                            "json_subtype_detected",
                            path=str(path),
                            subtype="gitlab_issues",
                        )
                        return "gitlab_issues"
                logger.debug("json_subtype_detected", path=str(path), subtype="jira")
                return "jira"

            if isinstance(data, list) and len(data) > 0:
                first = data[0]
                if isinstance(first, dict):
                    # Jira list format: has "key" and "fields"
                    if "key" in first and "fields" in first:
                        logger.debug("json_subtype_detected", path=str(path), subtype="jira")
                        return "jira"

                    # GitLab Issues: has "iid" (not "number")
                    if "iid" in first and "title" in first:
                        logger.debug(
                            "json_subtype_detected",
                            path=str(path),
                            subtype="gitlab_issues",
                        )
                        return "gitlab_issues"

                    # GitHub Issues: has "number" + ("html_url" or "title" + "labels")
                    if "number" in first and (
                        "html_url" in first or ("title" in first and "labels" in first)
                    ):
                        logger.debug(
                            "json_subtype_detected",
                            path=str(path),
                            subtype="github_issues",
                        )
                        return "github_issues"

                    # Slack export: has "type": "message" and "ts"
                    if first.get("type") == "message" and "ts" in first:
                        logger.debug("json_subtype_detected", path=str(path), subtype="slack")
                        return "slack"

            # Single GitLab issue (not in a list)
            if isinstance(data, dict) and "iid" in data and "title" in data:
                logger.debug("json_subtype_detected", path=str(path), subtype="gitlab_issues")
                return "gitlab_issues"

            # Single GitHub issue (not in a list)
            if (
                isinstance(data, dict)
                and "number" in data
                and ("html_url" in data or ("title" in data and "labels" in data))
            ):
                logger.debug("json_subtype_detected", path=str(path), subtype="github_issues")
                return "github_issues"

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


def create_default_registry(use_plugins: bool = True) -> ParserRegistry:
    """Create a ParserRegistry with all built-in parsers registered.

    When ``use_plugins`` is True, attempts to discover parsers from
    Python entry points first. Falls back to manual registration if
    plugin discovery fails or finds no parsers.

    Args:
        use_plugins: Whether to attempt plugin-based discovery.

    Returns:
        A fully configured ParserRegistry ready to use.
    """
    if use_plugins:
        try:
            from intake.plugins.discovery import PluginRegistry as PluginReg

            plugin_reg = PluginReg()
            plugin_reg.discover_group("intake.parsers")
            registry = ParserRegistry(plugin_registry=plugin_reg)
            count = registry.discover_parsers()
            if count > 0:
                logger.info(
                    "default_registry_created",
                    source="plugins",
                    formats=registry.registered_formats,
                )
                return registry
        except Exception as exc:
            logger.warning("plugin_discovery_failed", error=str(exc), fallback="manual")

    # Fallback: manual registration (identical to V0 behavior)
    return _create_manual_registry()


def _create_manual_registry() -> ParserRegistry:
    """Create a registry with hardcoded parser registrations.

    This is the V0 fallback path, used when plugin discovery is not
    available (e.g. running from source without pip install).
    """
    from intake.ingest.confluence import ConfluenceParser
    from intake.ingest.docx import DocxParser
    from intake.ingest.github_issues import GithubIssuesParser
    from intake.ingest.gitlab_issues import GitlabIssuesParser
    from intake.ingest.image import ImageParser
    from intake.ingest.jira import JiraParser
    from intake.ingest.markdown import MarkdownParser
    from intake.ingest.pdf import PdfParser
    from intake.ingest.plaintext import PlaintextParser
    from intake.ingest.slack import SlackParser
    from intake.ingest.url import UrlParser
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
    registry.register("url", UrlParser())
    registry.register("slack", SlackParser())
    registry.register("github_issues", GithubIssuesParser())
    registry.register("gitlab_issues", GitlabIssuesParser())

    logger.info("default_registry_created", source="manual", formats=registry.registered_formats)
    return registry
