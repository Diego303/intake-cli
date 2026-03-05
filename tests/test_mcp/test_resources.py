"""Tests for MCP resources (without requiring the mcp package)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from intake.mcp.resources import FILE_MAP, RESOURCE_URI_PREFIX


@pytest.fixture()
def spec_dir(tmp_path: Path) -> Path:
    """Create a minimal spec directory with all 6 files."""
    spec = tmp_path / "specs" / "auth"
    spec.mkdir(parents=True)

    (spec / "requirements.md").write_text("# Requirements\n\nFR-01: Login\n")
    (spec / "tasks.md").write_text("# Tasks\n\nTask 1: Implement login\n")
    (spec / "context.md").write_text("# Context\n\nPython + FastAPI\n")
    (spec / "design.md").write_text("# Design\n\nREST API\n")
    (spec / "sources.md").write_text("# Sources\n\nreqs.md\n")
    (spec / "acceptance.yaml").write_text(
        yaml.dump({"checks": [{"id": "c1", "name": "test", "type": "command", "command": "true"}]})
    )

    return tmp_path / "specs"


@pytest.fixture()
def partial_spec_dir(tmp_path: Path) -> Path:
    """Create a spec directory with only some files."""
    spec = tmp_path / "specs" / "partial"
    spec.mkdir(parents=True)

    (spec / "requirements.md").write_text("# Requirements\n\nFR-01: Login\n")
    (spec / "tasks.md").write_text("# Tasks\n\nTask 1: Setup\n")

    return tmp_path / "specs"


class TestFileMap:
    """Tests for the FILE_MAP constant."""

    def test_file_map_has_six_entries(self) -> None:
        assert len(FILE_MAP) == 6

    def test_file_map_keys(self) -> None:
        expected = {"requirements", "tasks", "context", "acceptance", "design", "sources"}
        assert set(FILE_MAP.keys()) == expected

    def test_file_map_values_are_filenames(self) -> None:
        for fname in FILE_MAP.values():
            assert "." in fname

    def test_file_map_markdown_files(self) -> None:
        md_keys = {"requirements", "tasks", "context", "design", "sources"}
        for key in md_keys:
            assert FILE_MAP[key].endswith(".md")

    def test_file_map_acceptance_is_yaml(self) -> None:
        assert FILE_MAP["acceptance"].endswith(".yaml")


class TestResourceURIParsing:
    """Tests for URI parsing logic used in read_resource."""

    def test_prefix_value(self) -> None:
        assert RESOURCE_URI_PREFIX == "intake://specs/"

    def test_valid_uri_parsing(self) -> None:
        uri = f"{RESOURCE_URI_PREFIX}auth/requirements"
        parts = uri.removeprefix(RESOURCE_URI_PREFIX).split("/")
        assert parts == ["auth", "requirements"]

    def test_uri_with_nested_spec_name(self) -> None:
        uri = f"{RESOURCE_URI_PREFIX}my-auth/tasks"
        parts = uri.removeprefix(RESOURCE_URI_PREFIX).split("/")
        assert parts == ["my-auth", "tasks"]

    def test_uri_with_all_sections(self) -> None:
        for section in FILE_MAP:
            uri = f"{RESOURCE_URI_PREFIX}test/{section}"
            parts = uri.removeprefix(RESOURCE_URI_PREFIX).split("/")
            assert parts[1] == section
            assert FILE_MAP[parts[1]] is not None

    def test_invalid_uri_too_few_parts(self) -> None:
        uri = f"{RESOURCE_URI_PREFIX}auth"
        parts = uri.removeprefix(RESOURCE_URI_PREFIX).split("/")
        assert len(parts) != 2

    def test_invalid_uri_too_many_parts(self) -> None:
        uri = f"{RESOURCE_URI_PREFIX}auth/tasks/extra"
        parts = uri.removeprefix(RESOURCE_URI_PREFIX).split("/")
        assert len(parts) != 2


class TestResourceIntegration:
    """Integration tests for resource listing and reading."""

    def test_spec_files_exist_on_disk(self, spec_dir: Path) -> None:
        """Verify all spec files created by the fixture exist."""
        spec = spec_dir / "auth"
        for _key, fname in FILE_MAP.items():
            assert (spec / fname).exists(), f"Missing: {fname}"

    def test_resource_content_readable(self, spec_dir: Path) -> None:
        """Verify spec files are readable."""
        spec = spec_dir / "auth"
        content = (spec / "requirements.md").read_text()
        assert "FR-01" in content

    def test_acceptance_yaml_parseable(self, spec_dir: Path) -> None:
        """Verify acceptance.yaml is valid YAML."""
        spec = spec_dir / "auth"
        with open(spec / "acceptance.yaml") as f:
            data = yaml.safe_load(f)
        assert "checks" in data

    def test_partial_spec_has_only_some_files(self, partial_spec_dir: Path) -> None:
        """Verify partial spec only has requirements and tasks."""
        spec = partial_spec_dir / "partial"
        assert (spec / "requirements.md").exists()
        assert (spec / "tasks.md").exists()
        assert not (spec / "context.md").exists()
        assert not (spec / "design.md").exists()

    def test_file_map_section_to_filename_resolution(self, spec_dir: Path) -> None:
        """Verify FILE_MAP correctly maps section names to actual files."""
        spec = spec_dir / "auth"
        for section, fname in FILE_MAP.items():
            fpath = spec / fname
            assert fpath.exists(), f"Section '{section}' maps to missing file '{fname}'"
            content = fpath.read_text()
            assert len(content) > 0, f"File '{fname}' is empty"

    def test_unknown_section_not_in_file_map(self) -> None:
        """Verify unknown section name returns None from FILE_MAP."""
        assert FILE_MAP.get("unknown") is None
        assert FILE_MAP.get("nonexistent") is None
        assert FILE_MAP.get("") is None
