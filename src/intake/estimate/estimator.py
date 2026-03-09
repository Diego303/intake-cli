"""LLM cost estimation for intake spec generation.

Estimates token usage and dollar cost based on input word count,
complexity mode, and model pricing — without making any LLM calls.

The pricing table is a hardcoded constant updated per release.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from intake.analyze.complexity import ComplexityMode, classify_complexity
from intake.config.schema import EstimateConfig, LLMConfig

if TYPE_CHECKING:
    from intake.ingest.base import ParsedContent

logger = structlog.get_logger()


# Approximate pricing per 1M tokens (input/output) for common models.
# Updated manually per release — LLM pricing changes frequently.
MODEL_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4": {"input": 3.0, "output": 15.0},
    "claude-haiku-4": {"input": 0.80, "output": 4.0},
    "claude-opus-4": {"input": 15.0, "output": 75.0},
    "gpt-4o": {"input": 2.50, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "deepseek-chat": {"input": 0.14, "output": 0.28},
}

# Fallback pricing when model is not in the table.
DEFAULT_PRICING: dict[str, float] = {"input": 3.0, "output": 15.0}

# Output-to-input token ratio by mode.
_OUTPUT_RATIO: dict[str, float] = {
    "quick": 0.4,
    "standard": 0.5,
    "enterprise": 0.6,
}


@dataclass
class CostEstimate:
    """Estimated cost for processing sources into a spec.

    Attributes:
        mode: Generation mode used for estimation.
        mode_auto_detected: Whether mode was auto-detected.
        total_input_words: Combined input word count.
        total_input_tokens: Estimated input tokens.
        total_output_tokens: Estimated output tokens.
        llm_calls: Estimated number of LLM calls.
        model: LLM model name.
        estimated_cost_usd: Total estimated cost in USD.
        cost_breakdown: Per-component cost details.
        warnings: Advisory messages (budget exceeded, unknown model, etc.).
    """

    mode: ComplexityMode
    mode_auto_detected: bool
    total_input_words: int
    total_input_tokens: int
    total_output_tokens: int
    llm_calls: int
    model: str
    estimated_cost_usd: float
    cost_breakdown: list[dict[str, str | float]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def formatted_cost(self) -> str:
        """Format cost for display."""
        if self.estimated_cost_usd < 0.01:
            return f"${self.estimated_cost_usd:.4f}"
        return f"${self.estimated_cost_usd:.2f}"


class CostEstimator:
    """Estimate LLM token usage and cost before running analysis.

    Uses heuristics based on:
    - Input word count -> estimated input tokens
    - Complexity mode -> number of LLM calls
    - Model pricing table -> estimated dollar cost

    This is an ESTIMATE. Actual cost depends on LLM response length,
    retry count, and prompt variations.
    """

    def __init__(
        self,
        config: EstimateConfig | None = None,
        llm_config: LLMConfig | None = None,
    ) -> None:
        self.config = config or EstimateConfig()
        self.llm_config = llm_config or LLMConfig()

    def estimate_from_sources(
        self,
        sources: list[ParsedContent],
        mode: ComplexityMode | None = None,
    ) -> CostEstimate:
        """Estimate cost from already-parsed sources.

        Args:
            sources: List of parsed content from ingestion.
            mode: Explicit mode, or None for auto-detection.

        Returns:
            CostEstimate with projected costs and warnings.
        """
        total_words = sum(s.word_count for s in sources)

        if mode is None:
            assessment = classify_complexity(sources)
            detected_mode = assessment.mode
            auto_detected = True
        else:
            detected_mode = mode
            auto_detected = False

        return self._calculate(
            total_words=total_words,
            mode=detected_mode,
            auto_detected=auto_detected,
        )

    def estimate_from_files(
        self,
        file_paths: list[str],
        mode: ComplexityMode | None = None,
    ) -> CostEstimate:
        """Quick estimate from file paths without full parsing.

        Args:
            file_paths: List of source file paths.
            mode: Explicit mode, or None for auto-detection.

        Returns:
            CostEstimate with projected costs and warnings.

        Raises:
            FileNotFoundError: If any source file does not exist.
        """
        missing = [fp for fp in file_paths if not Path(fp).exists()]
        if missing:
            raise FileNotFoundError(f"Source file(s) not found: {', '.join(missing)}")

        total_words = 0
        for fp in file_paths:
            path = Path(fp)
            if path.is_file():
                try:
                    content = path.read_text(errors="ignore")
                    total_words += len(content.split())
                except OSError:
                    logger.warning("file_read_failed", path=fp)

        if mode is None:
            # Simple heuristic without full parsing
            detected_mode: ComplexityMode
            if len(file_paths) == 1 and total_words < 500:
                detected_mode = "quick"
            elif len(file_paths) >= 4 or total_words > 5000:
                detected_mode = "enterprise"
            else:
                detected_mode = "standard"
            auto_detected = True
        else:
            detected_mode = mode
            auto_detected = False

        return self._calculate(
            total_words=total_words,
            mode=detected_mode,
            auto_detected=auto_detected,
        )

    def _calculate(
        self,
        total_words: int,
        mode: ComplexityMode,
        auto_detected: bool,
    ) -> CostEstimate:
        """Calculate estimated cost.

        Args:
            total_words: Combined input word count.
            mode: Generation mode.
            auto_detected: Whether mode was auto-detected.

        Returns:
            CostEstimate with full breakdown.
        """
        model = self.llm_config.model
        pricing = MODEL_PRICING.get(model, DEFAULT_PRICING)

        tokens_per_word = self.config.tokens_per_word
        overhead = self.config.prompt_overhead_tokens
        n_calls = self.config.calls_per_mode.get(mode, 3)

        # Input tokens: content + system prompt overhead per call
        content_tokens = int(total_words * tokens_per_word)
        total_input = (content_tokens + overhead) * n_calls

        # Output tokens: percentage of input based on mode
        output_ratio = _OUTPUT_RATIO.get(mode, 0.5)
        total_output = int(total_input * output_ratio)

        # Cost calculation
        input_cost = (total_input / 1_000_000) * pricing["input"]
        output_cost = (total_output / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost

        # Warnings
        warnings: list[str] = []
        if total_cost > self.llm_config.max_cost_per_spec:
            warnings.append(
                f"Estimated cost (${total_cost:.2f}) exceeds budget limit "
                f"(${self.llm_config.max_cost_per_spec:.2f}). "
                f"Consider using --mode quick or a cheaper model."
            )

        if model not in MODEL_PRICING:
            warnings.append(
                f"Model '{model}' not in pricing table. "
                f"Using default pricing ($3.00/$15.00 per 1M tokens). "
                f"Actual cost may differ."
            )

        logger.debug(
            "cost_estimated",
            model=model,
            mode=mode,
            total_words=total_words,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            estimated_cost_usd=total_cost,
        )

        return CostEstimate(
            mode=mode,
            mode_auto_detected=auto_detected,
            total_input_words=total_words,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            llm_calls=n_calls,
            model=model,
            estimated_cost_usd=total_cost,
            cost_breakdown=[
                {"label": "Input tokens", "tokens": float(total_input), "cost_usd": input_cost},
                {"label": "Output tokens", "tokens": float(total_output), "cost_usd": output_cost},
            ],
            warnings=warnings,
        )
