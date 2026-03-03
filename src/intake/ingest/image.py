"""Parser for image files via LLM vision.

Supports: .png, .jpg, .jpeg, .webp, .gif
Extracts: Text description of the image content via LLM vision API.

Note: This is the only parser that requires LLM access. It uses a
callable to delegate vision analysis, avoiding a direct dependency
on the llm/ module.
"""

from __future__ import annotations

import base64
from collections.abc import Callable
from pathlib import Path

import structlog

from intake.ingest.base import ParsedContent, ParseError, validate_file_readable
from intake.utils.file_detect import SUPPORTED_IMAGE_EXTENSIONS

logger = structlog.get_logger()

VISION_PROMPT = (
    "Describe this image in detail for a software requirements analyst. "
    "If it contains a UI mockup, wireframe, or diagram, describe all visible "
    "elements, their layout, labels, and any text. If it contains text, "
    "transcribe it. If it contains a system diagram, describe the components "
    "and their relationships."
)

# Type alias for the vision callback
VisionCallable = Callable[[str, str], str]


def _default_vision_stub(image_base64: str, prompt: str) -> str:
    """Default stub when no vision callable is provided.

    Returns a placeholder indicating LLM vision is needed.
    """
    return (
        "[Image content not analyzed — LLM vision not configured. "
        "Run `intake init` to enable image analysis via LLM.]"
    )


class ImageParser:
    """Parser for image files using LLM vision API.

    Supports:
    - PNG, JPG/JPEG, WebP, GIF images
    - UI mockups, wireframes, diagrams, screenshots
    - Text-heavy images (OCR via vision model)

    Extracts:
    - Detailed text description from LLM vision analysis
    - Image metadata (format, dimensions via filename)

    The ``vision_fn`` parameter allows injecting the LLM vision callable
    at runtime, keeping this parser decoupled from the llm/ module.
    """

    def __init__(self, vision_fn: VisionCallable | None = None) -> None:
        self._vision_fn = vision_fn or _default_vision_stub

    def can_parse(self, source: str) -> bool:
        """Check if this source is a supported image file."""
        path = Path(source)
        return (
            path.exists() and path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
        )

    def parse(self, source: str) -> ParsedContent:
        """Parse an image file using LLM vision.

        Args:
            source: Path to the image file.

        Returns:
            ParsedContent with vision-extracted description.

        Raises:
            ParseError: If the image cannot be read or processed.
        """
        path = validate_file_readable(source)

        try:
            raw_bytes = path.read_bytes()
        except OSError as e:
            raise ParseError(
                source=source,
                reason=f"Could not read image file: {e}",
                suggestion="Check file permissions and path.",
            ) from e

        image_base64 = base64.b64encode(raw_bytes).decode("utf-8")

        try:
            description = self._vision_fn(image_base64, VISION_PROMPT)
        except Exception as e:
            raise ParseError(
                source=source,
                reason=f"Vision analysis failed: {e}",
                suggestion=(
                    "Check your LLM API key and network connection. "
                    "Make sure you are using a model that supports vision."
                ),
            ) from e

        metadata: dict[str, str] = {
            "source_type": "image",
            "image_format": path.suffix.lower().lstrip("."),
            "file_size_bytes": str(len(raw_bytes)),
        }

        logger.info("image_parsed", source=source, format=path.suffix.lower())

        return ParsedContent(
            text=description,
            format="image",
            source=source,
            metadata=metadata,
        )
