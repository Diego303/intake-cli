"""Tests for adaptive spec generation."""

from __future__ import annotations

from pathlib import Path

from intake.analyze.complexity import ComplexityAssessment, classify_complexity
from intake.analyze.models import (
    AnalysisResult,
    DesignResult,
    Requirement,
    TaskItem,
)
from intake.config.schema import IntakeConfig
from intake.generate.adaptive import (
    ENTERPRISE_FILES,
    QUICK_FILES,
    STANDARD_FILES,
    AdaptiveSpecBuilder,
    GenerationPlan,
    create_generation_plan,
)
from intake.generate.spec_builder import SPEC_FILES
from intake.ingest.base import ParsedContent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_assessment(mode: str = "standard") -> ComplexityAssessment:
    """Create a ComplexityAssessment with the given mode."""
    return ComplexityAssessment(
        mode=mode,  # type: ignore[arg-type]
        total_words=1000,
        source_count=2,
        has_multiple_formats=False,
        has_structured_content=False,
        confidence=0.8,
        reason="test",
    )


def _make_config(**overrides: object) -> IntakeConfig:
    """Create an IntakeConfig with optional spec overrides."""
    config = IntakeConfig()
    for key, value in overrides.items():
        setattr(config.spec, key, value)
    return config


def _make_analysis_result() -> AnalysisResult:
    """Create a minimal AnalysisResult for generation."""
    return AnalysisResult(
        functional_requirements=[
            Requirement(
                id="REQ-001",
                type="functional",
                title="Test Requirement",
                description="A test requirement.",
                acceptance_criteria=["It works"],
                source="test.md",
            ),
        ],
        design=DesignResult(
            components=["api"],
            tasks=[
                TaskItem(
                    id=1,
                    title="Task 1",
                    description="Do something",
                    files=["app.py"],
                    dependencies=[],
                    checks=["test_task_1"],
                ),
            ],
        ),
        model_used="test-model",
        total_cost=0.01,
    )


def _make_sources() -> list[ParsedContent]:
    """Create minimal sources for generation."""
    return [
        ParsedContent(
            text="Test content for spec generation.",
            format="markdown",
            source="test.md",
        ),
    ]


# ---------------------------------------------------------------------------
# Tests — GenerationPlan
# ---------------------------------------------------------------------------


class TestGenerationPlan:
    def test_dataclass_creation(self) -> None:
        plan = GenerationPlan(
            mode="standard",
            files_to_generate=STANDARD_FILES,
            design_depth="moderate",
            task_granularity="medium",
            include_risks=True,
            include_sources=True,
        )
        assert plan.mode == "standard"
        assert "requirements.md" in plan.files_to_generate
        assert plan.design_depth == "moderate"


# ---------------------------------------------------------------------------
# Tests — create_generation_plan
# ---------------------------------------------------------------------------


class TestCreateGenerationPlan:
    def test_quick_plan(self) -> None:
        assessment = _make_assessment("quick")
        config = _make_config()
        plan = create_generation_plan(assessment, config)

        assert plan.mode == "quick"
        assert plan.files_to_generate == QUICK_FILES
        assert plan.design_depth == "minimal"
        assert plan.task_granularity == "coarse"
        assert not plan.include_risks
        assert not plan.include_sources

    def test_standard_plan_uses_config_defaults(self) -> None:
        assessment = _make_assessment("standard")
        config = _make_config()
        plan = create_generation_plan(assessment, config)

        assert plan.mode == "standard"
        assert plan.files_to_generate == STANDARD_FILES
        assert plan.design_depth == config.spec.design_depth
        assert plan.task_granularity == config.spec.task_granularity
        assert plan.include_risks == config.spec.risk_assessment
        assert plan.include_sources == config.spec.include_sources

    def test_standard_plan_respects_config_overrides(self) -> None:
        assessment = _make_assessment("standard")
        config = _make_config(
            design_depth="detailed",
            task_granularity="fine",
            risk_assessment=False,
            include_sources=False,
        )
        plan = create_generation_plan(assessment, config)

        assert plan.design_depth == "detailed"
        assert plan.task_granularity == "fine"
        assert not plan.include_risks
        assert not plan.include_sources

    def test_enterprise_plan(self) -> None:
        assessment = _make_assessment("enterprise")
        config = _make_config()
        plan = create_generation_plan(assessment, config)

        assert plan.mode == "enterprise"
        assert plan.files_to_generate == ENTERPRISE_FILES
        assert plan.design_depth == "detailed"
        assert plan.task_granularity == "fine"
        assert plan.include_risks
        assert plan.include_sources

    def test_quick_files_are_subset_of_standard(self) -> None:
        assert QUICK_FILES.issubset(STANDARD_FILES)

    def test_enterprise_files_equal_standard_files(self) -> None:
        assert ENTERPRISE_FILES == STANDARD_FILES


# ---------------------------------------------------------------------------
# Tests — AdaptiveSpecBuilder
# ---------------------------------------------------------------------------


class TestAdaptiveSpecBuilder:
    def test_plan_property(self) -> None:
        plan = GenerationPlan(
            mode="quick",
            files_to_generate=QUICK_FILES,
            design_depth="minimal",
            task_granularity="coarse",
            include_risks=False,
            include_sources=False,
        )
        config = _make_config()
        builder = AdaptiveSpecBuilder(config, plan)
        assert builder.plan is plan

    def test_quick_generates_only_two_files(self, tmp_path: Path) -> None:
        config = _make_config(output_dir=str(tmp_path), generate_lock=False)
        plan = GenerationPlan(
            mode="quick",
            files_to_generate=QUICK_FILES,
            design_depth="minimal",
            task_granularity="coarse",
            include_risks=False,
            include_sources=False,
        )
        builder = AdaptiveSpecBuilder(config, plan)
        result = _make_analysis_result()
        sources = _make_sources()

        generated = builder.generate(result, sources, "test-spec")

        filenames = {Path(p).name for p in generated}
        assert filenames == {"context.md", "tasks.md"}

    def test_standard_generates_all_files(self, tmp_path: Path) -> None:
        config = _make_config(output_dir=str(tmp_path), generate_lock=False)
        plan = GenerationPlan(
            mode="standard",
            files_to_generate=STANDARD_FILES,
            design_depth="moderate",
            task_granularity="medium",
            include_risks=True,
            include_sources=True,
        )
        builder = AdaptiveSpecBuilder(config, plan)
        result = _make_analysis_result()
        sources = _make_sources()

        generated = builder.generate(result, sources, "test-spec")

        filenames = {Path(p).name for p in generated}
        assert filenames == set(SPEC_FILES.keys())

    def test_generates_lock_file_when_configured(self, tmp_path: Path) -> None:
        config = _make_config(output_dir=str(tmp_path), generate_lock=True)
        plan = GenerationPlan(
            mode="quick",
            files_to_generate=QUICK_FILES,
            design_depth="minimal",
            task_granularity="coarse",
            include_risks=False,
            include_sources=False,
        )
        builder = AdaptiveSpecBuilder(config, plan)
        result = _make_analysis_result()
        sources = _make_sources()

        generated = builder.generate(result, sources, "test-spec")

        filenames = {Path(p).name for p in generated}
        assert "spec.lock.yaml" in filenames
        # Quick mode: 2 spec files + lock
        assert len(generated) == 3

    def test_no_lock_file_when_disabled(self, tmp_path: Path) -> None:
        config = _make_config(output_dir=str(tmp_path), generate_lock=False)
        plan = GenerationPlan(
            mode="quick",
            files_to_generate=QUICK_FILES,
            design_depth="minimal",
            task_granularity="coarse",
            include_risks=False,
            include_sources=False,
        )
        builder = AdaptiveSpecBuilder(config, plan)
        result = _make_analysis_result()
        sources = _make_sources()

        generated = builder.generate(result, sources, "test-spec")

        filenames = {Path(p).name for p in generated}
        assert "spec.lock.yaml" not in filenames

    def test_output_directory_created(self, tmp_path: Path) -> None:
        config = _make_config(output_dir=str(tmp_path), generate_lock=False)
        plan = GenerationPlan(
            mode="quick",
            files_to_generate=QUICK_FILES,
            design_depth="minimal",
            task_granularity="coarse",
            include_risks=False,
            include_sources=False,
        )
        builder = AdaptiveSpecBuilder(config, plan)
        result = _make_analysis_result()
        sources = _make_sources()

        builder.generate(result, sources, "new-spec")

        spec_dir = tmp_path / "new-spec"
        assert spec_dir.exists()
        assert (spec_dir / "context.md").exists()
        assert (spec_dir / "tasks.md").exists()

    def test_enterprise_generates_all_files(self, tmp_path: Path) -> None:
        config = _make_config(output_dir=str(tmp_path), generate_lock=False)
        plan = GenerationPlan(
            mode="enterprise",
            files_to_generate=ENTERPRISE_FILES,
            design_depth="detailed",
            task_granularity="fine",
            include_risks=True,
            include_sources=True,
        )
        builder = AdaptiveSpecBuilder(config, plan)
        result = _make_analysis_result()
        sources = _make_sources()

        generated = builder.generate(result, sources, "test-spec")

        filenames = {Path(p).name for p in generated}
        assert filenames == set(SPEC_FILES.keys())


# ---------------------------------------------------------------------------
# Tests — Integration (classify → plan → build)
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_full_pipeline_quick(self, tmp_path: Path) -> None:
        """End-to-end: small source → quick mode → 2 files."""
        sources = [
            ParsedContent(
                text="Fix the login button color.",
                format="plaintext",
                source="input.txt",
            ),
        ]

        assessment = classify_complexity(sources)
        assert assessment.mode == "quick"

        config = _make_config(output_dir=str(tmp_path), generate_lock=False)
        plan = create_generation_plan(assessment, config)
        assert plan.files_to_generate == QUICK_FILES

        builder = AdaptiveSpecBuilder(config, plan)
        result = _make_analysis_result()
        generated = builder.generate(result, sources, "quick-spec")

        assert len(generated) == 2
        filenames = {Path(p).name for p in generated}
        assert filenames == {"context.md", "tasks.md"}

    def test_full_pipeline_enterprise(self, tmp_path: Path) -> None:
        """End-to-end: many sources → enterprise mode → all files."""
        sources = [
            ParsedContent(
                text=" ".join(["word"] * 300),
                format=f"format_{i}",
                source=f"source_{i}.md",
            )
            for i in range(5)
        ]

        assessment = classify_complexity(sources)
        assert assessment.mode == "enterprise"

        config = _make_config(output_dir=str(tmp_path), generate_lock=False)
        plan = create_generation_plan(assessment, config)
        assert plan.files_to_generate == ENTERPRISE_FILES

        builder = AdaptiveSpecBuilder(config, plan)
        result = _make_analysis_result()
        generated = builder.generate(result, sources, "enterprise-spec")

        assert len(generated) == len(SPEC_FILES)
