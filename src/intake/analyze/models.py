"""Data models for the analysis pipeline.

All models are dataclasses (lightweight, no validation overhead).
These flow between analyze sub-phases and into the generate module.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Requirement:
    """A single extracted requirement (functional or non-functional)."""

    id: str
    type: str  # "functional" | "non_functional"
    title: str
    description: str
    acceptance_criteria: list[str]
    source: str
    priority: str = "medium"
    risk_score: float = 0.0


@dataclass
class Conflict:
    """A contradiction detected between two sources."""

    id: str
    description: str
    source_a: dict[str, str]
    source_b: dict[str, str]
    recommendation: str
    severity: str = "medium"  # "low" | "medium" | "high"


@dataclass
class OpenQuestion:
    """An ambiguity that cannot be resolved from available sources."""

    id: str
    question: str
    context: str
    source: str
    recommendation: str


@dataclass
class RiskItem:
    """Risk assessment for a requirement or group of requirements."""

    id: str
    requirement_ids: list[str]
    description: str
    probability: str  # "low" | "medium" | "high"
    impact: str  # "low" | "medium" | "high"
    mitigation: str
    category: str  # "technical" | "scope" | "integration" | "security" | "performance"


@dataclass
class TechDecision:
    """A technical design decision linked to a requirement."""

    decision: str
    justification: str
    requirement: str


@dataclass
class TaskItem:
    """An atomic implementation task."""

    id: int
    title: str
    description: str
    files: list[str]
    dependencies: list[int]
    checks: list[str]
    estimated_minutes: int = 15


@dataclass
class FileAction:
    """A file to create or modify."""

    path: str
    description: str
    action: str = "create"  # "create" | "modify"


@dataclass
class AcceptanceCheck:
    """An executable acceptance check."""

    id: str
    name: str
    type: str  # "command" | "files_exist" | "pattern_present" | "pattern_absent"
    required: bool = True
    tags: list[str] = field(default_factory=list)
    command: str = ""
    paths: list[str] = field(default_factory=list)
    glob: str = ""
    patterns: list[str] = field(default_factory=list)


@dataclass
class DesignResult:
    """Output of the design analysis phase."""

    components: list[str] = field(default_factory=list)
    files_to_create: list[FileAction] = field(default_factory=list)
    files_to_modify: list[FileAction] = field(default_factory=list)
    tech_decisions: list[TechDecision] = field(default_factory=list)
    tasks: list[TaskItem] = field(default_factory=list)
    acceptance_checks: list[AcceptanceCheck] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Complete output of the analysis pipeline.

    Aggregates requirements, conflicts, questions, risks, and design.
    This is the primary data structure consumed by the generate module.
    """

    functional_requirements: list[Requirement] = field(default_factory=list)
    non_functional_requirements: list[Requirement] = field(default_factory=list)
    open_questions: list[OpenQuestion] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    risks: list[RiskItem] = field(default_factory=list)
    design: DesignResult = field(default_factory=DesignResult)
    duplicates_removed: int = 0
    total_cost: float = 0.0
    model_used: str = ""

    @property
    def all_requirements(self) -> list[Requirement]:
        """All requirements (functional + non-functional)."""
        return self.functional_requirements + self.non_functional_requirements

    @property
    def requirement_count(self) -> int:
        """Total number of requirements."""
        return len(self.functional_requirements) + len(self.non_functional_requirements)

    @property
    def task_count(self) -> int:
        """Total number of tasks."""
        return len(self.design.tasks)
