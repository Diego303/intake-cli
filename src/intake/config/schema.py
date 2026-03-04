"""Pydantic v2 models for all intake configuration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """LLM configuration for analysis."""

    model: str = "claude-sonnet-4"
    api_key_env: str = "ANTHROPIC_API_KEY"
    max_cost_per_spec: float = 0.50
    temperature: float = 0.2
    max_retries: int = 3
    timeout: int = 120


class ProjectConfig(BaseModel):
    """Project configuration."""

    name: str = ""
    stack: list[str] = Field(default_factory=list)
    language: str = "en"
    conventions: dict[str, str] = Field(default_factory=dict)


class SpecConfig(BaseModel):
    """Spec format configuration."""

    output_dir: str = "./specs"
    requirements_format: Literal["ears", "user-stories", "bdd", "free"] = "ears"
    design_depth: Literal["minimal", "moderate", "detailed"] = "moderate"
    task_granularity: Literal["coarse", "medium", "fine"] = "medium"
    include_sources: bool = True
    version_specs: bool = True
    generate_lock: bool = True
    risk_assessment: bool = True
    auto_mode: bool = True


class VerificationConfig(BaseModel):
    """Verification configuration."""

    auto_generate_tests: bool = True
    test_output_dir: str = "./tests/generated"
    checks: list[str] = Field(default_factory=list)
    timeout_per_check: int = 120


class ExportConfig(BaseModel):
    """Export configuration."""

    default_format: Literal["architect", "claude-code", "cursor", "kiro", "copilot", "generic"] = (
        "generic"
    )
    architect_include_guardrails: bool = True
    architect_pipeline_template: str = "standard"
    claude_code_generate_claude_md: bool = True
    claude_code_task_dir: str = ".intake/tasks"
    cursor_rules_dir: str = ".cursor/rules"


class SecurityConfig(BaseModel):
    """Security and redaction configuration."""

    redact_patterns: list[str] = Field(default_factory=list)
    redact_files: list[str] = Field(default_factory=lambda: ["*.env", "*.pem", "*.key"])


# ---------------------------------------------------------------------------
# Connector configurations
# ---------------------------------------------------------------------------


class JiraConfig(BaseModel):
    """Jira API connector configuration."""

    url: str = ""
    auth_type: Literal["token", "oauth", "api_key"] = "token"
    token_env: str = "JIRA_API_TOKEN"
    email_env: str = "JIRA_EMAIL"
    default_project: str = ""
    include_comments: bool = True
    max_comments: int = 5
    fields: list[str] = Field(
        default_factory=lambda: [
            "summary",
            "description",
            "labels",
            "priority",
            "status",
            "issuelinks",
            "comment",
        ]
    )


class ConfluenceConfig(BaseModel):
    """Confluence API connector configuration."""

    url: str = ""
    auth_type: Literal["token", "oauth"] = "token"
    token_env: str = "CONFLUENCE_API_TOKEN"
    email_env: str = "CONFLUENCE_EMAIL"
    default_space: str = ""
    include_child_pages: bool = False
    max_depth: int = 1


class GithubConfig(BaseModel):
    """GitHub API connector configuration."""

    token_env: str = "GITHUB_TOKEN"
    default_repo: str = ""


class ConnectorsConfig(BaseModel):
    """Configuration for external connectors."""

    jira: JiraConfig = Field(default_factory=JiraConfig)
    confluence: ConfluenceConfig = Field(default_factory=ConfluenceConfig)
    github: GithubConfig = Field(default_factory=GithubConfig)


# ---------------------------------------------------------------------------
# Feedback configuration
# ---------------------------------------------------------------------------


class FeedbackConfig(BaseModel):
    """Feedback loop configuration."""

    auto_amend_spec: bool = False
    max_suggestions: int = 10
    include_code_snippets: bool = True


# ---------------------------------------------------------------------------
# Root configuration
# ---------------------------------------------------------------------------


class IntakeConfig(BaseModel):
    """Root intake configuration.

    Aggregates all sub-configurations. Built via layered merge:
    defaults -> preset -> .intake.yaml -> CLI flags.
    """

    llm: LLMConfig = Field(default_factory=LLMConfig)
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    spec: SpecConfig = Field(default_factory=SpecConfig)
    verification: VerificationConfig = Field(default_factory=VerificationConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    connectors: ConnectorsConfig = Field(default_factory=ConnectorsConfig)
    feedback: FeedbackConfig = Field(default_factory=FeedbackConfig)
