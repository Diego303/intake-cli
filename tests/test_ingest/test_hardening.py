"""Tests for parser error hardening: empty files, encoding, size limits."""

from __future__ import annotations

from pathlib import Path

import pytest

from intake.ingest.base import (
    MAX_FILE_SIZE_BYTES,
    EmptySourceError,
    FileTooLargeError,
    ParseError,
    read_text_safe,
    validate_file_readable,
)
from intake.ingest.markdown import MarkdownParser
from intake.ingest.plaintext import PlaintextParser
from intake.ingest.yaml_input import YamlInputParser


class TestValidateFileReadable:
    """Tests for the validate_file_readable utility."""

    def test_nonexistent_file_raises(self) -> None:
        with pytest.raises(ParseError, match="File not found"):
            validate_file_readable("/nonexistent/path.txt")

    def test_directory_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ParseError, match="not a file"):
            validate_file_readable(str(tmp_path))

    def test_empty_file_raises(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.txt"
        empty.write_text("")
        with pytest.raises(EmptySourceError):
            validate_file_readable(str(empty))

    def test_valid_file_returns_path(self, tmp_path: Path) -> None:
        valid = tmp_path / "valid.txt"
        valid.write_text("some content")
        result = validate_file_readable(str(valid))
        assert result == valid

    def test_large_file_raises(self, tmp_path: Path) -> None:
        large = tmp_path / "large.txt"
        large.write_text("x")
        with pytest.raises(FileTooLargeError, match="exceeds"):
            import unittest.mock

            original_stat = large.stat()
            fake_stat = original_stat.__class__(
                (
                    original_stat.st_mode,
                    original_stat.st_ino,
                    original_stat.st_dev,
                    original_stat.st_nlink,
                    original_stat.st_uid,
                    original_stat.st_gid,
                    MAX_FILE_SIZE_BYTES + 1,  # st_size
                    int(original_stat.st_atime),
                    int(original_stat.st_mtime),
                    int(original_stat.st_ctime),
                )
            )
            with unittest.mock.patch.object(Path, "stat", return_value=fake_stat):
                validate_file_readable(str(large))


class TestReadTextSafe:
    """Tests for the read_text_safe encoding fallback."""

    def test_reads_utf8(self, tmp_path: Path) -> None:
        f = tmp_path / "utf8.txt"
        f.write_text("Hello, world!", encoding="utf-8")
        result = read_text_safe(str(f), f)
        assert result == "Hello, world!"

    def test_fallback_to_latin1(self, tmp_path: Path) -> None:
        f = tmp_path / "latin1.txt"
        f.write_bytes("Héllo wörld".encode("latin-1"))
        result = read_text_safe(str(f), f)
        assert "rld" in result

    def test_whitespace_only_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "whitespace.txt"
        f.write_text("   \n\n  \t  \n")
        with pytest.raises(EmptySourceError):
            read_text_safe(str(f), f)


class TestMarkdownParserHardening:
    """Hardening tests specific to the Markdown parser."""

    def test_empty_file_raises(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.md"
        empty.write_text("")
        parser = MarkdownParser()
        with pytest.raises(EmptySourceError):
            parser.parse(str(empty))

    def test_whitespace_only_raises(self, tmp_path: Path) -> None:
        ws = tmp_path / "whitespace.md"
        ws.write_text("   \n\n   ")
        parser = MarkdownParser()
        with pytest.raises(EmptySourceError):
            parser.parse(str(ws))

    def test_directory_not_parseable(self, tmp_path: Path) -> None:
        parser = MarkdownParser()
        assert parser.can_parse(str(tmp_path)) is False


class TestPlaintextParserHardening:
    """Hardening tests specific to the Plaintext parser."""

    def test_empty_file_raises(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.txt"
        empty.write_text("")
        parser = PlaintextParser()
        with pytest.raises(EmptySourceError):
            parser.parse(str(empty))

    def test_directory_not_parseable(self, tmp_path: Path) -> None:
        parser = PlaintextParser()
        assert parser.can_parse(str(tmp_path)) is False


class TestYamlParserHardening:
    """Hardening tests specific to the YAML parser."""

    def test_empty_file_raises(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.yaml"
        empty.write_text("")
        parser = YamlInputParser()
        with pytest.raises(EmptySourceError):
            parser.parse(str(empty))

    def test_null_yaml_raises(self, tmp_path: Path) -> None:
        null_yaml = tmp_path / "null.yaml"
        null_yaml.write_text("---\n")
        parser = YamlInputParser()
        with pytest.raises(EmptySourceError):
            parser.parse(str(null_yaml))

    def test_directory_not_parseable(self, tmp_path: Path) -> None:
        parser = YamlInputParser()
        assert parser.can_parse(str(tmp_path)) is False
