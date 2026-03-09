"""Tests for generate/spec_builder.py — spec generation orchestrator."""

from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

from intake.analyze.models import (
    AcceptanceCheck,
    AnalysisResult,
    Conflict,
    DesignResult,
    FileAction,
    OpenQuestion,
    Requirement,
    RiskItem,
    TaskItem,
    TechDecision,
)
from intake.config.schema import IntakeConfig
from intake.generate.spec_builder import SpecBuilder
from intake.ingest.base import ParsedContent

if TYPE_CHECKING:
    from pathlib import Path


def _sample_result() -> AnalysisResult:
    """Create a realistic AnalysisResult for testing."""
    return AnalysisResult(
        functional_requirements=[
            Requirement(
                id="FR-01",
                type="functional",
                title="User login",
                description="When a user submits credentials, the system shall authenticate.",
                acceptance_criteria=["AC-01.1: Returns 200 on valid login"],
                source="Source 1",
                priority="high",
            ),
        ],
        non_functional_requirements=[
            Requirement(
                id="NFR-01",
                type="non_functional",
                title="Response time",
                description="API responds within 200ms p95.",
                acceptance_criteria=["AC-NFR-01.1: p95 < 200ms"],
                source="Source 1",
                priority="medium",
            ),
        ],
        open_questions=[
            OpenQuestion(
                id="Q-01",
                question="Which OAuth providers?",
                context="Not specified",
                source="Source 1",
                recommendation="Ask stakeholders",
            ),
        ],
        conflicts=[
            Conflict(
                id="CONFLICT-01",
                description="Auth method disagreement",
                source_a={"source": "Source 1", "says": "JWT"},
                source_b={"source": "Source 2", "says": "Sessions"},
                recommendation="Use JWT",
                severity="medium",
            ),
        ],
        risks=[
            RiskItem(
                id="RISK-01",
                requirement_ids=["FR-01"],
                description="Token security",
                probability="medium",
                impact="high",
                mitigation="Use short-lived tokens",
                category="security",
            ),
        ],
        design=DesignResult(
            components=["auth-module"],
            files_to_create=[
                FileAction(path="src/auth.py", description="Auth handler"),
            ],
            files_to_modify=[],
            tech_decisions=[
                TechDecision(
                    decision="Use JWT",
                    justification="Stateless auth",
                    requirement="FR-01",
                ),
            ],
            tasks=[
                TaskItem(
                    id=1,
                    title="Create auth module",
                    description="Implement JWT auth",
                    files=["src/auth.py"],
                    dependencies=[],
                    checks=["pytest tests/test_auth.py"],
                    estimated_minutes=20,
                ),
            ],
            acceptance_checks=[
                AcceptanceCheck(
                    id="tests-pass",
                    name="Tests pass",
                    type="command",
                    command="pytest -q",
                    required=True,
                    tags=["test"],
                ),
            ],
            dependencies=["pyjwt"],
        ),
        model_used="test-model",
        total_cost=0.05,
    )


def _sample_sources() -> list[ParsedContent]:
    """Create test sources."""
    return [
        ParsedContent(
            text="Build a user authentication system",
            format="markdown",
            source="reqs.md",
            metadata={},
            sections=[{"title": "Requirements", "content": "Auth requirements"}],
        ),
    ]


class TestSpecBuilder:
    """Tests for SpecBuilder."""

    def test_generates_all_spec_files(self, tmp_path: Path) -> None:
        config = IntakeConfig()
        config.spec.output_dir = str(tmp_path)
        builder = SpecBuilder(config)

        result = _sample_result()
        sources = _sample_sources()

        generated = builder.generate(result, sources, "test-spec")

        spec_dir = tmp_path / "test-spec"
        assert spec_dir.exists()

        expected_files = [
            "requirements.md",
            "design.md",
            "tasks.md",
            "acceptance.yaml",
            "context.md",
            "sources.md",
            "spec.lock.yaml",
        ]
        for filename in expected_files:
            assert (spec_dir / filename).exists(), f"Missing: {filename}"

        assert len(generated) == 7

    def test_requirements_md_contains_requirement(self, tmp_path: Path) -> None:
        config = IntakeConfig()
        config.spec.output_dir = str(tmp_path)
        builder = SpecBuilder(config)

        builder.generate(_sample_result(), _sample_sources(), "test-spec")

        content = (tmp_path / "test-spec" / "requirements.md").read_text()
        assert "FR-01" in content
        assert "User login" in content
        assert "AC-01.1" in content

    def test_design_md_contains_components(self, tmp_path: Path) -> None:
        config = IntakeConfig()
        config.spec.output_dir = str(tmp_path)
        builder = SpecBuilder(config)

        builder.generate(_sample_result(), _sample_sources(), "test-spec")

        content = (tmp_path / "test-spec" / "design.md").read_text()
        assert "auth-module" in content
        assert "src/auth.py" in content
        assert "JWT" in content

    def test_tasks_md_contains_tasks(self, tmp_path: Path) -> None:
        config = IntakeConfig()
        config.spec.output_dir = str(tmp_path)
        builder = SpecBuilder(config)

        builder.generate(_sample_result(), _sample_sources(), "test-spec")

        content = (tmp_path / "test-spec" / "tasks.md").read_text()
        assert "Create auth module" in content
        assert "src/auth.py" in content

    def test_acceptance_yaml_contains_checks(self, tmp_path: Path) -> None:
        config = IntakeConfig()
        config.spec.output_dir = str(tmp_path)
        builder = SpecBuilder(config)

        builder.generate(_sample_result(), _sample_sources(), "test-spec")

        content = (tmp_path / "test-spec" / "acceptance.yaml").read_text()
        assert "tests-pass" in content
        assert "pytest -q" in content

    def test_context_md_contains_project_info(self, tmp_path: Path) -> None:
        config = IntakeConfig()
        config.spec.output_dir = str(tmp_path)
        config.project.name = "my-project"
        builder = SpecBuilder(config)

        builder.generate(_sample_result(), _sample_sources(), "test-spec")

        content = (tmp_path / "test-spec" / "context.md").read_text()
        assert "my-project" in content

    def test_sources_md_contains_traceability(self, tmp_path: Path) -> None:
        config = IntakeConfig()
        config.spec.output_dir = str(tmp_path)
        builder = SpecBuilder(config)

        builder.generate(_sample_result(), _sample_sources(), "test-spec")

        content = (tmp_path / "test-spec" / "sources.md").read_text()
        assert "reqs.md" in content
        assert "FR-01" in content

    def test_skips_lock_when_disabled(self, tmp_path: Path) -> None:
        config = IntakeConfig()
        config.spec.output_dir = str(tmp_path)
        config.spec.generate_lock = False
        builder = SpecBuilder(config)

        generated = builder.generate(_sample_result(), _sample_sources(), "test-spec")

        assert not (tmp_path / "test-spec" / "spec.lock.yaml").exists()
        assert len(generated) == 6

    def test_creates_output_directory(self, tmp_path: Path) -> None:
        config = IntakeConfig()
        config.spec.output_dir = str(tmp_path / "nested" / "output")
        builder = SpecBuilder(config)

        builder.generate(_sample_result(), _sample_sources(), "test-spec")

        assert (tmp_path / "nested" / "output" / "test-spec").exists()

    def test_requirements_md_contains_conflicts(self, tmp_path: Path) -> None:
        config = IntakeConfig()
        config.spec.output_dir = str(tmp_path)
        builder = SpecBuilder(config)

        builder.generate(_sample_result(), _sample_sources(), "test-spec")

        content = (tmp_path / "test-spec" / "requirements.md").read_text()
        assert "CONFLICT-01" in content
        assert "Auth method disagreement" in content

    def test_requirements_md_contains_open_questions(self, tmp_path: Path) -> None:
        config = IntakeConfig()
        config.spec.output_dir = str(tmp_path)
        builder = SpecBuilder(config)

        builder.generate(_sample_result(), _sample_sources(), "test-spec")

        content = (tmp_path / "test-spec" / "requirements.md").read_text()
        assert "Q-01" in content
        assert "OAuth" in content

    def test_acceptance_yaml_valid_with_embedded_quotes(self, tmp_path: Path) -> None:
        """BUG-008: Commands with embedded quotes must produce valid YAML."""
        result = _sample_result()
        result.design.acceptance_checks = [
            AcceptanceCheck(
                id="ac-quotes",
                name='Registration endpoint "behavior"',
                type="command",
                required=True,
                tags=["FR-01"],
                command="python -c \"from src.auth.router import register_user; print('ok')\"",
            ),
            AcceptanceCheck(
                id="ac-grep",
                name="Token uses RS256",
                type="command",
                required=True,
                tags=["FR-02"],
                command='grep -R "RS256" src || true',
            ),
        ]

        config = IntakeConfig()
        config.spec.output_dir = str(tmp_path)
        builder = SpecBuilder(config)
        builder.generate(result, _sample_sources(), "test-spec")

        yaml_path = tmp_path / "test-spec" / "acceptance.yaml"
        raw = yaml_path.read_text()

        # Must be valid YAML (this was the BUG-008 failure)
        data = yaml.safe_load(raw)
        assert isinstance(data, dict)
        assert len(data["checks"]) == 2
        assert "register_user" in data["checks"][0]["command"]
        assert "RS256" in data["checks"][1]["command"]

    def test_acceptance_yaml_valid_with_special_chars(self, tmp_path: Path) -> None:
        """BUG-008: Special YAML chars (%, @, :) must be properly escaped."""
        result = _sample_result()
        result.design.acceptance_checks = [
            AcceptanceCheck(
                id="ac-special",
                name="Check 100% coverage & @admin roles: verified",
                type="command",
                required=True,
                command="echo '100% done' && test @admin",
            ),
        ]

        config = IntakeConfig()
        config.spec.output_dir = str(tmp_path)
        builder = SpecBuilder(config)
        builder.generate(result, _sample_sources(), "test-spec")

        yaml_path = tmp_path / "test-spec" / "acceptance.yaml"
        data = yaml.safe_load(yaml_path.read_text())
        assert data["checks"][0]["name"] == "Check 100% coverage & @admin roles: verified"
