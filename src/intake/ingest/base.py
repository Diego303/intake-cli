"""Base types for the ingest module.

Defines ParsedContent (the normalized output of any parser) and the Parser
Protocol that all parsers must satisfy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

import structlog

logger = structlog.get_logger()

# Maximum file size we'll attempt to parse (50 MB).
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024


class IngestError(Exception):
    """Base exception for all ingest errors."""


class ParseError(IngestError):
    """A source file could not be parsed.

    Attributes:
        source: Path or identifier of the source that failed.
        reason: Human-readable explanation of why parsing failed.
        suggestion: Optional hint for the user on how to fix the issue.
    """

    def __init__(self, source: str, reason: str, suggestion: str = "") -> None:
        self.source = source
        self.reason = reason
        self.suggestion = suggestion
        msg = f"Failed to parse '{source}': {reason}"
        if suggestion:
            msg += f"\n  Hint: {suggestion}"
        super().__init__(msg)


class EmptySourceError(ParseError):
    """The source file exists but contains no usable content."""

    def __init__(self, source: str) -> None:
        super().__init__(
            source=source,
            reason="File is empty or contains only whitespace",
            suggestion="Provide a file with actual content.",
        )


class FileTooLargeError(ParseError):
    """The source file exceeds the maximum allowed size."""

    def __init__(self, source: str, size_bytes: int) -> None:
        size_mb = size_bytes / (1024 * 1024)
        limit_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
        super().__init__(
            source=source,
            reason=f"File is {size_mb:.1f} MB, exceeds {limit_mb:.0f} MB limit",
            suggestion="Split the file into smaller parts or increase the limit.",
        )


def validate_file_readable(source: str) -> Path:
    """Validate that a file exists, is not empty, and is within size limits.

    Args:
        source: Path to the file to validate.

    Returns:
        Resolved Path object.

    Raises:
        ParseError: If the file does not exist or cannot be accessed.
        EmptySourceError: If the file is empty.
        FileTooLargeError: If the file exceeds the size limit.
    """
    path = Path(source)

    if not path.exists():
        raise ParseError(
            source=source,
            reason="File not found",
            suggestion="Check the file path and try again.",
        )

    if not path.is_file():
        raise ParseError(
            source=source,
            reason="Path is not a file",
            suggestion="Provide a path to a file, not a directory.",
        )

    size = path.stat().st_size
    if size == 0:
        raise EmptySourceError(source)

    if size > MAX_FILE_SIZE_BYTES:
        raise FileTooLargeError(source, size)

    return path


def read_text_safe(source: str, path: Path) -> str:
    """Read a text file with encoding fallback.

    Tries UTF-8 first, falls back to latin-1 with a warning.

    Args:
        source: Original source identifier (for error messages).
        path: Path to the file.

    Returns:
        File contents as a string.

    Raises:
        ParseError: If the file cannot be read.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        logger.warning(
            "encoding_fallback",
            source=source,
            original="utf-8",
            fallback="latin-1",
        )
        try:
            text = path.read_text(encoding="latin-1")
        except OSError as e:
            raise ParseError(
                source=source,
                reason=f"Could not read file: {e}",
                suggestion="Check file permissions and path.",
            ) from e
    except OSError as e:
        raise ParseError(
            source=source,
            reason=f"Could not read file: {e}",
            suggestion="Check file permissions and path.",
        ) from e

    if not text.strip():
        raise EmptySourceError(source)

    return text


class UnsupportedFormatError(IngestError):
    """The source format is not supported by any registered parser."""

    def __init__(self, source: str, detected_format: str) -> None:
        self.source = source
        self.detected_format = detected_format
        super().__init__(
            f"No parser available for format '{detected_format}' "
            f"(source: '{source}')"
        )


@dataclass
class ParsedContent:
    """Normalized content from any source.

    All parsers produce this same structure, regardless of the input format.
    This allows the analyze module to always work with the same data type.

    Attributes:
        text: Extracted, clean text content.
        format: Format identifier (e.g. "markdown", "jira", "pdf").
        source: Original file path or source identifier.
        metadata: Key-value pairs (author, date, priority, labels, etc.).
        assets: Paths to extracted assets (images, diagrams).
        sections: Structured sections extracted from the content.
        relations: Relationships between items (blocks, depends on, etc.).
    """

    text: str
    format: str
    source: str
    metadata: dict[str, str] = field(default_factory=dict)
    assets: list[Path] = field(default_factory=list)
    sections: list[dict[str, str]] = field(default_factory=list)
    relations: list[dict[str, str]] = field(default_factory=list)

    @property
    def word_count(self) -> int:
        """Number of words in the extracted text."""
        return len(self.text.split())

    @property
    def has_structure(self) -> bool:
        """Whether the content has structured sections."""
        return len(self.sections) > 0


@runtime_checkable
class Parser(Protocol):
    """Protocol that all parsers must implement.

    To create a new parser:
    1. Implement can_parse() and parse()
    2. Register it in the ParserRegistry
    """

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

        Raises:
            ParseError: If the file cannot be parsed.
        """
        ...
