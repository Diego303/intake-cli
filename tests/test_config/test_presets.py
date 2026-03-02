"""Tests for configuration presets."""

from __future__ import annotations

import pytest

from intake.config.presets import PRESETS, PresetError, apply_preset
from intake.config.schema import IntakeConfig


class TestPresets:
    def test_minimal_preset(self) -> None:
        config = apply_preset(IntakeConfig(), "minimal")
        assert config.llm.max_cost_per_spec == 0.10
        assert config.spec.requirements_format == "free"
        assert config.spec.design_depth == "minimal"
        assert config.spec.risk_assessment is False
        assert config.spec.generate_lock is False

    def test_standard_preset(self) -> None:
        config = apply_preset(IntakeConfig(), "standard")
        assert config.llm.max_cost_per_spec == 0.50
        assert config.spec.requirements_format == "ears"
        assert config.spec.design_depth == "moderate"
        assert config.spec.risk_assessment is True

    def test_enterprise_preset(self) -> None:
        config = apply_preset(IntakeConfig(), "enterprise")
        assert config.llm.max_cost_per_spec == 2.00
        assert config.llm.temperature == 0.1
        assert config.spec.design_depth == "detailed"
        assert config.spec.task_granularity == "fine"

    def test_unknown_preset_raises(self) -> None:
        with pytest.raises(PresetError, match="Unknown preset 'nonexistent'"):
            apply_preset(IntakeConfig(), "nonexistent")

    def test_preset_does_not_modify_original(self) -> None:
        original = IntakeConfig()
        _result = apply_preset(original, "minimal")
        assert original.llm.max_cost_per_spec == 0.50

    def test_all_presets_defined(self) -> None:
        assert "minimal" in PRESETS
        assert "standard" in PRESETS
        assert "enterprise" in PRESETS
