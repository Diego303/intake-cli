"""Automatic format detection by file extension and content inspection."""

from __future__ import annotations

from pathlib import Path

import structlog

logger = structlog.get_logger()

EXTENSION_MAP: dict[str, str] = {
    ".md": "markdown",
    ".txt": "plaintext",
    ".pdf": "pdf",
    ".docx": "docx",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".html": "html",
    ".htm": "html",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".webp": "image",
    ".gif": "image",
}

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def detect_format_by_extension(source: str) -> str | None:
    """Detect format by file extension alone.

    Args:
        source: Path to the file, or '-' for stdin.

    Returns:
        Format string if recognized, None otherwise.
    """
    if source == "-":
        return "plaintext"

    ext = Path(source).suffix.lower()
    return EXTENSION_MAP.get(ext)


def is_image_file(source: str) -> bool:
    """Check if a source path points to a supported image file.

    Args:
        source: Path to the file.

    Returns:
        True if the file extension is a supported image format.
    """
    return Path(source).suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
