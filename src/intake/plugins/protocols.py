"""V2 plugin protocols and supporting data types.

Defines the contracts that all intake plugins (parsers, exporters, connectors)
must satisfy. V2 protocols are supersets of the original V1 protocols — existing
V1 parsers and exporters continue to work unchanged.

Key types:
- PluginMeta: metadata every plugin must provide
- ParserPlugin: V2 parser protocol with confidence scoring
- ExporterPlugin: V2 exporter protocol with ExportResult
- ConnectorPlugin: protocol for live source connectors (async fetch)
- ExportResult: structured result from an export operation
- FetchedSource: result of a connector fetch operation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from intake.ingest.base import ParsedContent

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PluginError(Exception):
    """Base exception for all plugin-related errors."""

    def __init__(self, reason: str, suggestion: str = "") -> None:
        self.reason = reason
        self.suggestion = suggestion
        msg = f"Plugin error: {reason}"
        if suggestion:
            msg += f"\n  Hint: {suggestion}"
        super().__init__(msg)


class PluginLoadError(PluginError):
    """A plugin could not be loaded from its entry point."""

    def __init__(self, name: str, group: str, error: str) -> None:
        self.plugin_name = name
        self.group = group
        super().__init__(
            reason=f"Failed to load plugin '{name}' from group '{group}': {error}",
            suggestion="Check that the plugin package is installed correctly.",
        )


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class PluginMeta:
    """Metadata that every V2 plugin must provide."""

    name: str
    version: str
    description: str
    author: str = ""


@dataclass
class ExportResult:
    """Structured result of an export operation.

    Attributes:
        files_created: Paths to all files created during export.
        primary_file: The main file the user should look at.
        instructions: Human-readable next-step instructions.
    """

    files_created: list[str]
    primary_file: str
    instructions: str = ""


@dataclass
class FetchedSource:
    """Result of a connector fetch operation.

    A connector downloads remote content and saves it as a local temp file
    that parsers can then process.

    Attributes:
        local_path: Path to the temporary file with fetched content.
        original_uri: The original source URI that was fetched.
        format_hint: Detected format for parser dispatch (e.g. "jira", "confluence").
        metadata: Extra key-value metadata about the fetched source.
    """

    local_path: str
    original_uri: str
    format_hint: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# V2 Protocols
# ---------------------------------------------------------------------------


@runtime_checkable
class ParserPlugin(Protocol):
    """V2 parser protocol with metadata and confidence scoring.

    Changes from V1 (``intake.ingest.base.Parser``):
    - Added ``meta`` property for plugin metadata
    - Added ``supported_extensions`` for format discovery
    - Added ``confidence()`` for multi-parser resolution
    - ``can_parse()`` and ``parse()`` remain the same

    Existing V1 parsers do NOT need to implement this protocol.
    The registry handles both V1 and V2 parsers transparently.
    """

    @property
    def meta(self) -> PluginMeta:
        """Plugin metadata."""
        ...

    @property
    def supported_extensions(self) -> set[str]:
        """File extensions this parser handles. E.g. {'.md', '.markdown'}."""
        ...

    def confidence(self, source: str) -> float:
        """How confident is this parser it can handle this source? 0.0-1.0.

        Used when multiple parsers claim they can handle a source.
        Higher confidence wins.

        Args:
            source: Path to the file or source identifier.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        ...

    def can_parse(self, source: str) -> bool:
        """Check if this parser can process the given source.

        Args:
            source: Path to the file or source identifier.

        Returns:
            True if the parser can process this source.
        """
        ...

    def parse(self, source: str) -> ParsedContent:
        """Parse the source and return normalized content.

        Args:
            source: Path to the file or source identifier.

        Returns:
            ParsedContent with extracted text and metadata.
        """
        ...


@runtime_checkable
class ExporterPlugin(Protocol):
    """V2 exporter protocol with metadata and structured result.

    Changes from V1 (``intake.export.base.Exporter``):
    - Added ``meta`` property
    - Added ``supported_agents`` for discovery
    - ``export()`` returns ``ExportResult`` instead of ``list[str]``

    Existing V1 exporters do NOT need to implement this protocol.
    """

    @property
    def meta(self) -> PluginMeta:
        """Plugin metadata."""
        ...

    @property
    def supported_agents(self) -> list[str]:
        """Agent names this exporter targets. E.g. ['claude-code']."""
        ...

    def export(self, spec_dir: str, output_dir: str) -> ExportResult:
        """Export the spec to the target agent format.

        Args:
            spec_dir: Path to the spec directory (contains the 6 spec files).
            output_dir: Path to write exported files.

        Returns:
            ExportResult with metadata about generated files.
        """
        ...


@runtime_checkable
class ConnectorPlugin(Protocol):
    """Protocol for live source connectors.

    Connectors handle remote data fetching. They download content from APIs
    and produce local temp files that parsers can then process.

    Connectors are async (fetch involves network I/O) unlike parsers
    which are always synchronous.
    """

    @property
    def meta(self) -> PluginMeta:
        """Plugin metadata."""
        ...

    @property
    def uri_schemes(self) -> list[str]:
        """URI schemes this connector handles. E.g. ['jira://']."""
        ...

    def can_handle(self, uri: str) -> bool:
        """Check if this connector can handle the given URI.

        Args:
            uri: Source URI string.

        Returns:
            True if this connector can fetch this URI.
        """
        ...

    async def fetch(self, uri: str) -> list[FetchedSource]:
        """Fetch remote source(s) and return local file paths.

        A single URI may produce multiple sources (e.g. a JQL query
        returns multiple issues, each saved as a separate temp file).

        Args:
            uri: Source URI to fetch.

        Returns:
            List of FetchedSource with local temp file paths.
        """
        ...

    def validate_config(self) -> list[str]:
        """Validate that required credentials and configuration are present.

        Returns:
            List of error messages. Empty list means configuration is valid.
        """
        ...
