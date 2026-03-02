"""Analyzer orchestrator — coordinates the LLM analysis pipeline.

Flow:
1. Combine text from all parsed sources
2. Phase A — Extraction: LLM extracts structured requirements
3. Deduplication: detect and remove repeated requirements across sources
4. Validation: filter incomplete conflicts and questions
5. Risk assessment: evaluate risk per requirement (optional)
6. Design: architecture, tasks, and acceptance checks
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import structlog

from intake.analyze.conflicts import validate_conflicts
from intake.analyze.dedup import deduplicate
from intake.analyze.design import parse_design
from intake.analyze.extraction import parse_extraction
from intake.analyze.models import DesignResult
from intake.analyze.prompts import DESIGN_PROMPT, EXTRACTION_PROMPT, RISK_ASSESSMENT_PROMPT
from intake.analyze.questions import validate_questions
from intake.analyze.risks import parse_risks

if TYPE_CHECKING:
    from intake.analyze.models import AnalysisResult, RiskItem
    from intake.config.schema import IntakeConfig
    from intake.ingest.base import ParsedContent
    from intake.llm import LLMAdapter

logger = structlog.get_logger()


class AnalyzeError(Exception):
    """Base exception for analysis errors."""

    def __init__(self, reason: str, suggestion: str = "") -> None:
        self.reason = reason
        self.suggestion = suggestion
        msg = f"Analysis failed: {reason}"
        if suggestion:
            msg += f"\n  Hint: {suggestion}"
        super().__init__(msg)


class Analyzer:
    """Orchestrates content analysis with LLM.

    Coordinates extraction, deduplication, conflict validation,
    risk assessment, and design phases into a single AnalysisResult.

    Args:
        config: Full intake configuration.
        llm: LLM adapter for making completion calls.
    """

    def __init__(self, config: IntakeConfig, llm: LLMAdapter) -> None:
        self.config = config
        self.llm = llm

    async def analyze(self, sources: list[ParsedContent]) -> AnalysisResult:
        """Analyze multiple parsed sources and produce a structured result.

        Args:
            sources: List of parsed content from the ingest phase.

        Returns:
            Complete AnalysisResult with requirements, design, and metadata.

        Raises:
            AnalyzeError: If analysis fails.
        """
        if not sources:
            raise AnalyzeError(
                reason="No sources provided for analysis.",
                suggestion="Pass at least one source file with -s.",
            )

        combined_text = self._combine_sources(sources)
        total_words = sum(s.word_count for s in sources)

        logger.info(
            "analysis_starting",
            sources=len(sources),
            total_words=total_words,
        )

        # Phase A: Requirement extraction
        extraction_raw = await self.llm.completion(
            system_prompt=EXTRACTION_PROMPT.format(
                n_sources=len(sources),
                language=self.config.project.language,
                requirements_format=self.config.spec.requirements_format,
            ),
            user_prompt=combined_text,
            response_format="json",
            phase="extraction",
        )

        if not isinstance(extraction_raw, dict):
            msg = "LLM extraction did not return JSON"
            raise AnalyzeError(msg, suggestion="Check your LLM model configuration.")
        result = parse_extraction(extraction_raw)

        # Deduplication
        result.duplicates_removed = deduplicate(result)

        # Validate conflicts and questions
        result.conflicts = validate_conflicts(result.conflicts)
        result.open_questions = validate_questions(result.open_questions)

        # Risk assessment (conditional)
        if self.config.spec.risk_assessment:
            result.risks = await self._assess_risks(result)

        # Design phase
        result.design = await self._design(result)

        # Metadata
        result.total_cost = self.llm.total_cost
        result.model_used = self.config.llm.model

        logger.info(
            "analysis_complete",
            functional=len(result.functional_requirements),
            non_functional=len(result.non_functional_requirements),
            conflicts=len(result.conflicts),
            questions=len(result.open_questions),
            risks=len(result.risks),
            tasks=len(result.design.tasks),
            duplicates_removed=result.duplicates_removed,
            cost=f"${result.total_cost:.4f}",
        )

        return result

    def _combine_sources(self, sources: list[ParsedContent]) -> str:
        """Combine multiple sources into a single text for the LLM.

        Each source is prefixed with a header identifying its index,
        file path, and format.
        """
        parts: list[str] = []
        for i, source in enumerate(sources, 1):
            header = (
                f"=== SOURCE {i}: {source.source} "
                f"(format: {source.format}) ==="
            )
            parts.append(f"{header}\n\n{source.text}")
        return "\n\n---\n\n".join(parts)

    async def _assess_risks(self, result: AnalysisResult) -> list[RiskItem]:
        """Ask LLM to assess risks based on extracted requirements."""
        requirements_data = [
            {
                "id": r.id,
                "title": r.title,
                "type": r.type,
                "priority": r.priority,
            }
            for r in result.all_requirements
        ]

        conflicts_data = [
            {
                "id": c.id,
                "description": c.description,
                "severity": c.severity,
            }
            for c in result.conflicts
        ]

        risk_raw = await self.llm.completion(
            system_prompt=RISK_ASSESSMENT_PROMPT.format(
                language=self.config.project.language,
                requirements_json=json.dumps(requirements_data, indent=2),
                conflicts_json=json.dumps(conflicts_data, indent=2),
            ),
            user_prompt="Assess risks for the requirements above.",
            response_format="json",
            phase="risk_assessment",
        )

        if not isinstance(risk_raw, dict):
            return []
        return parse_risks(risk_raw)

    async def _design(self, result: AnalysisResult) -> DesignResult:
        """Ask LLM to produce technical design, tasks, and checks."""
        requirements_data = [
            {
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "type": r.type,
                "priority": r.priority,
                "acceptance_criteria": r.acceptance_criteria,
            }
            for r in result.all_requirements
        ]

        project_stack = self.config.project.stack
        stack = ", ".join(project_stack) if project_stack else "not specified"

        design_raw = await self.llm.completion(
            system_prompt=DESIGN_PROMPT.format(
                language=self.config.project.language,
                design_depth=self.config.spec.design_depth,
                task_granularity=self.config.spec.task_granularity,
                stack=stack,
                file_tree="(not available)",
                requirements_json=json.dumps(requirements_data, indent=2),
            ),
            user_prompt="Produce the technical design for these requirements.",
            response_format="json",
            phase="design",
        )

        if not isinstance(design_raw, dict):
            return DesignResult()
        return parse_design(design_raw)
