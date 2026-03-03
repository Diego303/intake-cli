"""Plugin discovery via Python entry points (PEP 621).

Discovers parsers, exporters, and connectors registered as entry points
in ``pyproject.toml`` files. Built-in plugins register themselves through
intake's own ``pyproject.toml``; third-party plugins install their own
entry points via ``pip``.

Entry point groups:
- ``intake.parsers``: input format parsers
- ``intake.exporters``: agent-format exporters
- ``intake.connectors``: live source connectors (API integrations)
"""

from __future__ import annotations

import importlib.metadata
from dataclasses import dataclass

import structlog

from intake.plugins.protocols import (
    ConnectorPlugin,
    ExporterPlugin,
    ParserPlugin,
)

logger = structlog.get_logger()

PARSER_GROUP = "intake.parsers"
EXPORTER_GROUP = "intake.exporters"
CONNECTOR_GROUP = "intake.connectors"

ALL_GROUPS = [PARSER_GROUP, EXPORTER_GROUP, CONNECTOR_GROUP]

# The distribution name for the intake package itself.
BUILTIN_DISTRIBUTION = "intake-ai-cli"


@dataclass
class PluginInfo:
    """Metadata about a discovered plugin.

    Attributes:
        name: Entry point name (e.g. "markdown", "jira").
        group: Entry point group (e.g. "intake.parsers").
        module: Full module:class path (e.g. "intake.ingest.markdown:MarkdownParser").
        distribution: Package that provides this plugin.
        version: Package version.
        is_builtin: True if provided by the intake package itself.
        is_v2: True if the plugin implements the V2 protocol.
        load_error: Non-empty if loading failed.
    """

    name: str
    group: str
    module: str = ""
    distribution: str = ""
    version: str = ""
    is_builtin: bool = False
    is_v2: bool = False
    load_error: str = ""


class PluginRegistry:
    """Central registry for all discovered plugins.

    Discovers plugins via Python entry_points (PEP 621). Built-in
    parsers/exporters register as entry_points in intake's own
    pyproject.toml, so they are discovered via the same mechanism
    as third-party plugins.

    Example::

        registry = PluginRegistry()
        registry.discover_all()
        parsers = registry.get_parsers()
        # parsers["markdown"] is a MarkdownParser instance
    """

    def __init__(self) -> None:
        self._parsers: dict[str, object] = {}
        self._exporters: dict[str, object] = {}
        self._connectors: dict[str, object] = {}
        self._plugin_info: list[PluginInfo] = []

    def discover_all(self) -> None:
        """Discover and load all plugins from all entry point groups."""
        self.discover_group(PARSER_GROUP)
        self.discover_group(EXPORTER_GROUP)
        self.discover_group(CONNECTOR_GROUP)

        logger.info(
            "plugins_discovered",
            parsers=len(self._parsers),
            exporters=len(self._exporters),
            connectors=len(self._connectors),
        )

    def discover_group(self, group: str) -> list[PluginInfo]:
        """Discover plugins for a specific entry point group.

        Args:
            group: Entry point group name (e.g. "intake.parsers").

        Returns:
            List of PluginInfo for discovered plugins.
        """
        target = self._target_for_group(group)
        discovered: list[PluginInfo] = []

        try:
            eps = importlib.metadata.entry_points(group=group)
        except Exception as exc:
            logger.warning("entry_point_scan_failed", group=group, error=str(exc))
            return discovered

        for ep in eps:
            info = self._load_entry_point(ep, group)
            discovered.append(info)
            self._plugin_info.append(info)

            if not info.load_error and info.name not in target:
                target[info.name] = self._instantiate(ep, info)

        logger.debug("group_discovered", group=group, count=len(discovered))
        return discovered

    def get_parsers(self) -> dict[str, object]:
        """Get all discovered parser instances."""
        return dict(self._parsers)

    def get_exporters(self) -> dict[str, object]:
        """Get all discovered exporter instances."""
        return dict(self._exporters)

    def get_connectors(self) -> dict[str, object]:
        """Get all discovered connector instances."""
        return dict(self._connectors)

    def list_plugins(self) -> list[PluginInfo]:
        """List all discovered plugins with metadata, sorted by group and name."""
        return sorted(self._plugin_info, key=lambda p: (p.group, p.name))

    def check_compatibility(self, info: PluginInfo) -> list[str]:
        """Check if a plugin is compatible with this version of intake.

        Args:
            info: Plugin information to check.

        Returns:
            List of compatibility issues. Empty means compatible.
        """
        issues: list[str] = []

        if info.load_error:
            issues.append(f"Plugin failed to load: {info.load_error}")

        return issues

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _target_for_group(self, group: str) -> dict[str, object]:
        """Get the target dict for a group."""
        if group == PARSER_GROUP:
            return self._parsers
        if group == EXPORTER_GROUP:
            return self._exporters
        if group == CONNECTOR_GROUP:
            return self._connectors
        return {}

    def _load_entry_point(
        self,
        ep: importlib.metadata.EntryPoint,
        group: str,
    ) -> PluginInfo:
        """Load metadata from a single entry point without instantiating.

        Args:
            ep: The entry point to inspect.
            group: The group this entry point belongs to.

        Returns:
            PluginInfo with metadata (may have load_error set).
        """
        dist = ep.dist
        dist_name = dist.name if dist else "unknown"
        dist_version = dist.version if dist else "0.0.0"
        is_builtin = dist_name == BUILTIN_DISTRIBUTION

        info = PluginInfo(
            name=ep.name,
            group=group,
            module=ep.value,
            distribution=dist_name,
            version=dist_version,
            is_builtin=is_builtin,
        )

        # Try loading the class to check protocol version
        try:
            cls = ep.load()
            info.is_v2 = self._detect_protocol_version(cls, group)
        except Exception as exc:
            info.load_error = str(exc)
            logger.warning(
                "plugin_load_failed",
                name=ep.name,
                group=group,
                error=str(exc),
            )

        return info

    def _instantiate(
        self,
        ep: importlib.metadata.EntryPoint,
        info: PluginInfo,
    ) -> object:
        """Instantiate a plugin class from an entry point.

        Args:
            ep: The entry point to instantiate.
            info: Plugin info (for logging).

        Returns:
            Plugin instance.
        """
        try:
            cls = ep.load()
            instance = cls()
            logger.debug(
                "plugin_loaded",
                name=info.name,
                group=info.group,
                distribution=info.distribution,
                is_v2=info.is_v2,
            )
            return instance
        except Exception as exc:
            info.load_error = str(exc)
            logger.warning(
                "plugin_instantiation_failed",
                name=info.name,
                group=info.group,
                error=str(exc),
            )
            return None

    def _detect_protocol_version(self, cls: type, group: str) -> bool:
        """Detect if a class implements the V2 protocol.

        Checks for V2-specific attributes (``meta`` property) that V1
        classes do not have.

        Args:
            cls: The plugin class to check.
            group: Entry point group (determines which protocol to check).

        Returns:
            True if the class implements V2 protocol.
        """
        if group == PARSER_GROUP:
            return isinstance(cls, type) and issubclass_safe(cls, ParserPlugin)
        if group == EXPORTER_GROUP:
            return isinstance(cls, type) and issubclass_safe(cls, ExporterPlugin)
        if group == CONNECTOR_GROUP:
            return isinstance(cls, type) and issubclass_safe(cls, ConnectorPlugin)
        return False


def issubclass_safe(cls: type, protocol: type) -> bool:
    """Check if a class satisfies a runtime-checkable Protocol, safely.

    Args:
        cls: Class to check.
        protocol: Protocol to check against.

    Returns:
        True if the class satisfies the protocol.
    """
    try:
        # Create a temporary instance to check against the protocol
        # since Protocol isinstance checks work on instances, not classes
        check_method = "parse" if protocol is ParserPlugin else "export"
        return hasattr(cls, "meta") and hasattr(cls, check_method)
    except Exception:
        return False


def create_registry() -> PluginRegistry:
    """Create and populate a plugin registry.

    Convenience function that creates a PluginRegistry and discovers
    all plugins from entry points.

    Returns:
        A fully populated PluginRegistry.
    """
    registry = PluginRegistry()
    registry.discover_all()
    return registry
