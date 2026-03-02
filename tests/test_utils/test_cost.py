"""Tests for LLM cost tracking."""

from __future__ import annotations

from intake.utils.cost import CostTracker


class TestCostTracker:
    def test_empty_tracker(self) -> None:
        tracker = CostTracker()
        assert tracker.total_cost == 0.0
        assert tracker.total_input_tokens == 0
        assert tracker.total_output_tokens == 0
        assert tracker.call_count == 0

    def test_add_entry(self) -> None:
        tracker = CostTracker()
        tracker.add(
            model="claude-sonnet-4",
            input_tokens=1000,
            output_tokens=500,
            cost=0.015,
            phase="extraction",
        )
        assert tracker.call_count == 1
        assert tracker.total_cost == 0.015
        assert tracker.total_input_tokens == 1000
        assert tracker.total_output_tokens == 500

    def test_multiple_entries(self) -> None:
        tracker = CostTracker()
        tracker.add("model-a", 100, 50, 0.01, "extraction")
        tracker.add("model-a", 200, 100, 0.02, "design")
        assert tracker.call_count == 2
        assert tracker.total_cost == pytest.approx(0.03)
        assert tracker.total_input_tokens == 300

    def test_summary(self) -> None:
        tracker = CostTracker()
        tracker.add("model-a", 100, 50, 0.01)
        summary = tracker.summary()
        assert summary["total_cost"] == 0.01
        assert summary["call_count"] == 1

    def test_cost_by_phase(self) -> None:
        tracker = CostTracker()
        tracker.add("m", 100, 50, 0.01, "extraction")
        tracker.add("m", 100, 50, 0.02, "extraction")
        tracker.add("m", 100, 50, 0.05, "design")
        by_phase = tracker.cost_by_phase()
        assert by_phase["extraction"] == pytest.approx(0.03)
        assert by_phase["design"] == pytest.approx(0.05)


import pytest  # noqa: E402
