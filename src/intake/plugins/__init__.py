"""Plugin system for intake: discovery, protocols, and hooks."""

from __future__ import annotations

from intake.plugins.discovery import PluginInfo, PluginRegistry, create_registry
from intake.plugins.hooks import HookEvent, HookManager
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

__all__ = [
    "ConnectorPlugin",
    "ExportResult",
    "ExporterPlugin",
    "FetchedSource",
    "HookEvent",
    "HookManager",
    "ParserPlugin",
    "PluginError",
    "PluginInfo",
    "PluginLoadError",
    "PluginMeta",
    "PluginRegistry",
    "create_registry",
]
