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
