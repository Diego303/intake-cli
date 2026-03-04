"""Feedback analyzer — uses LLM to analyze verification failures.

Accepts a verification report (JSON), loads the associated spec,
and produces structured analysis with root causes and suggestions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from intake.export._helpers import parse_tasks, read_spec_file, summarize_content
from intake.feedback.prompts import FEEDBACK_ANALYSIS_PROMPT

if TYPE_CHECKING:
    from intake.config.schema import FeedbackConfig, IntakeConfig
    from intake.llm.adapter import LLMAdapter

logger = structlog.get_logger()


class FeedbackError(Exception):
    """Error during feedback analysis."""

    def __init__(self, reason: str, suggestion: str = "") -> None:
        self.reason = reason
        self.suggestion = suggestion
        msg = f"Feedback error: {reason}"
        if suggestion:
            msg += f"\n  Hint: {suggestion}"
        super().__init__(msg)


@dataclass
class SpecAmendment:
    """A proposed change to a spec file.

    Attributes:
        target_file: Spec file to modify (e.g., "requirements.md").
        section: Section or requirement ID to modify.
        action: One of "add", "modify", "remove".
        content: The proposed new content.
    """

    target_file: str
    section: str
    action: str
    content: str


@dataclass
class FailureAnalysis:
    """Analysis of a single verification failure.

    Attributes:
        check_name: Name of the failed check.
        root_cause: Why the check failed.
        suggestion: Actionable fix suggestion.
        category: Failure category.
        severity: How critical this failure is.
        affected_tasks: Task IDs related to this failure.
        spec_amendment: Optional spec change proposal.
    """

    check_name: str
    root_cause: str
    suggestion: str
    category: str = "implementation_gap"
    severity: str = "major"
    affected_tasks: list[str] = field(default_factory=list)
    spec_amendment: SpecAmendment | None = None


@dataclass
class FeedbackResult:
    """Complete feedback analysis result.

    Attributes:
        failures: Analysis for each failed check.
        summary: Overall assessment.
        estimated_effort: Estimated effort to fix (small/medium/large).
        total_cost: LLM cost for this analysis.
    """

    failures: list[FailureAnalysis]
    summary: str = ""
    estimated_effort: str = "medium"
    total_cost: float = 0.0

    @property
    def amendment_count(self) -> int:
        """Number of proposed spec amendments."""
        return sum(1 for f in self.failures if f.spec_amendment is not None)

    @property
    def critical_count(self) -> int:
        """Number of critical failures."""
        return sum(1 for f in self.failures if f.severity == "critical")


class FeedbackAnalyzer:
    """Analyze verification failures using LLM.

    Args:
        config: Full intake configuration.
        llm: LLM adapter for analysis calls.
    """

    def __init__(self, config: IntakeConfig, llm: LLMAdapter) -> None:
        self.config = config
        self.feedback_config: FeedbackConfig = config.feedback
        self.llm = llm

    async def analyze(
        self,
        verify_report: dict[str, object],
        spec_dir: str,
        project_dir: str = ".",
    ) -> FeedbackResult:
        """Analyze a verification report and produce feedback.

        Args:
            verify_report: Parsed JSON verification report with check results.
            spec_dir: Path to the spec directory.
            project_dir: Path to the project being verified.

        Returns:
            FeedbackResult with analysis and suggestions.

        Raises:
            FeedbackError: If analysis fails.
        """
        spec_path = Path(spec_dir)

        # Extract failed checks from report
        failed_checks = self._extract_failures(verify_report)
        if not failed_checks:
            return FeedbackResult(
                failures=[],
                summary="All checks passed. No feedback needed.",
                estimated_effort="small",
            )

        # Build context for LLM
        context = self._build_context(spec_path, failed_checks, project_dir)

        # Call LLM
        system_prompt = FEEDBACK_ANALYSIS_PROMPT.format(
            language=self.config.project.language,
        )

        try:
            response = await self.llm.completion(
                system_prompt=system_prompt,
                user_prompt=context,
                response_format="json",
                max_tokens=4000,
                phase="feedback",
            )
        except Exception as e:
            raise FeedbackError(
                reason=f"LLM analysis failed: {e}",
                suggestion="Check your API key and network connection.",
            ) from e

        if not isinstance(response, dict):
            raise FeedbackError(
                reason="LLM returned unexpected response format",
                suggestion="Try again or use a different model.",
            )

        # Parse LLM response
        result = self._parse_response(response)
        result.total_cost = self.llm.total_cost

        logger.info(
            "feedback_analysis_complete",
            failures=len(result.failures),
            amendments=result.amendment_count,
            effort=result.estimated_effort,
        )

        return result

    def _extract_failures(
        self,
        report: dict[str, object],
    ) -> list[dict[str, object]]:
        """Extract failed checks from a verification report.

        Args:
            report: Parsed verification report JSON.

        Returns:
            List of failed check dicts.
        """
        checks = report.get("checks", [])
        if not isinstance(checks, list):
            return []
        return [c for c in checks if isinstance(c, dict) and c.get("status") == "fail"]

    def _build_context(
        self,
        spec_path: Path,
        failed_checks: list[dict[str, object]],
        project_dir: str,
    ) -> str:
        """Build the user prompt with all relevant context.

        Args:
            spec_path: Path to the spec directory.
            failed_checks: List of failed check dicts.
            project_dir: Path to the project.

        Returns:
            Formatted context string for the LLM.
        """
        sections: list[str] = []

        # Failed checks
        sections.append("## Failed Checks\n")
        sections.append(json.dumps(failed_checks, indent=2))

        # Spec context
        requirements = read_spec_file(spec_path, "requirements.md")
        tasks_content = read_spec_file(spec_path, "tasks.md")
        design = read_spec_file(spec_path, "design.md")

        if requirements:
            sections.append("\n## Requirements (summary)\n")
            sections.append(summarize_content(requirements, max_lines=50))

        if tasks_content:
            sections.append("\n## Tasks\n")
            tasks = parse_tasks(tasks_content)
            for task in tasks:
                sections.append(f"- Task {task['id']}: {task['title']} ({task['status']})")

        if design:
            sections.append("\n## Design (summary)\n")
            sections.append(summarize_content(design, max_lines=30))

        sections.append(f"\n## Project Directory: {project_dir}")

        # Include code snippet hints if configured
        if self.feedback_config.include_code_snippets:
            sections.append(
                "\n## Instructions\n"
                "Include relevant code snippets in your suggestions "
                "to illustrate the recommended fixes."
            )

        return "\n".join(sections)

    def _parse_response(self, response: dict[str, object]) -> FeedbackResult:
        """Parse the LLM response into a FeedbackResult.

        Args:
            response: Parsed JSON dict from LLM.

        Returns:
            Structured FeedbackResult.
        """
        failures_data = response.get("failures", [])
        if not isinstance(failures_data, list):
            failures_data = []

        failures: list[FailureAnalysis] = []
        max_suggestions = self.feedback_config.max_suggestions

        for item in failures_data[:max_suggestions]:
            if not isinstance(item, dict):
                continue

            amendment = None
            amendment_data = item.get("spec_amendment")
            if isinstance(amendment_data, dict) and amendment_data.get("target_file"):
                amendment = SpecAmendment(
                    target_file=str(amendment_data.get("target_file", "")),
                    section=str(amendment_data.get("section", "")),
                    action=str(amendment_data.get("action", "modify")),
                    content=str(amendment_data.get("content", "")),
                )

            affected_tasks = item.get("affected_tasks", [])
            if not isinstance(affected_tasks, list):
                affected_tasks = []

            failures.append(
                FailureAnalysis(
                    check_name=str(item.get("check_name", "unknown")),
                    root_cause=str(item.get("root_cause", "")),
                    suggestion=str(item.get("suggestion", "")),
                    category=str(item.get("category", "implementation_gap")),
                    severity=str(item.get("severity", "major")),
                    affected_tasks=[str(t) for t in affected_tasks],
                    spec_amendment=amendment,
                )
            )

        return FeedbackResult(
            failures=failures,
            summary=str(response.get("summary", "")),
            estimated_effort=str(response.get("estimated_effort", "medium")),
        )
