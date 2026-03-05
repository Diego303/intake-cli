"""Tests for configuration schema validation."""

from __future__ import annotations

from intake.config.schema import (
    ConfluenceConfig,
    ConnectorsConfig,
    ExportConfig,
    FeedbackConfig,
    GithubConfig,
    IntakeConfig,
    JiraConfig,
    LLMConfig,
    MCPConfig,
    ProjectConfig,
    SecurityConfig,
    SpecConfig,
    VerificationConfig,
    WatchConfig,
)


class TestLLMConfig:
    def test_defaults(self) -> None:
        config = LLMConfig()
        assert config.model == "claude-sonnet-4"
        assert config.api_key_env == "ANTHROPIC_API_KEY"
        assert config.max_cost_per_spec == 0.50
        assert config.temperature == 0.2
        assert config.max_retries == 3
        assert config.timeout == 120

    def test_custom_values(self) -> None:
        config = LLMConfig(model="gpt-4o", temperature=0.5)
        assert config.model == "gpt-4o"
        assert config.temperature == 0.5


class TestSpecConfig:
    def test_defaults(self) -> None:
        config = SpecConfig()
        assert config.requirements_format == "ears"
        assert config.design_depth == "moderate"
        assert config.generate_lock is True
        assert config.risk_assessment is True

    def test_literal_validation(self) -> None:
        config = SpecConfig(requirements_format="bdd")
        assert config.requirements_format == "bdd"


class TestExportConfig:
    def test_defaults(self) -> None:
        config = ExportConfig()
        assert config.default_format == "generic"
        assert config.claude_code_generate_claude_md is True
        assert config.claude_code_task_dir == ".intake/tasks"
        assert config.cursor_rules_dir == ".cursor/rules"

    def test_copilot_format_allowed(self) -> None:
        config = ExportConfig(default_format="copilot")
        assert config.default_format == "copilot"


class TestJiraConfig:
    def test_defaults(self) -> None:
        config = JiraConfig()
        assert config.url == ""
        assert config.auth_type == "token"
        assert config.token_env == "JIRA_API_TOKEN"
        assert config.email_env == "JIRA_EMAIL"
        assert config.default_project == ""
        assert config.include_comments is True
        assert config.max_comments == 5
        assert "summary" in config.fields
        assert "description" in config.fields

    def test_custom_values(self) -> None:
        config = JiraConfig(
            url="https://mycompany.atlassian.net",
            email_env="MY_JIRA_EMAIL",
            max_comments=10,
        )
        assert config.url == "https://mycompany.atlassian.net"
        assert config.email_env == "MY_JIRA_EMAIL"
        assert config.max_comments == 10


class TestConfluenceConfig:
    def test_defaults(self) -> None:
        config = ConfluenceConfig()
        assert config.url == ""
        assert config.auth_type == "token"
        assert config.token_env == "CONFLUENCE_API_TOKEN"
        assert config.email_env == "CONFLUENCE_EMAIL"
        assert config.default_space == ""
        assert config.include_child_pages is False
        assert config.max_depth == 1


class TestGithubConfig:
    def test_defaults(self) -> None:
        config = GithubConfig()
        assert config.token_env == "GITHUB_TOKEN"
        assert config.default_repo == ""


class TestConnectorsConfig:
    def test_defaults(self) -> None:
        config = ConnectorsConfig()
        assert isinstance(config.jira, JiraConfig)
        assert isinstance(config.confluence, ConfluenceConfig)
        assert isinstance(config.github, GithubConfig)


class TestFeedbackConfig:
    def test_defaults(self) -> None:
        config = FeedbackConfig()
        assert config.auto_amend_spec is False
        assert config.max_suggestions == 10
        assert config.include_code_snippets is True

    def test_custom_values(self) -> None:
        config = FeedbackConfig(auto_amend_spec=True, max_suggestions=5)
        assert config.auto_amend_spec is True
        assert config.max_suggestions == 5


class TestMCPConfig:
    def test_defaults(self) -> None:
        config = MCPConfig()
        assert config.specs_dir == "./specs"
        assert config.project_dir == "."
        assert config.transport == "stdio"
        assert config.sse_port == 8080

    def test_custom_values(self) -> None:
        config = MCPConfig(
            specs_dir="/my/specs",
            transport="sse",
            sse_port=9090,
        )
        assert config.specs_dir == "/my/specs"
        assert config.transport == "sse"
        assert config.sse_port == 9090


class TestWatchConfig:
    def test_defaults(self) -> None:
        config = WatchConfig()
        assert config.debounce_seconds == 2.0
        assert "*.pyc" in config.ignore_patterns
        assert "__pycache__" in config.ignore_patterns
        assert ".git" in config.ignore_patterns
        assert "node_modules" in config.ignore_patterns
        assert ".intake" in config.ignore_patterns

    def test_custom_values(self) -> None:
        config = WatchConfig(
            debounce_seconds=5.0,
            ignore_patterns=["*.log", "dist/"],
        )
        assert config.debounce_seconds == 5.0
        assert config.ignore_patterns == ["*.log", "dist/"]


class TestIntakeConfig:
    def test_defaults(self) -> None:
        config = IntakeConfig()
        assert isinstance(config.llm, LLMConfig)
        assert isinstance(config.project, ProjectConfig)
        assert isinstance(config.spec, SpecConfig)
        assert isinstance(config.verification, VerificationConfig)
        assert isinstance(config.export, ExportConfig)
        assert isinstance(config.security, SecurityConfig)
        assert isinstance(config.connectors, ConnectorsConfig)
        assert isinstance(config.feedback, FeedbackConfig)
        assert isinstance(config.mcp, MCPConfig)
        assert isinstance(config.watch, WatchConfig)

    def test_nested_override(self) -> None:
        config = IntakeConfig(llm=LLMConfig(model="gpt-4o"))
        assert config.llm.model == "gpt-4o"
        assert config.spec.requirements_format == "ears"

    def test_model_copy_update(self) -> None:
        config = IntakeConfig()
        updated = config.model_copy(
            update={"llm": config.llm.model_copy(update={"model": "gemini-pro"})}
        )
        assert updated.llm.model == "gemini-pro"
        assert config.llm.model == "claude-sonnet-4"

    def test_feedback_nested(self) -> None:
        config = IntakeConfig(feedback=FeedbackConfig(auto_amend_spec=True))
        assert config.feedback.auto_amend_spec is True

    def test_mcp_nested_override(self) -> None:
        config = IntakeConfig(mcp=MCPConfig(specs_dir="/custom/specs"))
        assert config.mcp.specs_dir == "/custom/specs"
        assert config.mcp.transport == "stdio"

    def test_watch_nested_override(self) -> None:
        config = IntakeConfig(watch=WatchConfig(debounce_seconds=10.0))
        assert config.watch.debounce_seconds == 10.0
        assert ".git" in config.watch.ignore_patterns
