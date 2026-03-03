"""Source URI parser for multi-format input resolution.

Parses raw source strings from the CLI ``--source`` flag into typed
``SourceURI`` objects so the system can distinguish local files from
URLs, Jira project URIs, GitHub issue references, etc.

Supported formats:
- Local file: ``requirements.md``, ``./path/to/file.pdf``
- Stdin: ``-``
- URL: ``https://...``
- Jira: ``jira://PROJ-123``, ``jira://PROJ?jql=...``
- Confluence: ``confluence://SPACE/page-title``, ``confluence://page/123``
- GitHub: ``github://org/repo/issues/42``, ``github://org/repo/issues?labels=bug``
- Free text: ``"Fix the login button"`` (no scheme, no file extension)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import structlog

logger = structlog.get_logger()

SourceType = Literal["file", "stdin", "url", "jira", "confluence", "github", "text"]

# File extensions that indicate the source is a local file path.
_FILE_EXTENSIONS = {
    ".md",
    ".pdf",
    ".docx",
    ".json",
    ".yaml",
    ".yml",
    ".html",
    ".htm",
    ".txt",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
}


@dataclass
class SourceURI:
    """Parsed source URI.

    Attributes:
        type: Resolved source type.
        raw: Original string as provided by the user.
        path: File path, page title, issue key, URL, or free text.
        params: Query parameters extracted from scheme URIs.
    """

    type: SourceType
    raw: str
    path: str = ""
    params: dict[str, str] = field(default_factory=dict)


# Scheme patterns: scheme name -> regex matching the full URI.
SCHEME_PATTERNS: dict[str, re.Pattern[str]] = {
    "jira": re.compile(r"^jira://(.+)$"),
    "confluence": re.compile(r"^confluence://(.+)$"),
    "github": re.compile(r"^github://(.+)$"),
}


def parse_source(raw: str) -> SourceURI:
    """Parse a raw source string into a typed SourceURI.

    Detection order:
    1. Stdin marker (``-``)
    2. Known scheme patterns (``jira://``, ``confluence://``, ``github://``)
    3. HTTP(S) URLs
    4. Existing file on disk
    5. String that looks like a file path (has extension)
    6. Fallback to free text

    Args:
        raw: Raw source string from CLI ``--source`` flag.

    Returns:
        Parsed SourceURI with type and components.
    """
    raw = raw.strip()

    # 1. Stdin
    if raw == "-":
        logger.debug("source_resolved", raw=raw, type="stdin")
        return SourceURI(type="stdin", raw=raw)

    # 2. Known schemes
    for scheme, pattern in SCHEME_PATTERNS.items():
        match = pattern.match(raw)
        if match:
            remainder = match.group(1)
            path, params = _parse_scheme_path(remainder)
            logger.debug("source_resolved", raw=raw, type=scheme, path=path)
            return SourceURI(type=scheme, raw=raw, path=path, params=params)  # type: ignore[arg-type]

    # 3. HTTP(S) URL
    parsed = urlparse(raw)
    if parsed.scheme in ("http", "https"):
        logger.debug("source_resolved", raw=raw, type="url")
        return SourceURI(type="url", raw=raw, path=raw)

    # 4. Existing file on disk
    if Path(raw).exists():
        logger.debug("source_resolved", raw=raw, type="file")
        return SourceURI(type="file", raw=raw, path=raw)

    # 5. Looks like a file path (has a known extension)
    if _looks_like_file_path(raw):
        logger.debug("source_resolved", raw=raw, type="file")
        return SourceURI(type="file", raw=raw, path=raw)

    # 6. Free text fallback
    logger.debug("source_resolved", raw=raw, type="text")
    return SourceURI(type="text", raw=raw, path=raw)


def _parse_scheme_path(remainder: str) -> tuple[str, dict[str, str]]:
    """Parse the path and query params from a scheme-specific URI.

    Args:
        remainder: Everything after ``scheme://``.

    Returns:
        Tuple of (path, params dict).
    """
    if "?" in remainder:
        path, query = remainder.split("?", 1)
        params = dict(pair.split("=", 1) for pair in query.split("&") if "=" in pair)
        return path, params
    return remainder, {}


def _looks_like_file_path(source: str) -> bool:
    """Heuristic: does this string look like a file path?

    Checks for path separators or known file extensions.

    Args:
        source: String to check.

    Returns:
        True if the string looks like a file path.
    """
    # Has a path separator
    if "/" in source or "\\" in source:
        return True

    # Has a known file extension
    suffix = Path(source).suffix.lower()
    return suffix in _FILE_EXTENSIONS
