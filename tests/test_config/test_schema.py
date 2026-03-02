"""Tests for configuration schema validation."""

from __future__ import annotations

from intake.config.schema import (
    ExportConfig,
    IntakeConfig,
    LLMConfig,
    ProjectConfig,
    SecurityConfig,
    SpecConfig,
    VerificationConfig,
)


class TestLLMConfig:
    def test_defaults(self) -> None:
        config = LLMConfig()
        assert config.model == "claude-sonnet-4"
        assert config.api_key_env == "ANTHROPIC_API_KEY"
        assert config.max_cost_per_spec == 0.50
        assert config.temperature == 0.2
        assert config.max_retries == 3
        assert config.timeout == 120

    def test_custom_values(self) -> None:
        config = LLMConfig(model="gpt-4o", temperature=0.5)
        assert config.model == "gpt-4o"
        assert config.temperature == 0.5


class TestSpecConfig:
    def test_defaults(self) -> None:
        config = SpecConfig()
        assert config.requirements_format == "ears"
        assert config.design_depth == "moderate"
        assert config.generate_lock is True
        assert config.risk_assessment is True

    def test_literal_validation(self) -> None:
        config = SpecConfig(requirements_format="bdd")
        assert config.requirements_format == "bdd"


class TestIntakeConfig:
    def test_defaults(self) -> None:
        config = IntakeConfig()
        assert isinstance(config.llm, LLMConfig)
        assert isinstance(config.project, ProjectConfig)
        assert isinstance(config.spec, SpecConfig)
        assert isinstance(config.verification, VerificationConfig)
        assert isinstance(config.export, ExportConfig)
        assert isinstance(config.security, SecurityConfig)

    def test_nested_override(self) -> None:
        config = IntakeConfig(llm=LLMConfig(model="gpt-4o"))
        assert config.llm.model == "gpt-4o"
        assert config.spec.requirements_format == "ears"

    def test_model_copy_update(self) -> None:
        config = IntakeConfig()
        updated = config.model_copy(
            update={"llm": config.llm.model_copy(update={"model": "gemini-pro"})}
        )
        assert updated.llm.model == "gemini-pro"
        assert config.llm.model == "claude-sonnet-4"
