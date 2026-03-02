"""Registry of available exporters."""

from __future__ import annotations

import structlog

from intake.export.base import Exporter, ExportError

logger = structlog.get_logger()


class ExporterRegistry:
    """Registry for format-based exporter dispatch.

    Maps format names to exporter instances.
    """

    def __init__(self) -> None:
        self._exporters: dict[str, Exporter] = {}

    def register(self, format_name: str, exporter: Exporter) -> None:
        """Register an exporter for a format.

        Args:
            format_name: Format identifier (e.g., "architect", "generic").
            exporter: Exporter instance.
        """
        self._exporters[format_name] = exporter
        logger.debug("exporter_registered", format=format_name)

    def get(self, format_name: str) -> Exporter:
        """Get the exporter for a format.

        Args:
            format_name: Format identifier.

        Returns:
            Exporter instance.

        Raises:
            ExportError: If the format is not registered.
        """
        exporter = self._exporters.get(format_name)
        if exporter is None:
            available = ", ".join(sorted(self._exporters.keys()))
            raise ExportError(
                reason=f"Unknown export format: {format_name}",
                suggestion=f"Available formats: {available}",
            )
        return exporter

    @property
    def available_formats(self) -> list[str]:
        """List of registered format names."""
        return sorted(self._exporters.keys())


def create_default_registry() -> ExporterRegistry:
    """Create a registry with all built-in exporters.

    Returns:
        ExporterRegistry with architect and generic exporters registered.
    """
    from intake.export.architect import ArchitectExporter
    from intake.export.generic import GenericExporter

    registry = ExporterRegistry()
    registry.register("architect", ArchitectExporter())
    registry.register("generic", GenericExporter())
    return registry
