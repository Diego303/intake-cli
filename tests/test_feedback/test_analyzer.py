"""Tests for the feedback analyzer."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from intake.config.schema import FeedbackConfig, IntakeConfig
from intake.feedback.analyzer import (
    FailureAnalysis,
    FeedbackAnalyzer,
    FeedbackError,
    FeedbackResult,
    SpecAmendment,
)


@pytest.fixture
def config() -> IntakeConfig:
    """Create a test configuration."""
    return IntakeConfig()


@pytest.fixture
def spec_dir(tmp_path: Path) -> Path:
    """Create a sample spec directory."""
    spec = tmp_path / "test-spec"
    spec.mkdir()
    (spec / "requirements.md").write_text(
        "# Requirements\n\n### FR-001: User login\n\nUser can log in.\n"
    )
    (spec / "tasks.md").write_text(
        "# Tasks\n\n### Task 1: Setup\n\nSetup project.\n\n**Status:** pending\n"
    )
    (spec / "design.md").write_text("# Design\n\nMonolith.\n")
    (spec / "context.md").write_text("# Context\n\nStack: Python\n")
    return spec


@pytest.fixture
def failed_report() -> dict[str, object]:
    """Create a sample failed verification report."""
    return {
        "spec_name": "test-spec",
        "total": 3,
        "passed": 1,
        "failed": 2,
        "checks": [
            {"id": "tests", "name": "Run tests", "type": "command", "status": "pass"},
            {
                "id": "types",
                "name": "Type check",
                "type": "command",
                "status": "fail",
                "error": "5 errors",
            },
            {
                "id": "lint",
                "name": "Lint",
                "type": "command",
                "status": "fail",
                "error": "3 warnings",
            },
        ],
    }


@pytest.fixture
def mock_llm() -> MagicMock:
    """Create a mock LLM adapter."""
    llm = MagicMock()
    llm.total_cost = 0.001
    llm.completion = AsyncMock(
        return_value={
            "failures": [
                {
                    "check_name": "Type check",
                    "root_cause": "Missing type annotations in module X",
                    "suggestion": "Add type hints to functions in src/module.py",
                    "category": "implementation_gap",
                    "severity": "major",
                    "affected_tasks": ["1"],
                    "spec_amendment": None,
                },
                {
                    "check_name": "Lint",
                    "root_cause": "Unused imports in 3 files",
                    "suggestion": "Remove unused imports",
                    "category": "implementation_gap",
                    "severity": "minor",
                    "affected_tasks": [],
                    "spec_amendment": {
                        "target_file": "requirements.md",
                        "section": "FR-001",
                        "action": "modify",
                        "content": "Updated criteria with lint requirement",
                    },
                },
            ],
            "summary": "Two minor issues found, easy to fix.",
            "estimated_effort": "small",
        }
    )
    return llm


class TestFeedbackResult:
    def test_amendment_count(self) -> None:
        """amendment_count returns number of failures with amendments."""
        result = FeedbackResult(
            failures=[
                FailureAnalysis(
                    check_name="a",
                    root_cause="x",
                    suggestion="y",
                    spec_amendment=SpecAmendment("r.md", "FR-1", "modify", "new"),
                ),
                FailureAnalysis(check_name="b", root_cause="x", suggestion="y"),
            ],
        )
        assert result.amendment_count == 1

    def test_critical_count(self) -> None:
        """critical_count returns number of critical failures."""
        result = FeedbackResult(
            failures=[
                FailureAnalysis(
                    check_name="a",
                    root_cause="x",
                    suggestion="y",
                    severity="critical",
                ),
                FailureAnalysis(
                    check_name="b",
                    root_cause="x",
                    suggestion="y",
                    severity="major",
                ),
            ],
        )
        assert result.critical_count == 1

    def test_empty_result(self) -> None:
        """Empty result has zero counts."""
        result = FeedbackResult(failures=[])
        assert result.amendment_count == 0
        assert result.critical_count == 0


class TestFeedbackAnalyzer:
    @pytest.mark.asyncio
    async def test_analyze_produces_result(
        self,
        config: IntakeConfig,
        mock_llm: MagicMock,
        spec_dir: Path,
        failed_report: dict[str, object],
    ) -> None:
        """Analyzer produces a FeedbackResult from a failed report."""
        analyzer = FeedbackAnalyzer(config=config, llm=mock_llm)
        result = await analyzer.analyze(failed_report, str(spec_dir))

        assert isinstance(result, FeedbackResult)
        assert len(result.failures) == 2
        assert result.summary == "Two minor issues found, easy to fix."
        assert result.estimated_effort == "small"

    @pytest.mark.asyncio
    async def test_analyze_passes_with_no_failures(
        self,
        config: IntakeConfig,
        mock_llm: MagicMock,
        spec_dir: Path,
    ) -> None:
        """Analyzer returns empty result when all checks pass."""
        report: dict[str, object] = {
            "checks": [
                {"id": "tests", "name": "Run tests", "status": "pass"},
            ],
        }
        analyzer = FeedbackAnalyzer(config=config, llm=mock_llm)
        result = await analyzer.analyze(report, str(spec_dir))

        assert len(result.failures) == 0
        assert "passed" in result.summary.lower()
        # LLM should not be called when there are no failures
        mock_llm.completion.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_analyze_parses_amendments(
        self,
        config: IntakeConfig,
        mock_llm: MagicMock,
        spec_dir: Path,
        failed_report: dict[str, object],
    ) -> None:
        """Analyzer correctly parses spec amendments from LLM response."""
        analyzer = FeedbackAnalyzer(config=config, llm=mock_llm)
        result = await analyzer.analyze(failed_report, str(spec_dir))

        amendments = [f for f in result.failures if f.spec_amendment is not None]
        assert len(amendments) == 1
        assert amendments[0].spec_amendment.target_file == "requirements.md"
        assert amendments[0].spec_amendment.action == "modify"

    @pytest.mark.asyncio
    async def test_analyze_respects_max_suggestions(
        self,
        spec_dir: Path,
        failed_report: dict[str, object],
    ) -> None:
        """Analyzer respects max_suggestions config."""
        config = IntakeConfig(
            feedback=FeedbackConfig(max_suggestions=1),
        )
        llm = MagicMock()
        llm.total_cost = 0.0
        llm.completion = AsyncMock(
            return_value={
                "failures": [
                    {"check_name": "a", "root_cause": "x", "suggestion": "y"},
                    {"check_name": "b", "root_cause": "x", "suggestion": "y"},
                    {"check_name": "c", "root_cause": "x", "suggestion": "y"},
                ],
                "summary": "Multiple issues",
                "estimated_effort": "medium",
            }
        )
        analyzer = FeedbackAnalyzer(config=config, llm=llm)
        result = await analyzer.analyze(failed_report, str(spec_dir))

        assert len(result.failures) <= 1

    @pytest.mark.asyncio
    async def test_analyze_handles_llm_error(
        self,
        config: IntakeConfig,
        spec_dir: Path,
        failed_report: dict[str, object],
    ) -> None:
        """Analyzer raises FeedbackError on LLM failure."""
        llm = MagicMock()
        llm.completion = AsyncMock(side_effect=Exception("API error"))
        analyzer = FeedbackAnalyzer(config=config, llm=llm)

        with pytest.raises(FeedbackError, match="LLM analysis failed"):
            await analyzer.analyze(failed_report, str(spec_dir))


class TestExtractFailures:
    def test_extracts_failed_checks(self, config: IntakeConfig) -> None:
        """Correctly extracts only failed checks."""
        llm = MagicMock()
        analyzer = FeedbackAnalyzer(config=config, llm=llm)
        report: dict[str, object] = {
            "checks": [
                {"name": "a", "status": "pass"},
                {"name": "b", "status": "fail"},
                {"name": "c", "status": "fail"},
            ],
        }
        failures = analyzer._extract_failures(report)
        assert len(failures) == 2

    def test_handles_empty_report(self, config: IntakeConfig) -> None:
        """Returns empty list for report with no checks."""
        llm = MagicMock()
        analyzer = FeedbackAnalyzer(config=config, llm=llm)
        assert analyzer._extract_failures({}) == []
        assert analyzer._extract_failures({"checks": "invalid"}) == []
