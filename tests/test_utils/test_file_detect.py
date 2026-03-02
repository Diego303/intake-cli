"""Tests for file format detection utilities."""

from __future__ import annotations

from intake.utils.file_detect import (
    EXTENSION_MAP,
    detect_format_by_extension,
    is_image_file,
)


class TestDetectFormatByExtension:
    def test_markdown(self) -> None:
        assert detect_format_by_extension("readme.md") == "markdown"

    def test_plaintext(self) -> None:
        assert detect_format_by_extension("notes.txt") == "plaintext"

    def test_pdf(self) -> None:
        assert detect_format_by_extension("doc.pdf") == "pdf"

    def test_docx(self) -> None:
        assert detect_format_by_extension("doc.docx") == "docx"

    def test_yaml(self) -> None:
        assert detect_format_by_extension("config.yaml") == "yaml"
        assert detect_format_by_extension("config.yml") == "yaml"

    def test_json(self) -> None:
        assert detect_format_by_extension("data.json") == "json"

    def test_html(self) -> None:
        assert detect_format_by_extension("page.html") == "html"
        assert detect_format_by_extension("page.htm") == "html"

    def test_image(self) -> None:
        assert detect_format_by_extension("img.png") == "image"
        assert detect_format_by_extension("img.jpg") == "image"
        assert detect_format_by_extension("img.jpeg") == "image"
        assert detect_format_by_extension("img.webp") == "image"
        assert detect_format_by_extension("img.gif") == "image"

    def test_stdin(self) -> None:
        assert detect_format_by_extension("-") == "plaintext"

    def test_unknown_extension(self) -> None:
        assert detect_format_by_extension("file.xyz") is None

    def test_case_insensitive(self) -> None:
        assert detect_format_by_extension("FILE.MD") == "markdown"


class TestIsImageFile:
    def test_png(self) -> None:
        assert is_image_file("test.png") is True

    def test_jpg(self) -> None:
        assert is_image_file("test.jpg") is True

    def test_non_image(self) -> None:
        assert is_image_file("test.pdf") is False

    def test_case_insensitive(self) -> None:
        assert is_image_file("test.PNG") is True


class TestExtensionMap:
    def test_all_expected_formats_present(self) -> None:
        expected = {".md", ".txt", ".pdf", ".docx", ".json", ".yaml", ".yml",
                    ".html", ".htm", ".png", ".jpg", ".jpeg", ".webp", ".gif"}
        assert expected.issubset(set(EXTENSION_MAP.keys()))
