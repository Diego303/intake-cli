"""Pre-built configuration presets for common use cases.

Presets provide sensible defaults for different team sizes and project types.
They can be selected via ``--preset`` flag or ``preset:`` key in .intake.yaml.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from intake.config.schema import IntakeConfig

logger = structlog.get_logger()

PRESETS: dict[str, dict[str, Any]] = {
    "minimal": {
        # Solo developer, quick prototyping. Low cost, fast output.
        "llm": {"max_cost_per_spec": 0.10, "temperature": 0.3},
        "spec": {
            "requirements_format": "free",
            "design_depth": "minimal",
            "task_granularity": "coarse",
            "include_sources": False,
            "risk_assessment": False,
            "generate_lock": False,
        },
    },
    "standard": {
        # Small-medium teams. Balanced cost vs quality.
        "llm": {"max_cost_per_spec": 0.50, "temperature": 0.2},
        "spec": {
            "requirements_format": "ears",
            "design_depth": "moderate",
            "task_granularity": "medium",
            "include_sources": True,
            "risk_assessment": True,
            "generate_lock": True,
        },
    },
    "enterprise": {
        # Regulated / large teams. Full traceability, detailed output.
        "llm": {"max_cost_per_spec": 2.00, "temperature": 0.1},
        "spec": {
            "requirements_format": "ears",
            "design_depth": "detailed",
            "task_granularity": "fine",
            "include_sources": True,
            "risk_assessment": True,
            "generate_lock": True,
        },
    },
}

PRESET_NAMES = list(PRESETS.keys())


class PresetError(Exception):
    """Raised when an unknown preset name is requested."""

    def __init__(self, preset_name: str) -> None:
        self.preset_name = preset_name
        available = ", ".join(PRESET_NAMES)
        super().__init__(
            f"Unknown preset '{preset_name}'. Available presets: {available}"
        )


def apply_preset(config: IntakeConfig, preset_name: str) -> IntakeConfig:
    """Apply a preset over the base config.

    Preset values override defaults but are themselves overridden by
    explicit .intake.yaml values and CLI flags.

    Args:
        config: The base configuration to apply the preset to.
        preset_name: Name of the preset (minimal, standard, enterprise).

    Returns:
        A new IntakeConfig with preset values applied.

    Raises:
        PresetError: If the preset name is not recognized.
    """
    if preset_name not in PRESETS:
        raise PresetError(preset_name)

    preset = PRESETS[preset_name]
    updates: dict[str, Any] = {}

    for section_key, section_overrides in preset.items():
        current_section = getattr(config, section_key)
        merged = current_section.model_copy(update=section_overrides)
        updates[section_key] = merged

    logger.debug("preset_applied", preset=preset_name, sections=list(updates.keys()))
    return config.model_copy(update=updates)
