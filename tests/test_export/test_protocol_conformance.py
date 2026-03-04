"""Protocol conformance tests for V2 exporters.

Verifies that all V2 exporters satisfy the ExporterPlugin protocol
requirements: meta, supported_agents, and export returning ExportResult.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from intake.export.claude_code import ClaudeCodeExporter
from intake.export.copilot import CopilotExporter
from intake.export.cursor import CursorExporter
from intake.export.kiro import KiroExporter
from intake.plugins.protocols import ExporterPlugin, ExportResult, PluginMeta

EXPORTERS = [
    ClaudeCodeExporter,
    CursorExporter,
    KiroExporter,
    CopilotExporter,
]


class TestExporterProtocolConformance:
    """Verify all V2 exporters satisfy ExporterPlugin protocol."""

    @pytest.mark.parametrize(
        "exporter_cls",
        EXPORTERS,
        ids=lambda c: c.__name__,
    )
    def test_has_meta_property(self, exporter_cls: type) -> None:
        """Exporter has a meta property returning PluginMeta."""
        exporter = exporter_cls()
        meta = exporter.meta
        assert isinstance(meta, PluginMeta)
        assert meta.name
        assert meta.version
        assert meta.description

    @pytest.mark.parametrize(
        "exporter_cls",
        EXPORTERS,
        ids=lambda c: c.__name__,
    )
    def test_has_supported_agents_property(self, exporter_cls: type) -> None:
        """Exporter has a supported_agents property returning a list."""
        exporter = exporter_cls()
        agents = exporter.supported_agents
        assert isinstance(agents, list)
        assert len(agents) > 0
        assert all(isinstance(a, str) for a in agents)

    @pytest.mark.parametrize(
        "exporter_cls",
        EXPORTERS,
        ids=lambda c: c.__name__,
    )
    def test_has_export_method(self, exporter_cls: type) -> None:
        """Exporter has an export method."""
        exporter = exporter_cls()
        assert callable(getattr(exporter, "export", None))

    @pytest.mark.parametrize(
        "exporter_cls",
        EXPORTERS,
        ids=lambda c: c.__name__,
    )
    def test_isinstance_exporter_plugin(self, exporter_cls: type) -> None:
        """Exporter instance satisfies runtime ExporterPlugin check."""
        exporter = exporter_cls()
        assert isinstance(exporter, ExporterPlugin)

    @pytest.mark.parametrize(
        "exporter_cls",
        EXPORTERS,
        ids=lambda c: c.__name__,
    )
    def test_export_returns_export_result(
        self,
        exporter_cls: type,
        tmp_path: Path,
    ) -> None:
        """Export method returns an ExportResult on a minimal spec."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "context.md").write_text("# Context\n")
        (spec_dir / "requirements.md").write_text("# Requirements\n")
        (spec_dir / "design.md").write_text("# Design\n")
        (spec_dir / "tasks.md").write_text("# Tasks\n")
        (spec_dir / "acceptance.yaml").write_text(yaml.dump({"checks": []}))

        output_dir = tmp_path / "output"
        exporter = exporter_cls()
        result = exporter.export(str(spec_dir), str(output_dir))

        assert isinstance(result, ExportResult)
        assert isinstance(result.files_created, list)
        assert result.primary_file
        assert Path(result.primary_file).exists()


class TestConnectorProtocolConformance:
    """Verify all connectors satisfy ConnectorPlugin protocol."""

    def test_jira_connector_has_protocol(self) -> None:
        """JiraConnector satisfies ConnectorPlugin."""
        from intake.connectors.jira_api import JiraConnector
        from intake.plugins.protocols import ConnectorPlugin

        connector = JiraConnector()
        assert isinstance(connector, ConnectorPlugin)
        assert connector.meta.name == "jira"
        assert "jira://" in connector.uri_schemes

    def test_confluence_connector_has_protocol(self) -> None:
        """ConfluenceConnector satisfies ConnectorPlugin."""
        from intake.connectors.confluence_api import ConfluenceConnector
        from intake.plugins.protocols import ConnectorPlugin

        connector = ConfluenceConnector()
        assert isinstance(connector, ConnectorPlugin)
        assert connector.meta.name == "confluence"
        assert "confluence://" in connector.uri_schemes

    def test_github_connector_has_protocol(self) -> None:
        """GithubConnector satisfies ConnectorPlugin."""
        from intake.connectors.github_api import GithubConnector
        from intake.plugins.protocols import ConnectorPlugin

        connector = GithubConnector()
        assert isinstance(connector, ConnectorPlugin)
        assert connector.meta.name == "github"
        assert "github://" in connector.uri_schemes
