"""Verification report formatters.

Supports three output formats:
- terminal: Rich table with colors (default)
- json: Machine-readable JSON
- junit: JUnit XML for CI integration
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Protocol, runtime_checkable
from xml.etree.ElementTree import Element, SubElement, tostring

import structlog
from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from intake.verify.engine import VerificationReport

logger = structlog.get_logger()


@runtime_checkable
class Reporter(Protocol):
    """Protocol for verification report formatters."""

    def render(self, report: VerificationReport) -> str:
        """Render a verification report to string.

        Args:
            report: The verification report to render.

        Returns:
            Formatted string output.
        """
        ...


class TerminalReporter:
    """Rich terminal output for verification results."""

    def render(self, report: VerificationReport) -> str:
        """Render report as a Rich table to the console.

        Also returns a plain text summary.

        Args:
            report: The verification report to render.

        Returns:
            Plain text summary string.
        """
        console = Console()

        table = Table(
            title=f"Verification: {report.spec_name}",
            show_lines=True,
        )
        table.add_column("ID", style="bold")
        table.add_column("Check", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Required", justify="center")
        table.add_column("Duration", justify="right")
        table.add_column("Details", max_width=60)

        for result in report.results:
            status = "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]"
            required = "[yellow]yes[/yellow]" if result.required else "no"
            duration = f"{result.duration_ms}ms"
            details = result.error if result.error else result.output
            # Truncate long details for table display
            if len(details) > 80:
                details = details[:77] + "..."

            table.add_row(
                result.id, result.name, status, required, duration, details,
            )

        console.print(table)

        # Summary line
        if report.all_required_passed:
            summary = (
                f"All {report.passed} check(s) passed"
                f" ({report.total_checks} total, {report.skipped} skipped)."
            )
            console.print(f"\n[green]{summary}[/green]")
        else:
            summary = (
                f"{report.failed} check(s) failed, {report.passed} passed"
                f" ({report.total_checks} total, {report.skipped} skipped)."
            )
            console.print(f"\n[red]{summary}[/red]")

        return summary


class JsonReporter:
    """JSON output for machine consumption."""

    def render(self, report: VerificationReport) -> str:
        """Render report as JSON.

        Args:
            report: The verification report to render.

        Returns:
            JSON string.
        """
        data = {
            "spec_name": report.spec_name,
            "total_checks": report.total_checks,
            "passed": report.passed,
            "failed": report.failed,
            "skipped": report.skipped,
            "all_required_passed": report.all_required_passed,
            "exit_code": report.exit_code,
            "results": [
                {
                    "id": r.id,
                    "name": r.name,
                    "passed": r.passed,
                    "required": r.required,
                    "output": r.output,
                    "error": r.error,
                    "duration_ms": r.duration_ms,
                }
                for r in report.results
            ],
        }
        return json.dumps(data, indent=2)


class JunitReporter:
    """JUnit XML output for CI integration."""

    def render(self, report: VerificationReport) -> str:
        """Render report as JUnit XML.

        Args:
            report: The verification report to render.

        Returns:
            JUnit XML string.
        """
        testsuites = Element("testsuites")
        testsuite = SubElement(
            testsuites,
            "testsuite",
            name=report.spec_name,
            tests=str(report.total_checks),
            failures=str(report.failed),
            skipped=str(report.skipped),
        )

        for result in report.results:
            testcase = SubElement(
                testsuite,
                "testcase",
                name=result.name,
                classname=f"intake.verify.{report.spec_name}",
                time=str(result.duration_ms / 1000),
            )

            if not result.passed:
                failure = SubElement(
                    testcase,
                    "failure",
                    message=result.error or result.output,
                    type="AssertionError",
                )
                failure.text = result.error or result.output

            if result.output and result.passed:
                system_out = SubElement(testcase, "system-out")
                system_out.text = result.output

        return tostring(testsuites, encoding="unicode", xml_declaration=True)


def get_reporter(format_name: str) -> Reporter:
    """Get a reporter instance by format name.

    Args:
        format_name: One of "terminal", "json", "junit".

    Returns:
        Reporter instance.

    Raises:
        ValueError: If the format is not recognized.
    """
    reporters: dict[str, Reporter] = {
        "terminal": TerminalReporter(),
        "json": JsonReporter(),
        "junit": JunitReporter(),
    }
    reporter = reporters.get(format_name)
    if reporter is None:
        raise ValueError(
            f"Unknown report format: {format_name}. "
            f"Valid formats: {', '.join(reporters.keys())}"
        )
    return reporter
