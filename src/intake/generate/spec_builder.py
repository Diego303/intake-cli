"""Spec generation orchestrator.

Renders AnalysisResult into the 6 spec files using Jinja2 templates,
then optionally generates a spec.lock.yaml for reproducibility.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import structlog
from jinja2 import Environment, PackageLoader

from intake.generate.lock import LOCK_FILENAME, create_lock

if TYPE_CHECKING:
    from intake.analyze.models import AnalysisResult
    from intake.config.schema import IntakeConfig
    from intake.ingest.base import ParsedContent

logger = structlog.get_logger()


class GenerateError(Exception):
    """Error during spec generation."""

    def __init__(self, reason: str, suggestion: str = "") -> None:
        self.reason = reason
        self.suggestion = suggestion
        msg = f"Generation failed: {reason}"
        if suggestion:
            msg += f"\n  Hint: {suggestion}"
        super().__init__(msg)


# Mapping of spec filename to its Jinja2 template.
SPEC_FILES: dict[str, str] = {
    "requirements.md": "requirements.md.j2",
    "design.md": "design.md.j2",
    "tasks.md": "tasks.md.j2",
    "acceptance.yaml": "acceptance.yaml.j2",
    "context.md": "context.md.j2",
    "sources.md": "sources.md.j2",
}


class SpecBuilder:
    """Orchestrates generation of the 6 spec files + lock.

    Uses Jinja2 templates from the intake/templates package directory.

    Args:
        config: Full intake configuration.
    """

    def __init__(self, config: IntakeConfig) -> None:
        self.config = config
        self.env = Environment(
            loader=PackageLoader("intake", "templates"),
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(
        self,
        result: AnalysisResult,
        sources: list[ParsedContent],
        spec_name: str,
    ) -> list[str]:
        """Generate all spec files to the configured output directory.

        Args:
            result: Complete analysis result.
            sources: Original parsed sources (for traceability).
            spec_name: Name for this spec (used as subdirectory).

        Returns:
            List of generated file paths.
        """
        output_dir = Path(self.config.spec.output_dir) / spec_name
        output_dir.mkdir(parents=True, exist_ok=True)

        generated: list[str] = []

        # Build template context
        context = self._build_context(result, sources)

        # Render each spec file
        for filename, template_name in SPEC_FILES.items():
            output_path = output_dir / filename
            content = self._render_template(template_name, context)
            output_path.write_text(content, encoding="utf-8")
            generated.append(str(output_path))

            logger.debug("spec_file_generated", file=filename, path=str(output_path))

        # Generate lock file
        if self.config.spec.generate_lock:
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
            "spec_generation_complete",
            spec_name=spec_name,
            output_dir=str(output_dir),
            files=len(generated),
        )

        return generated

    def _build_context(
        self,
        result: AnalysisResult,
        sources: list[ParsedContent],
    ) -> dict[str, object]:
        """Build the template rendering context from analysis results.

        Args:
            result: Complete analysis result.
            sources: Original parsed sources.

        Returns:
            Dict of template variables.
        """
        design = result.design

        return {
            # Requirements template
            "functional_requirements": result.functional_requirements,
            "non_functional_requirements": result.non_functional_requirements,
            "conflicts": result.conflicts,
            "open_questions": result.open_questions,
            "all_requirements": result.all_requirements,
            # Design template
            "components": design.components,
            "files_to_create": design.files_to_create,
            "files_to_modify": design.files_to_modify,
            "tech_decisions": design.tech_decisions,
            "dependencies": design.dependencies,
            # Tasks template
            "tasks": design.tasks,
            # Acceptance template
            "checks": design.acceptance_checks,
            # Context template
            "project_name": self.config.project.name,
            "language": self.config.project.language,
            "stack": self.config.project.stack,
            "conventions": self.config.project.conventions,
            "functional_count": len(result.functional_requirements),
            "non_functional_count": len(result.non_functional_requirements),
            "question_count": len(result.open_questions),
            "conflict_count": len(result.conflicts),
            "risk_count": len(result.risks),
            "risks": result.risks,
            "component_count": len(design.components),
            "files_to_create_count": len(design.files_to_create),
            "files_to_modify_count": len(design.files_to_modify),
            "task_count": result.task_count,
            "check_count": len(design.acceptance_checks),
            # Sources template
            "sources": sources,
            # Metadata
            "model_used": result.model_used,
            "total_cost": result.total_cost,
            "duplicates_removed": result.duplicates_removed,
        }

    def _render_template(self, template_name: str, context: dict[str, object]) -> str:
        """Render a single Jinja2 template with the given context.

        Args:
            template_name: Template filename (e.g., "requirements.md.j2").
            context: Template variables.

        Returns:
            Rendered string content.
        """
        template = self.env.get_template(template_name)
        return template.render(**context)
