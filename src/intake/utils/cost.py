"""LLM cost tracking and reporting."""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger()


@dataclass
class CostEntry:
    """A single LLM call cost record."""

    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    phase: str = ""


@dataclass
class CostTracker:
    """Tracks LLM costs across multiple calls.

    Accumulates cost entries and provides summary reporting.
    """

    entries: list[CostEntry] = field(default_factory=list)

    @property
    def total_cost(self) -> float:
        """Total cost across all entries."""
        return sum(e.cost for e in self.entries)

    @property
    def total_input_tokens(self) -> int:
        """Total input tokens across all entries."""
        return sum(e.input_tokens for e in self.entries)

    @property
    def total_output_tokens(self) -> int:
        """Total output tokens across all entries."""
        return sum(e.output_tokens for e in self.entries)

    @property
    def call_count(self) -> int:
        """Number of LLM calls tracked."""
        return len(self.entries)

    def add(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        phase: str = "",
    ) -> None:
        """Record a new LLM call cost.

        Args:
            model: Model name used.
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.
            cost: Dollar cost of the call.
            phase: Pipeline phase (e.g. "extraction", "design", "risk").
        """
        entry = CostEntry(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            phase=phase,
        )
        self.entries.append(entry)
        logger.debug(
            "cost_recorded",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=f"${cost:.4f}",
            phase=phase,
        )

    def summary(self) -> dict[str, float | int]:
        """Generate a cost summary.

        Returns:
            Dictionary with total cost, token counts, and call count.
        """
        return {
            "total_cost": self.total_cost,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "call_count": self.call_count,
        }

    def cost_by_phase(self) -> dict[str, float]:
        """Break down costs by pipeline phase.

        Returns:
            Dictionary mapping phase names to their total cost.
        """
        by_phase: dict[str, float] = {}
        for entry in self.entries:
            phase = entry.phase or "unknown"
            by_phase[phase] = by_phase.get(phase, 0.0) + entry.cost
        return by_phase
