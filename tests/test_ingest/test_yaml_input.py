"""Tests for the YAML/JSON input parser."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from intake.ingest.base import ParseError
from intake.ingest.yaml_input import YamlInputParser

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def parser() -> YamlInputParser:
    return YamlInputParser()


class TestYamlInputParser:
    def test_can_parse_yaml(self, parser: YamlInputParser, yaml_fixture: Path) -> None:
        assert parser.can_parse(str(yaml_fixture)) is True

    def test_cannot_parse_nonexistent(self, parser: YamlInputParser) -> None:
        assert parser.can_parse("/nonexistent/file.yaml") is False

    def test_parse_extracts_text(
        self, parser: YamlInputParser, yaml_fixture: Path
    ) -> None:
        result = parser.parse(str(yaml_fixture))
        assert result.format == "yaml"
        assert "Payment Gateway" in result.text

    def test_parse_extracts_sections(
        self, parser: YamlInputParser, yaml_fixture: Path
    ) -> None:
        result = parser.parse(str(yaml_fixture))
        assert result.has_structure is True
        titles = [s["title"] for s in result.sections]
        assert "project" in titles
        assert "requirements" in titles

    def test_parse_metadata(
        self, parser: YamlInputParser, yaml_fixture: Path
    ) -> None:
        result = parser.parse(str(yaml_fixture))
        assert result.metadata["source_type"] == "yaml"
        assert "top_level_keys" in result.metadata

    def test_parse_json(self, parser: YamlInputParser, tmp_path: Path) -> None:
        json_file = tmp_path / "data.json"
        json_file.write_text('{"key": "value", "items": [1, 2, 3]}')
        result = parser.parse(str(json_file))
        assert result.format == "yaml"
        assert result.metadata["source_type"] == "json"

    def test_parse_invalid_yaml_raises(
        self, parser: YamlInputParser, tmp_path: Path
    ) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text("invalid: yaml: [broken: {")
        with pytest.raises(ParseError, match=r"Invalid \.yaml syntax"):
            parser.parse(str(bad))

    def test_parse_list_data(self, parser: YamlInputParser, tmp_path: Path) -> None:
        list_file = tmp_path / "list.yaml"
        list_file.write_text("- item1\n- item2\n- item3\n")
        result = parser.parse(str(list_file))
        assert result.metadata.get("item_count") == "3"
        assert result.sections == []
