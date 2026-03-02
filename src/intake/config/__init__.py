"""Configuration loading, validation, and presets."""

from __future__ import annotations

from intake.config.loader import load_config
from intake.config.schema import IntakeConfig

__all__ = ["IntakeConfig", "load_config"]
