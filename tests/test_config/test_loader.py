"""Tests for configuration loading with layered merge."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from intake.config.loader import ConfigError, load_config

if TYPE_CHECKING:
    from pathlib import Path


class TestLoadConfig:
    def test_defaults(self) -> None:
        config = load_config(config_path="/nonexistent/.intake.yaml")
        assert config.llm.model == "claude-sonnet-4"
        assert config.spec.output_dir == "./specs"

    def test_with_preset(self) -> None:
        config = load_config(preset="minimal", config_path="/nonexistent/.intake.yaml")
        assert config.llm.max_cost_per_spec == 0.10
        assert config.spec.requirements_format == "free"

    def test_with_yaml_file(self, tmp_yaml_config: Path) -> None:
        config = load_config(config_path=str(tmp_yaml_config))
        assert config.llm.model == "gpt-4o"
        assert config.llm.max_cost_per_spec == 1.00
        assert config.project.name == "test-project"
        assert config.spec.output_dir == "./custom-specs"

    def test_cli_overrides(self) -> None:
        config = load_config(
            cli_overrides={"llm.model": "gemini-pro", "spec.output_dir": "/tmp/specs"},
            config_path="/nonexistent/.intake.yaml",
        )
        assert config.llm.model == "gemini-pro"
        assert config.spec.output_dir == "/tmp/specs"

    def test_cli_overrides_win_over_yaml(self, tmp_yaml_config: Path) -> None:
        config = load_config(
            cli_overrides={"llm.model": "claude-opus-4"},
            config_path=str(tmp_yaml_config),
        )
        assert config.llm.model == "claude-opus-4"

    def test_none_overrides_ignored(self) -> None:
        config = load_config(
            cli_overrides={"llm.model": None},
            config_path="/nonexistent/.intake.yaml",
        )
        assert config.llm.model == "claude-sonnet-4"

    def test_invalid_yaml_raises(self, invalid_yaml_config: Path) -> None:
        with pytest.raises(ConfigError, match="Invalid YAML"):
            load_config(config_path=str(invalid_yaml_config))

    def test_preset_then_yaml_then_cli(self, tmp_yaml_config: Path) -> None:
        config = load_config(
            cli_overrides={"spec.design_depth": "minimal"},
            preset="enterprise",
            config_path=str(tmp_yaml_config),
        )
        # CLI override wins
        assert config.spec.design_depth == "minimal"
        # YAML wins over preset for model
        assert config.llm.model == "gpt-4o"
