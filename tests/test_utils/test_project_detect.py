"""Tests for project tech stack detection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from intake.utils.project_detect import detect_stack

if TYPE_CHECKING:
    from pathlib import Path


class TestDetectStack:
    def test_empty_directory(self, tmp_path: Path) -> None:
        result = detect_stack(str(tmp_path))
        assert result == []

    def test_detects_python(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n")
        result = detect_stack(str(tmp_path))
        assert "python" in result

    def test_detects_javascript(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text('{"name": "test"}')
        result = detect_stack(str(tmp_path))
        assert "javascript" in result
        assert "node" in result

    def test_detects_docker(self, tmp_path: Path) -> None:
        (tmp_path / "Dockerfile").write_text("FROM python:3.12")
        result = detect_stack(str(tmp_path))
        assert "docker" in result

    def test_detects_fastapi_in_pyproject(self, tmp_path: Path) -> None:
        content = '[project]\nname="test"\ndependencies=["fastapi>=0.100"]\n'
        (tmp_path / "pyproject.toml").write_text(content)
        result = detect_stack(str(tmp_path))
        assert "python" in result
        assert "fastapi" in result

    def test_detects_multiple_techs(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n")
        (tmp_path / "Dockerfile").write_text("FROM python:3.12")
        (tmp_path / "Makefile").write_text("test: pytest\n")
        result = detect_stack(str(tmp_path))
        assert "python" in result
        assert "docker" in result
        assert "make" in result

    def test_nonexistent_directory(self) -> None:
        result = detect_stack("/nonexistent/path")
        assert result == []

    def test_sorted_and_deduped(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n")
        (tmp_path / "setup.py").write_text("# setup")
        result = detect_stack(str(tmp_path))
        # python appears in both markers but should be deduped
        assert result.count("python") == 1
        assert result == sorted(result)
