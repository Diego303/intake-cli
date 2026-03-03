"""Parser for YAML and JSON structured input files.

Supports: .yaml, .yml, .json files with structured requirements.
Extracts: Full text representation, sections from top-level keys, metadata.
"""

from __future__ import annotations

import json
from pathlib import Path

import structlog
import yaml

from intake.ingest.base import (
    EmptySourceError,
    ParsedContent,
    ParseError,
    validate_file_readable,
)

logger = structlog.get_logger()


class YamlInputParser:
    """Parser for YAML/JSON structured requirement files.

    Supports:
    - .yaml / .yml files
    - .json files (that are not Jira exports)
    - Nested structures converted to readable text

    Extracts:
    - Text representation of the structured data
    - Sections from top-level keys
    - Metadata (format type, key count)
    """

    def can_parse(self, source: str) -> bool:
        """Check if this source is a YAML or JSON file."""
        path = Path(source)
        return (
            path.exists() and path.is_file() and path.suffix.lower() in {".yaml", ".yml", ".json"}
        )

    def parse(self, source: str) -> ParsedContent:
        """Parse a YAML/JSON file into normalized content.

        Args:
            source: Path to the YAML or JSON file.

        Returns:
            ParsedContent with text representation and structured sections.

        Raises:
            ParseError: If the file cannot be read or parsed.
        """
        path = validate_file_readable(source)
        data = self._load_data(path)
        if data is None:
            raise EmptySourceError(source)
        text = self._data_to_text(data)
        sections = self._extract_sections(data)
        metadata = self._extract_metadata(data, path)

        logger.info(
            "yaml_parsed",
            source=source,
            sections=len(sections),
            format_type=path.suffix.lower(),
        )

        return ParsedContent(
            text=text,
            format="yaml",
            source=source,
            metadata=metadata,
            sections=sections,
        )

    def _load_data(self, path: Path) -> object:
        """Load data from a YAML or JSON file."""
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as e:
            raise ParseError(
                source=str(path),
                reason=f"Could not read file: {e}",
                suggestion="Check file permissions and path.",
            ) from e

        try:
            if path.suffix.lower() == ".json":
                return json.loads(raw)
            return yaml.safe_load(raw)
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise ParseError(
                source=str(path),
                reason=f"Invalid {path.suffix} syntax: {e}",
                suggestion="Validate the file syntax with a linter.",
            ) from e

    def _data_to_text(self, data: object) -> str:
        """Convert structured data to a readable text representation."""
        return yaml.dump(
            data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    def _extract_sections(self, data: object) -> list[dict[str, str]]:
        """Extract sections from top-level keys of a mapping."""
        if not isinstance(data, dict):
            return []

        sections: list[dict[str, str]] = []
        for key, value in data.items():
            content = yaml.dump(
                value,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
            sections.append(
                {
                    "title": str(key),
                    "content": content.strip(),
                }
            )
        return sections

    def _extract_metadata(self, data: object, path: Path) -> dict[str, str]:
        """Extract basic metadata about the structured data."""
        metadata: dict[str, str] = {
            "source_type": "yaml" if path.suffix.lower() in {".yaml", ".yml"} else "json",
        }
        if isinstance(data, dict):
            metadata["top_level_keys"] = str(len(data))
        elif isinstance(data, list):
            metadata["item_count"] = str(len(data))
        return metadata
