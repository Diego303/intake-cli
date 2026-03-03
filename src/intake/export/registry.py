"""Registry of available exporters.

Supports both V1 exporters (manual registration) and V2 exporters
(plugin discovery via entry points).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from intake.export.base import Exporter, ExportError

if TYPE_CHECKING:
    from intake.plugins.discovery import PluginRegistry

logger = structlog.get_logger()


class ExporterRegistry:
    """Registry for format-based exporter dispatch.

    Maps format names to exporter instances. Can be backed by a
    ``PluginRegistry`` for automatic exporter discovery.
    """

    def __init__(self, plugin_registry: PluginRegistry | None = None) -> None:
        self._exporters: dict[str, Exporter] = {}
        self._plugin_registry = plugin_registry

    def register(self, format_name: str, exporter: Exporter) -> None:
        """Register an exporter for a format.

        Args:
            format_name: Format identifier (e.g., "architect", "generic").
            exporter: Exporter instance.
        """
        self._exporters[format_name] = exporter
        logger.debug("exporter_registered", format=format_name)

    def discover_exporters(self) -> int:
        """Discover and register exporters from the plugin registry.

        Only registers exporters that are not already manually registered.

        Returns:
            Number of exporters discovered and registered.
        """
        if self._plugin_registry is None:
            return 0

        exporters = self._plugin_registry.get_exporters()
        count = 0
        for name, exporter_instance in exporters.items():
            if name not in self._exporters and exporter_instance is not None:
                self._exporters[name] = exporter_instance  # type: ignore[assignment]
                count += 1
                logger.debug("exporter_discovered", name=name)

        logger.info("exporters_discovered", count=count)
        return count

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


def create_default_registry(use_plugins: bool = True) -> ExporterRegistry:
    """Create a registry with all built-in exporters.

    When ``use_plugins`` is True, attempts to discover exporters from
    Python entry points first. Falls back to manual registration if
    plugin discovery fails or finds no exporters.

    Args:
        use_plugins: Whether to attempt plugin-based discovery.

    Returns:
        ExporterRegistry with all available exporters registered.
    """
    if use_plugins:
        try:
            from intake.plugins.discovery import PluginRegistry as PluginReg

            plugin_reg = PluginReg()
            plugin_reg.discover_group("intake.exporters")
            registry = ExporterRegistry(plugin_registry=plugin_reg)
            count = registry.discover_exporters()
            if count > 0:
                logger.info(
                    "default_exporter_registry_created",
                    source="plugins",
                    formats=registry.available_formats,
                )
                return registry
        except Exception as exc:
            logger.warning("exporter_plugin_discovery_failed", error=str(exc), fallback="manual")

    # Fallback: manual registration
    return _create_manual_registry()


def _create_manual_registry() -> ExporterRegistry:
    """Create a registry with hardcoded exporter registrations."""
    from intake.export.architect import ArchitectExporter
    from intake.export.generic import GenericExporter

    registry = ExporterRegistry()
    registry.register("architect", ArchitectExporter())
    registry.register("generic", GenericExporter())

    logger.info(
        "default_exporter_registry_created",
        source="manual",
        formats=registry.available_formats,
    )
    return registry
