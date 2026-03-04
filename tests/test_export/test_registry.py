"""Tests for the export registry."""

from __future__ import annotations

import pytest

from intake.export.architect import ArchitectExporter
from intake.export.base import Exporter, ExportError
from intake.export.generic import GenericExporter
from intake.export.registry import ExporterRegistry, create_default_registry


def test_register_and_get() -> None:
    """Can register and retrieve an exporter."""
    registry = ExporterRegistry()
    exporter = GenericExporter()
    registry.register("generic", exporter)

    retrieved = registry.get("generic")
    assert retrieved is exporter


def test_get_unknown_raises() -> None:
    """Getting an unregistered format raises ExportError."""
    registry = ExporterRegistry()
    with pytest.raises(ExportError, match="Unknown export format"):
        registry.get("nonexistent")


def test_available_formats() -> None:
    """available_formats returns sorted list of registered formats."""
    registry = ExporterRegistry()
    registry.register("generic", GenericExporter())
    registry.register("architect", ArchitectExporter())

    assert registry.available_formats == ["architect", "generic"]


def test_default_registry_has_architect() -> None:
    """Default registry includes the architect exporter."""
    registry = create_default_registry()
    exporter = registry.get("architect")
    assert isinstance(exporter, ArchitectExporter)


def test_default_registry_has_generic() -> None:
    """Default registry includes the generic exporter."""
    registry = create_default_registry()
    exporter = registry.get("generic")
    assert isinstance(exporter, GenericExporter)


def test_exporters_satisfy_protocol() -> None:
    """Both exporters satisfy the Exporter protocol."""
    assert isinstance(ArchitectExporter(), Exporter)
    assert isinstance(GenericExporter(), Exporter)


def test_plugin_discovery_finds_exporters() -> None:
    """Plugin discovery via entry_points finds all built-in exporters."""
    registry = create_default_registry(use_plugins=True)
    assert "architect" in registry.available_formats
    assert "generic" in registry.available_formats


def test_manual_fallback_works() -> None:
    """Manual fallback creates the same set of exporters."""
    registry = create_default_registry(use_plugins=False)
    assert registry.available_formats == [
        "architect",
        "claude-code",
        "copilot",
        "cursor",
        "generic",
        "kiro",
    ]


def test_plugin_and_manual_produce_same_formats() -> None:
    """Plugin discovery and manual registration produce the same formats."""
    plugin_registry = create_default_registry(use_plugins=True)
    manual_registry = create_default_registry(use_plugins=False)
    assert plugin_registry.available_formats == manual_registry.available_formats
