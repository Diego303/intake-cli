"""Phase 1 — Input parsers that normalize any format to ParsedContent."""

from __future__ import annotations

from intake.ingest.base import (
    EmptySourceError,
    FileTooLargeError,
    IngestError,
    ParsedContent,
    Parser,
    UnsupportedFormatError,
    read_text_safe,
    validate_file_readable,
)
from intake.ingest.registry import ParserRegistry, create_default_registry

__all__ = [
    "EmptySourceError",
    "FileTooLargeError",
    "IngestError",
    "ParsedContent",
    "Parser",
    "ParserRegistry",
    "UnsupportedFormatError",
    "create_default_registry",
    "read_text_safe",
    "validate_file_readable",
]
