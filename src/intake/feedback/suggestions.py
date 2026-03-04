"""Format feedback suggestions for different output targets.

Supports generic Markdown output, Claude Code format, and Cursor format.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from jinja2 import Environment, PackageLoader

if TYPE_CHECKING:
    from intake.feedback.analyzer import FeedbackResult

logger = structlog.get_logger()

AGENT_FORMATS = ("generic", "claude-code", "cursor")


class SuggestionFormatter:
    """Format feedback results for human or agent consumption.

    Supports multiple output formats for different AI coding agents.
    """

    def __init__(self) -> None:
        self._env = Environment(
            loader=PackageLoader("intake", "templates"),
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def format(
        self,
        result: FeedbackResult,
        agent_format: str = "generic",
    ) -> str:
        """Format a feedback result as Markdown.

        Args:
            result: FeedbackResult from the analyzer.
            agent_format: Output format (generic, claude-code, cursor).

        Returns:
            Formatted Markdown string.
        """
        if agent_format not in AGENT_FORMATS:
            agent_format = "generic"

        template = self._env.get_template("feedback.md.j2")
        return template.render(
            result=result,
            agent_format=agent_format,
        )

    def format_terminal(self, result: FeedbackResult) -> str:
        """Format feedback for terminal display with Rich markup.

        Args:
            result: FeedbackResult from the analyzer.

        Returns:
            String with Rich markup for console display.
        """
        lines: list[str] = []

        if not result.failures:
            lines.append("[green]All checks passed. No feedback needed.[/green]")
            return "\n".join(lines)

        lines.append(f"[bold]Feedback Analysis[/bold] ({len(result.failures)} failures)")
        lines.append("")

        severity_styles = {
            "critical": "[red bold]CRITICAL[/red bold]",
            "major": "[yellow]MAJOR[/yellow]",
            "minor": "[dim]minor[/dim]",
        }

        for i, failure in enumerate(result.failures, 1):
            severity = severity_styles.get(failure.severity, failure.severity)
            lines.append(f"  {i}. {severity} [bold]{failure.check_name}[/bold]")
            lines.append(f"     Cause: {failure.root_cause}")
            lines.append(f"     Fix: {failure.suggestion}")
            if failure.affected_tasks:
                tasks_str = ", ".join(f"Task {t}" for t in failure.affected_tasks)
                lines.append(f"     Tasks: {tasks_str}")
            if failure.spec_amendment:
                lines.append(
                    f"     [cyan]Spec amendment:[/cyan] "
                    f"{failure.spec_amendment.action} in "
                    f"{failure.spec_amendment.target_file}"
                )
            lines.append("")

        if result.summary:
            lines.append(f"[bold]Summary:[/bold] {result.summary}")

        lines.append(f"Estimated effort: {result.estimated_effort}")

        if result.amendment_count > 0:
            lines.append(
                f"\n[cyan]{result.amendment_count} spec amendment(s) suggested.[/cyan] "
                f"Use --apply to auto-apply."
            )

        return "\n".join(lines)
