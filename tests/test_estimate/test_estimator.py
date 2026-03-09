"""Tests for the LLM cost estimator."""

from __future__ import annotations

from pathlib import Path

import pytest

from intake.config.schema import EstimateConfig, LLMConfig
from intake.estimate.estimator import (
    CostEstimate,
    CostEstimator,
)
from intake.ingest.base import ParsedContent


def _make_source(text: str, fmt: str = "markdown") -> ParsedContent:
    """Create a minimal ParsedContent for testing."""
    return ParsedContent(text=text, format=fmt, source="test.md")


class TestCostEstimateFormatting:
    """Tests for CostEstimate.formatted_cost property."""

    def test_small_cost_uses_four_decimals(self) -> None:
        estimate = CostEstimate(
            mode="quick",
            mode_auto_detected=True,
            total_input_words=100,
            total_input_tokens=1000,
            total_output_tokens=400,
            llm_calls=1,
            model="claude-sonnet-4",
            estimated_cost_usd=0.005,
        )
        assert estimate.formatted_cost == "$0.0050"

    def test_larger_cost_uses_two_decimals(self) -> None:
        estimate = CostEstimate(
            mode="enterprise",
            mode_auto_detected=False,
            total_input_words=5000,
            total_input_tokens=50000,
            total_output_tokens=30000,
            llm_calls=4,
            model="claude-opus-4",
            estimated_cost_usd=1.23,
        )
        assert estimate.formatted_cost == "$1.23"

    def test_zero_cost(self) -> None:
        estimate = CostEstimate(
            mode="quick",
            mode_auto_detected=True,
            total_input_words=0,
            total_input_tokens=0,
            total_output_tokens=0,
            llm_calls=1,
            model="claude-sonnet-4",
            estimated_cost_usd=0.0,
        )
        assert estimate.formatted_cost == "$0.0000"


class TestEstimateFromFiles:
    """Tests for CostEstimator.estimate_from_files()."""

    def test_single_small_file(self, tmp_path: Path) -> None:
        f = tmp_path / "reqs.md"
        f.write_text("This is a small requirements file with a few words.")
        estimator = CostEstimator()
        result = estimator.estimate_from_files([str(f)])

        assert result.mode == "quick"
        assert result.mode_auto_detected is True
        assert result.total_input_words > 0
        assert result.total_input_tokens > 0
        assert result.total_output_tokens > 0
        assert result.estimated_cost_usd > 0.0

    def test_nonexistent_file_raises_error(self) -> None:
        """BUG-003: Nonexistent files must raise FileNotFoundError."""
        estimator = CostEstimator()
        with pytest.raises(FileNotFoundError, match="not found"):
            estimator.estimate_from_files(["/nonexistent/file.md"])

    def test_explicit_mode_overrides_detection(self, tmp_path: Path) -> None:
        f = tmp_path / "reqs.md"
        f.write_text("Short file.")
        estimator = CostEstimator()
        result = estimator.estimate_from_files([str(f)], mode="enterprise")

        assert result.mode == "enterprise"
        assert result.mode_auto_detected is False

    def test_multiple_files_detects_enterprise(self, tmp_path: Path) -> None:
        for i in range(5):
            (tmp_path / f"file{i}.md").write_text(f"Content for file {i}.")
        files = [str(tmp_path / f"file{i}.md") for i in range(5)]
        estimator = CostEstimator()
        result = estimator.estimate_from_files(files)

        assert result.mode == "enterprise"

    def test_large_single_file_detects_enterprise(self, tmp_path: Path) -> None:
        f = tmp_path / "large.md"
        f.write_text("word " * 6000)
        estimator = CostEstimator()
        result = estimator.estimate_from_files([str(f)])

        assert result.mode == "enterprise"

    def test_medium_file_detects_standard(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.md"
        f2 = tmp_path / "b.md"
        f1.write_text("word " * 300)
        f2.write_text("word " * 300)
        estimator = CostEstimator()
        result = estimator.estimate_from_files([str(f1), str(f2)])

        assert result.mode == "standard"


class TestEstimateFromSources:
    """Tests for CostEstimator.estimate_from_sources()."""

    def test_basic_estimate(self) -> None:
        sources = [_make_source("word " * 100)]
        estimator = CostEstimator()
        result = estimator.estimate_from_sources(sources)

        assert result.total_input_words == 100
        assert result.mode_auto_detected is True
        assert result.estimated_cost_usd > 0

    def test_explicit_mode(self) -> None:
        sources = [_make_source("word " * 100)]
        estimator = CostEstimator()
        result = estimator.estimate_from_sources(sources, mode="enterprise")

        assert result.mode == "enterprise"
        assert result.mode_auto_detected is False

    def test_empty_sources_gives_quick(self) -> None:
        estimator = CostEstimator()
        result = estimator.estimate_from_sources([])

        assert result.mode == "quick"
        assert result.total_input_words == 0


class TestPricingTable:
    """Tests for model pricing and cost calculation."""

    def test_known_model_uses_specific_pricing(self) -> None:
        llm_config = LLMConfig(model="gpt-4o-mini")
        estimator = CostEstimator(llm_config=llm_config)
        result = estimator.estimate_from_sources([_make_source("word " * 100)], mode="quick")

        assert result.model == "gpt-4o-mini"
        assert len(result.warnings) == 0

    def test_unknown_model_uses_default_pricing_with_warning(self) -> None:
        llm_config = LLMConfig(model="unknown-model-v99")
        estimator = CostEstimator(llm_config=llm_config)
        result = estimator.estimate_from_sources([_make_source("word " * 100)], mode="quick")

        assert result.model == "unknown-model-v99"
        assert any("not in pricing table" in w for w in result.warnings)

    def test_budget_warning_when_cost_exceeds_max(self) -> None:
        llm_config = LLMConfig(model="claude-opus-4", max_cost_per_spec=0.01)
        estimator = CostEstimator(llm_config=llm_config)
        result = estimator.estimate_from_sources([_make_source("word " * 2000)], mode="enterprise")

        assert any("exceeds budget" in w for w in result.warnings)

    def test_no_budget_warning_when_within_limit(self) -> None:
        llm_config = LLMConfig(model="deepseek-chat", max_cost_per_spec=10.0)
        estimator = CostEstimator(llm_config=llm_config)
        result = estimator.estimate_from_sources([_make_source("word " * 10)], mode="quick")

        budget_warnings = [w for w in result.warnings if "exceeds budget" in w]
        assert len(budget_warnings) == 0


class TestCostBreakdown:
    """Tests for cost breakdown structure."""

    def test_breakdown_has_input_and_output(self) -> None:
        estimator = CostEstimator()
        result = estimator.estimate_from_sources([_make_source("word " * 100)], mode="standard")

        assert len(result.cost_breakdown) == 2
        labels = [item["label"] for item in result.cost_breakdown]
        assert "Input tokens" in labels
        assert "Output tokens" in labels

    def test_breakdown_costs_sum_to_total(self) -> None:
        estimator = CostEstimator()
        result = estimator.estimate_from_sources([_make_source("word " * 500)], mode="standard")

        breakdown_total = sum(item["cost_usd"] for item in result.cost_breakdown)
        assert abs(breakdown_total - result.estimated_cost_usd) < 1e-10


class TestCustomConfig:
    """Tests for custom EstimateConfig parameters."""

    def test_custom_tokens_per_word(self) -> None:
        config = EstimateConfig(tokens_per_word=2.0)
        estimator = CostEstimator(config=config)
        result = estimator.estimate_from_sources([_make_source("word " * 100)], mode="quick")

        # With 2.0 tokens/word, should have more tokens than default (1.35)
        default_estimator = CostEstimator()
        default_result = default_estimator.estimate_from_sources(
            [_make_source("word " * 100)], mode="quick"
        )
        assert result.total_input_tokens > default_result.total_input_tokens

    def test_custom_overhead_tokens(self) -> None:
        config = EstimateConfig(prompt_overhead_tokens=5000)
        estimator = CostEstimator(config=config)
        result = estimator.estimate_from_sources([_make_source("word " * 100)], mode="quick")

        default_estimator = CostEstimator()
        default_result = default_estimator.estimate_from_sources(
            [_make_source("word " * 100)], mode="quick"
        )
        assert result.total_input_tokens > default_result.total_input_tokens

    def test_calls_per_mode_affects_cost(self) -> None:
        config = EstimateConfig(calls_per_mode={"quick": 1, "standard": 10, "enterprise": 20})
        estimator = CostEstimator(config=config)
        result = estimator.estimate_from_sources([_make_source("word " * 100)], mode="standard")

        default_estimator = CostEstimator()
        default_result = default_estimator.estimate_from_sources(
            [_make_source("word " * 100)], mode="standard"
        )
        # 10 calls vs default 3 calls → more tokens and higher cost
        assert result.estimated_cost_usd > default_result.estimated_cost_usd


class TestLLMCallCount:
    """Tests for LLM call count in estimate."""

    def test_quick_mode_call_count(self) -> None:
        estimator = CostEstimator()
        result = estimator.estimate_from_sources([_make_source("test")], mode="quick")
        assert result.llm_calls == 1

    def test_standard_mode_call_count(self) -> None:
        estimator = CostEstimator()
        result = estimator.estimate_from_sources([_make_source("test")], mode="standard")
        assert result.llm_calls == 3

    def test_enterprise_mode_call_count(self) -> None:
        estimator = CostEstimator()
        result = estimator.estimate_from_sources([_make_source("test")], mode="enterprise")
        assert result.llm_calls == 4
