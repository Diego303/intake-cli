"""Tests for plugin protocols and supporting data types."""

from __future__ import annotations

from intake.ingest.base import ParsedContent
from intake.plugins.protocols import (
    ConnectorPlugin,
    ExporterPlugin,
    ExportResult,
    FetchedSource,
    ParserPlugin,
    PluginError,
    PluginLoadError,
    PluginMeta,
)

# ---------------------------------------------------------------------------
# Dataclass tests
# ---------------------------------------------------------------------------


class TestPluginMeta:
    def test_create_with_required_fields(self) -> None:
        meta = PluginMeta(name="test", version="1.0.0", description="A test plugin")
        assert meta.name == "test"
        assert meta.version == "1.0.0"
        assert meta.description == "A test plugin"
        assert meta.author == ""

    def test_create_with_author(self) -> None:
        meta = PluginMeta(name="test", version="1.0.0", description="desc", author="me")
        assert meta.author == "me"


class TestExportResult:
    def test_create_with_required_fields(self) -> None:
        result = ExportResult(files_created=["a.md", "b.sh"], primary_file="a.md")
        assert result.files_created == ["a.md", "b.sh"]
        assert result.primary_file == "a.md"
        assert result.instructions == ""

    def test_create_with_instructions(self) -> None:
        result = ExportResult(
            files_created=["CLAUDE.md"],
            primary_file="CLAUDE.md",
            instructions="Run claude-code with this file.",
        )
        assert "claude-code" in result.instructions


class TestFetchedSource:
    def test_create_with_required_fields(self) -> None:
        fs = FetchedSource(local_path="/tmp/issue.json", original_uri="jira://PROJ-123")
        assert fs.local_path == "/tmp/issue.json"
        assert fs.original_uri == "jira://PROJ-123"
        assert fs.format_hint == ""
        assert fs.metadata == {}

    def test_create_with_all_fields(self) -> None:
        fs = FetchedSource(
            local_path="/tmp/issue.json",
            original_uri="jira://PROJ-123",
            format_hint="jira",
            metadata={"key": "PROJ-123", "summary": "Auth feature"},
        )
        assert fs.format_hint == "jira"
        assert fs.metadata["key"] == "PROJ-123"


# ---------------------------------------------------------------------------
# Exception tests
# ---------------------------------------------------------------------------


class TestPluginError:
    def test_message_without_suggestion(self) -> None:
        err = PluginError(reason="something broke")
        assert "something broke" in str(err)
        assert err.reason == "something broke"
        assert err.suggestion == ""

    def test_message_with_suggestion(self) -> None:
        err = PluginError(reason="failed", suggestion="try again")
        assert "failed" in str(err)
        assert "try again" in str(err)


class TestPluginLoadError:
    def test_message_contains_plugin_info(self) -> None:
        err = PluginLoadError(
            name="bad-parser",
            group="intake.parsers",
            error="ModuleNotFoundError",
        )
        assert "bad-parser" in str(err)
        assert "intake.parsers" in str(err)
        assert "ModuleNotFoundError" in str(err)
        assert err.plugin_name == "bad-parser"
        assert err.group == "intake.parsers"


# ---------------------------------------------------------------------------
# Protocol conformance tests
# ---------------------------------------------------------------------------


class TestParserPluginProtocol:
    def test_v1_parser_does_not_satisfy_v2(self) -> None:
        """Existing V1 parsers lack meta, supported_extensions, confidence."""
        from intake.ingest.markdown import MarkdownParser

        parser = MarkdownParser()
        assert not isinstance(parser, ParserPlugin)

    def test_v2_parser_satisfies_protocol(self) -> None:
        """A properly shaped class satisfies ParserPlugin."""

        class MyV2Parser:
            @property
            def meta(self) -> PluginMeta:
                return PluginMeta(name="test", version="1.0", description="test parser")

            @property
            def supported_extensions(self) -> set[str]:
                return {".test"}

            def confidence(self, source: str) -> float:
                return 0.5

            def can_parse(self, source: str) -> bool:
                return source.endswith(".test")

            def parse(self, source: str) -> ParsedContent:
                return ParsedContent(text="", format="test", source=source)

        assert isinstance(MyV2Parser(), ParserPlugin)


class TestExporterPluginProtocol:
    def test_v1_exporter_does_not_satisfy_v2(self) -> None:
        """Existing V1 exporters lack meta, supported_agents, and return list[str]."""
        from intake.export.generic import GenericExporter

        exporter = GenericExporter()
        assert not isinstance(exporter, ExporterPlugin)

    def test_v2_exporter_satisfies_protocol(self) -> None:
        class MyV2Exporter:
            @property
            def meta(self) -> PluginMeta:
                return PluginMeta(name="test", version="1.0", description="test exporter")

            @property
            def supported_agents(self) -> list[str]:
                return ["test-agent"]

            def export(self, spec_dir: str, output_dir: str) -> ExportResult:
                return ExportResult(files_created=[], primary_file="")

        assert isinstance(MyV2Exporter(), ExporterPlugin)


class TestConnectorPluginProtocol:
    def test_connector_satisfies_protocol(self) -> None:
        class MyConnector:
            @property
            def meta(self) -> PluginMeta:
                return PluginMeta(name="test", version="1.0", description="test connector")

            @property
            def uri_schemes(self) -> list[str]:
                return ["test://"]

            def can_handle(self, uri: str) -> bool:
                return uri.startswith("test://")

            async def fetch(self, uri: str) -> list[FetchedSource]:
                return []

            def validate_config(self) -> list[str]:
                return []

        assert isinstance(MyConnector(), ConnectorPlugin)
