"""Tests for the suggestion formatter."""

from __future__ import annotations

from intake.feedback.analyzer import (
    FailureAnalysis,
    FeedbackResult,
    SpecAmendment,
)
from intake.feedback.suggestions import SuggestionFormatter


def _make_result(with_amendment: bool = False) -> FeedbackResult:
    """Create a sample FeedbackResult."""
    amendment = None
    if with_amendment:
        amendment = SpecAmendment(
            target_file="requirements.md",
            section="FR-001",
            action="modify",
            content="Updated acceptance criteria",
        )

    return FeedbackResult(
        failures=[
            FailureAnalysis(
                check_name="Type check",
                root_cause="Missing type annotations",
                suggestion="Add type hints",
                category="implementation_gap",
                severity="major",
                affected_tasks=["1"],
                spec_amendment=amendment,
            ),
        ],
        summary="One issue found.",
        estimated_effort="small",
    )


class TestSuggestionFormatter:
    def test_format_generic(self) -> None:
        """Generic format produces Markdown."""
        formatter = SuggestionFormatter()
        output = formatter.format(_make_result())

        assert "Type check" in output
        assert "Missing type annotations" in output
        assert "Add type hints" in output

    def test_format_claude_code(self) -> None:
        """Claude Code format produces Markdown with code blocks."""
        formatter = SuggestionFormatter()
        output = formatter.format(_make_result(with_amendment=True), agent_format="claude-code")

        assert "Type check" in output
        assert "```" in output

    def test_format_cursor(self) -> None:
        """Cursor format produces Markdown with blockquotes."""
        formatter = SuggestionFormatter()
        output = formatter.format(_make_result(with_amendment=True), agent_format="cursor")

        assert "Type check" in output
        assert ">" in output

    def test_format_unknown_falls_back_to_generic(self) -> None:
        """Unknown format falls back to generic."""
        formatter = SuggestionFormatter()
        output = formatter.format(_make_result(), agent_format="unknown")
        assert "Type check" in output

    def test_format_empty_result(self) -> None:
        """Empty result produces a success message."""
        formatter = SuggestionFormatter()
        output = formatter.format(FeedbackResult(failures=[]))
        assert "passed" in output.lower() or "no feedback" in output.lower()


class TestTerminalFormat:
    def test_terminal_with_failures(self) -> None:
        """Terminal format includes Rich markup."""
        formatter = SuggestionFormatter()
        output = formatter.format_terminal(_make_result())

        assert "Type check" in output
        assert "MAJOR" in output
        assert "Missing type annotations" in output

    def test_terminal_critical_severity(self) -> None:
        """Terminal format highlights critical failures."""
        result = FeedbackResult(
            failures=[
                FailureAnalysis(
                    check_name="Security",
                    root_cause="SQL injection",
                    suggestion="Use parameterized queries",
                    severity="critical",
                ),
            ],
        )
        formatter = SuggestionFormatter()
        output = formatter.format_terminal(result)
        assert "CRITICAL" in output

    def test_terminal_with_amendments(self) -> None:
        """Terminal format shows amendment info."""
        formatter = SuggestionFormatter()
        output = formatter.format_terminal(_make_result(with_amendment=True))
        assert "amendment" in output.lower()

    def test_terminal_no_failures(self) -> None:
        """Terminal format for no failures."""
        formatter = SuggestionFormatter()
        output = formatter.format_terminal(FeedbackResult(failures=[]))
        assert "passed" in output.lower()
