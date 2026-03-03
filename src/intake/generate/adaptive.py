"""Adaptive spec generation based on complexity classification.

Wraps the standard SpecBuilder to generate only the files appropriate
for the classified complexity mode:

- quick: context.md + tasks.md only
- standard: all 6 spec files
- enterprise: all 6 spec files + detailed risk assessment
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import structlog

from intake.generate.spec_builder import SPEC_FILES, SpecBuilder

if TYPE_CHECKING:
    from intake.analyze.complexity import ComplexityAssessment, ComplexityMode
    from intake.analyze.models import AnalysisResult
    from intake.config.schema import IntakeConfig
    from intake.ingest.base import ParsedContent

logger = structlog.get_logger()

# Files generated per complexity mode.
QUICK_FILES = frozenset({"context.md", "tasks.md"})

STANDARD_FILES = frozenset(SPEC_FILES.keys())

ENTERPRISE_FILES = frozenset(SPEC_FILES.keys())


@dataclass
class GenerationPlan:
    """Plan describing what to generate based on complexity.

    Attributes:
        mode: Complexity mode driving the plan.
        files_to_generate: Set of filenames to produce.
        design_depth: How detailed the design doc should be.
        task_granularity: How fine-grained tasks should be.
        include_risks: Whether to include risk assessment.
        include_sources: Whether to include source traceability.
    """

    mode: ComplexityMode
    files_to_generate: frozenset[str]
    design_depth: Literal["minimal", "moderate", "detailed"]
    task_granularity: Literal["coarse", "medium", "fine"]
    include_risks: bool
    include_sources: bool


def create_generation_plan(
    assessment: ComplexityAssessment,
    config: IntakeConfig,
) -> GenerationPlan:
    """Create a generation plan based on complexity assessment and config.

    The plan respects existing config overrides — if the user has explicitly
    set design_depth or task_granularity in their config, those values are
    preserved regardless of complexity mode.

    Args:
        assessment: Result of complexity classification.
        config: Current intake configuration.

    Returns:
        GenerationPlan describing what files to generate and how.
    """
    mode = assessment.mode

    if mode == "quick":
        plan = GenerationPlan(
            mode=mode,
            files_to_generate=QUICK_FILES,
            design_depth="minimal",
            task_granularity="coarse",
            include_risks=False,
            include_sources=False,
        )
    elif mode == "enterprise":
        plan = GenerationPlan(
            mode=mode,
            files_to_generate=ENTERPRISE_FILES,
            design_depth="detailed",
            task_granularity="fine",
            include_risks=True,
            include_sources=True,
        )
    else:
        plan = GenerationPlan(
            mode=mode,
            files_to_generate=STANDARD_FILES,
            design_depth=config.spec.design_depth,
            task_granularity=config.spec.task_granularity,
            include_risks=config.spec.risk_assessment,
            include_sources=config.spec.include_sources,
        )

    logger.info(
        "generation_plan_created",
        mode=mode,
        files=sorted(plan.files_to_generate),
        design_depth=plan.design_depth,
        task_granularity=plan.task_granularity,
    )

    return plan


class AdaptiveSpecBuilder:
    """Spec builder that adapts output based on complexity.

    Wraps a standard ``SpecBuilder`` and filters which files are
    generated according to a ``GenerationPlan``.

    Args:
        config: Full intake configuration.
        plan: Generation plan from complexity classification.
    """

    def __init__(self, config: IntakeConfig, plan: GenerationPlan) -> None:
        self._builder = SpecBuilder(config)
        self._plan = plan

    @property
    def plan(self) -> GenerationPlan:
        """The generation plan driving this builder."""
        return self._plan

    def generate(
        self,
        result: AnalysisResult,
        sources: list[ParsedContent],
        spec_name: str,
    ) -> list[str]:
        """Generate spec files filtered by the generation plan.

        Only produces files listed in ``plan.files_to_generate``.
        Always generates the lock file if configured.

        Args:
            result: Complete analysis result.
            sources: Original parsed sources.
            spec_name: Name for this spec (used as subdirectory).

        Returns:
            List of generated file paths.
        """
        output_dir = Path(self._builder.config.spec.output_dir) / spec_name
        output_dir.mkdir(parents=True, exist_ok=True)

        generated: list[str] = []
        context = self._builder._build_context(result, sources)

        for filename, template_name in SPEC_FILES.items():
            if filename not in self._plan.files_to_generate:
                logger.debug(
                    "spec_file_skipped",
                    file=filename,
                    mode=self._plan.mode,
                )
                continue

            output_path = output_dir / filename
            content = self._builder._render_template(template_name, context)
            output_path.write_text(content, encoding="utf-8")
            generated.append(str(output_path))

            logger.debug(
                "spec_file_generated",
                file=filename,
                path=str(output_path),
            )

        # Generate lock file if configured.
        if self._builder.config.spec.generate_lock:
            from intake.generate.lock import LOCK_FILENAME, create_lock

            source_paths = [s.source for s in sources if s.source != "-"]
            lock = create_lock(
                sources=source_paths,
                spec_dir=str(output_dir),
                model=result.model_used,
                total_cost=result.total_cost,
                requirement_count=result.requirement_count,
                task_count=result.task_count,
            )
            lock_path = str(output_dir / LOCK_FILENAME)
            lock.to_yaml(lock_path)
            generated.append(lock_path)

        logger.info(
            "adaptive_generation_complete",
            spec_name=spec_name,
            mode=self._plan.mode,
            files=len(generated),
            total_possible=len(SPEC_FILES),
        )

        return generated
