# Example: Custom Parser Plugin

Create a custom parser plugin for intake that adds support for a new input format.

## How Plugins Work

intake discovers plugins via Python [entry points](https://packaging.python.org/en/latest/specifications/entry-points/) (PEP 621). Any pip-installable package can register parsers, exporters, or connectors.

## Creating a Parser Plugin

### 1. Project structure

```
intake-parser-notion/
├── pyproject.toml
├── src/
│   └── intake_parser_notion/
│       ├── __init__.py
│       └── parser.py
└── tests/
    └── test_parser.py
```

### 2. Implement the parser

```python
# src/intake_parser_notion/parser.py

from __future__ import annotations

import json
from pathlib import Path

import structlog

from intake.ingest.base import ParsedContent
from intake.plugins.protocols import ParserPlugin, PluginMeta

logger = structlog.get_logger()


class NotionParser:
    """Parser for Notion HTML exports.

    Supports:
    - Notion exported HTML files
    - Notion exported Markdown files with metadata

    Extracts:
    - Page title, content, sub-pages
    - Database entries as structured sections
    - Callout blocks as notes/warnings
    """

    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="notion",
            version="0.1.0",
            description="Parser for Notion HTML/Markdown exports",
            author="Your Name",
        )

    @property
    def supported_extensions(self) -> list[str]:
        return [".html", ".md"]

    def can_parse(self, source: str) -> bool:
        """Check if this looks like a Notion export."""
        path = Path(source)
        if not path.exists():
            return False
        # Notion exports have specific markers
        if path.suffix.lower() == ".html":
            content = path.read_text(errors="ignore")[:2000]
            return "notion" in content.lower() or "notion-page" in content
        return False

    def confidence(self, source: str) -> float:
        """How confident are we this is a Notion export?"""
        if not self.can_parse(source):
            return 0.0
        path = Path(source)
        content = path.read_text(errors="ignore")[:2000]
        if "notion-page" in content:
            return 0.95
        if "notion" in content.lower():
            return 0.7
        return 0.3

    def parse(self, source: str) -> ParsedContent:
        """Parse a Notion export into normalized content."""
        path = Path(source)
        content = path.read_text(errors="ignore")

        # Your parsing logic here
        # Extract text, metadata, sections, etc.

        logger.info("notion_parsed", source=source)

        return ParsedContent(
            text=content,
            format="notion",
            source=source,
            metadata={"source_type": "notion"},
            sections=[],
            relations=[],
        )
```

### 3. Register as entry point

```toml
# pyproject.toml

[project]
name = "intake-parser-notion"
version = "0.1.0"
dependencies = [
    "intake-ai-cli>=0.4.0",
    "beautifulsoup4>=4.12",
]

[project.entry-points."intake.parsers"]
notion = "intake_parser_notion.parser:NotionParser"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 4. Install and verify

```bash
# Install your plugin
pip install -e .

# Verify it's discovered
intake plugins list

# Check compatibility
intake plugins check

# Use it
intake init "Notion import" -s notion-export.html
```

## Creating an Exporter Plugin

Same pattern, but register under `intake.exporters`:

```python
from intake.plugins.protocols import ExporterPlugin, ExportResult, PluginMeta


class MyAgentExporter:
    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="my-agent",
            version="0.1.0",
            description="Export for My Agent",
        )

    @property
    def supported_agents(self) -> list[str]:
        return ["my-agent"]

    def export(self, spec_dir: str, output_dir: str) -> ExportResult:
        # Generate output files for your agent
        # ...
        return ExportResult(
            files_created=["my-agent-config.yaml"],
            primary_file="my-agent-config.yaml",
            instructions="Run: my-agent start --config my-agent-config.yaml",
        )
```

```toml
[project.entry-points."intake.exporters"]
my-agent = "my_exporter:MyAgentExporter"
```

## Creating a Connector Plugin

Register under `intake.connectors`:

```python
from intake.plugins.protocols import ConnectorPlugin, FetchedSource, PluginMeta


class LinearConnector:
    @property
    def meta(self) -> PluginMeta:
        return PluginMeta(
            name="linear",
            version="0.1.0",
            description="Linear API connector",
        )

    @property
    def uri_schemes(self) -> list[str]:
        return ["linear://"]

    def can_handle(self, uri: str) -> bool:
        return uri.startswith("linear://")

    async def fetch(self, uri: str) -> list[FetchedSource]:
        # Fetch from Linear API, save to temp files
        # ...
        return [FetchedSource(
            local_path="/tmp/linear_issue.json",
            original_uri=uri,
            format_hint="json",
        )]

    def validate_config(self) -> list[str]:
        import os
        if not os.environ.get("LINEAR_API_KEY"):
            return ["LINEAR_API_KEY environment variable is not set"]
        return []
```

```toml
[project.entry-points."intake.connectors"]
linear = "my_connector:LinearConnector"
```

## V1 vs V2 Protocol

intake supports two protocol versions for backwards compatibility:

| Feature | V1 (basic) | V2 (full plugin) |
|---------|-----------|-----------------|
| `meta` property | - | Required |
| `supported_extensions` / `supported_agents` | - | Required |
| `confidence()` method | - | Required (parsers) |
| `can_parse()` / `can_handle()` | Required | Required |
| `parse()` / `export()` / `fetch()` | Required | Required |
| Plugin discovery | Manual only | Entry points |

V1 plugins still work but won't be discoverable via entry points.
