"""Tests for the Image parser."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from intake.ingest.base import ParseError
from intake.ingest.image import ImageParser

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def parser() -> ImageParser:
    return ImageParser()


@pytest.fixture
def parser_with_vision() -> ImageParser:
    def mock_vision(image_base64: str, prompt: str) -> str:
        return "A wireframe showing a login form with email and password fields."

    return ImageParser(vision_fn=mock_vision)


class TestImageParser:
    def test_can_parse_png(self, parser: ImageParser, image_fixture: Path) -> None:
        assert parser.can_parse(str(image_fixture)) is True

    def test_cannot_parse_txt(self, parser: ImageParser, plaintext_fixture: Path) -> None:
        assert parser.can_parse(str(plaintext_fixture)) is False

    def test_cannot_parse_nonexistent(self, parser: ImageParser) -> None:
        assert parser.can_parse("/nonexistent/image.png") is False

    def test_parse_with_stub_returns_placeholder(
        self, parser: ImageParser, image_fixture: Path
    ) -> None:
        result = parser.parse(str(image_fixture))
        assert result.format == "image"
        assert "not analyzed" in result.text.lower() or "not configured" in result.text.lower()

    def test_parse_with_vision_fn(
        self, parser_with_vision: ImageParser, image_fixture: Path
    ) -> None:
        result = parser_with_vision.parse(str(image_fixture))
        assert result.format == "image"
        assert "wireframe" in result.text.lower()
        assert "login" in result.text.lower()

    def test_parse_metadata(self, parser: ImageParser, image_fixture: Path) -> None:
        result = parser.parse(str(image_fixture))
        assert result.metadata["source_type"] == "image"
        assert result.metadata["image_format"] == "png"
        assert int(result.metadata["file_size_bytes"]) > 0

    def test_parse_nonexistent_raises(self, parser: ImageParser) -> None:
        with pytest.raises(ParseError, match="File not found"):
            parser.parse("/nonexistent/image.png")

    def test_parse_vision_error_raises(self, image_fixture: Path) -> None:
        def failing_vision(image_base64: str, prompt: str) -> str:
            raise RuntimeError("API connection failed")

        parser = ImageParser(vision_fn=failing_vision)
        with pytest.raises(ParseError, match="Vision analysis failed"):
            parser.parse(str(image_fixture))
