"""Configuration loading with layered merge.

Priority (highest wins):
    CLI flags -> .intake.yaml -> preset -> hardcoded defaults
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
import yaml

from intake.config.defaults import DEFAULT_CONFIG_FILENAME
from intake.config.presets import apply_preset
from intake.config.schema import IntakeConfig

logger = structlog.get_logger()


class ConfigError(Exception):
    """Raised when configuration loading or validation fails."""

    def __init__(self, reason: str, suggestion: str = "") -> None:
        self.reason = reason
        self.suggestion = suggestion
        msg = f"Configuration error: {reason}"
        if suggestion:
            msg += f"\n  Hint: {suggestion}"
        super().__init__(msg)


def load_config(
    cli_overrides: dict[str, Any] | None = None,
    preset: str | None = None,
    config_path: str = DEFAULT_CONFIG_FILENAME,
) -> IntakeConfig:
    """Load configuration with layered merge.

    Merge order (each layer overrides the previous):
    1. Hardcoded defaults (IntakeConfig())
    2. Preset (if specified)
    3. .intake.yaml (if it exists)
    4. CLI flags (only non-None values)

    Args:
        cli_overrides: Dictionary of CLI flag overrides, keyed by
            dotted paths (e.g. ``{"llm.model": "gpt-4o"}``).
        preset: Optional preset name to apply.
        config_path: Path to the YAML config file.

    Returns:
        Fully resolved IntakeConfig.

    Raises:
        ConfigError: If the config file is invalid or a preset is unknown.
    """
    config = IntakeConfig()

    if preset:
        config = apply_preset(config, preset)
        logger.info("config_preset_applied", preset=preset)

    path = Path(config_path)
    if path.exists():
        config = _merge_yaml(config, path)
        logger.info("config_file_loaded", path=str(path))

    if cli_overrides:
        config = _merge_overrides(config, cli_overrides)
        logger.debug("config_cli_overrides_applied", overrides=list(cli_overrides.keys()))

    return config


def _merge_yaml(config: IntakeConfig, path: Path) -> IntakeConfig:
    """Merge a YAML config file into the current config."""
    try:
        raw = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        raise ConfigError(
            reason=f"Invalid YAML in {path}: {e}",
            suggestion="Check YAML syntax with a validator.",
        ) from e

    if not isinstance(data, dict):
        raise ConfigError(
            reason=f"Expected a mapping in {path}, got {type(data).__name__}",
            suggestion="The config file should be a YAML mapping (key: value pairs).",
        )

    updates: dict[str, Any] = {}
    for section_key, section_data in data.items():
        if not hasattr(config, section_key):
            logger.warning("config_unknown_section", section=section_key, path=str(path))
            continue

        if not isinstance(section_data, dict):
            logger.warning(
                "config_section_not_mapping",
                section=section_key,
                path=str(path),
            )
            continue

        current_section = getattr(config, section_key)
        updates[section_key] = current_section.model_copy(update=section_data)

    return config.model_copy(update=updates)


def _merge_overrides(config: IntakeConfig, overrides: dict[str, Any]) -> IntakeConfig:
    """Merge CLI overrides into the config.

    Overrides use dotted notation: ``llm.model``, ``spec.output_dir``, etc.
    Only non-None values are applied.
    """
    section_updates: dict[str, dict[str, Any]] = {}

    for key, value in overrides.items():
        if value is None:
            continue

        parts = key.split(".", maxsplit=1)
        if len(parts) == 2:
            section, field = parts
            section_updates.setdefault(section, {})[field] = value
        else:
            logger.warning("config_override_no_section", key=key)

    updates: dict[str, Any] = {}
    for section_key, fields in section_updates.items():
        if not hasattr(config, section_key):
            logger.warning("config_override_unknown_section", section=section_key)
            continue
        current_section = getattr(config, section_key)
        updates[section_key] = current_section.model_copy(update=fields)

    return config.model_copy(update=updates)
