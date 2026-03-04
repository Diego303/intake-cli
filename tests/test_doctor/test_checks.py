"""Tests for the doctor health checks."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from intake.doctor.checks import DiagnosticResult, DoctorChecks


class TestDoctorChecks:
    def test_run_all_returns_results(self) -> None:
        checks = DoctorChecks()
        results = checks.run_all(config_path="/nonexistent/.intake.yaml")
        assert len(results) > 0
        assert all(hasattr(r, "passed") for r in results)

    def test_python_version_passes(self) -> None:
        checks = DoctorChecks()
        result = checks._check_python_version()
        assert result.passed is True
        assert "Python" in result.message

    def test_api_key_passes_when_set(self) -> None:
        checks = DoctorChecks()
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-12345678"}):
            result = checks._check_api_key()
        assert result.passed is True
        assert "ANTHROPIC_API_KEY" in result.message

    def test_api_key_fails_when_unset(self) -> None:
        checks = DoctorChecks()
        env = {
            k: v for k, v in os.environ.items() if k not in {"ANTHROPIC_API_KEY", "OPENAI_API_KEY"}
        }
        with patch.dict(os.environ, env, clear=True):
            result = checks._check_api_key()
        assert result.passed is False
        assert "No LLM API key" in result.message

    def test_optional_deps_include_pdfplumber(self) -> None:
        checks = DoctorChecks()
        results = checks._check_optional_deps()
        names = [r.name for r in results]
        assert any("PDF" in n for n in names)

    def test_config_no_file_is_ok(self) -> None:
        checks = DoctorChecks()
        result = checks._check_config("/nonexistent/.intake.yaml")
        assert result.passed is True
        assert "using defaults" in result.message.lower()

    def test_config_valid_yaml(self, tmp_yaml_config: Path) -> None:
        checks = DoctorChecks()
        result = checks._check_config(str(tmp_yaml_config))
        assert result.passed is True

    def test_config_invalid_yaml(self, invalid_yaml_config: Path) -> None:
        checks = DoctorChecks()
        result = checks._check_config(str(invalid_yaml_config))
        assert result.passed is False
        assert "Invalid YAML" in result.message

    def test_config_non_mapping(self, tmp_path: Path) -> None:
        config = tmp_path / ".intake.yaml"
        config.write_text("- just\n- a\n- list\n")
        checks = DoctorChecks()
        result = checks._check_config(str(config))
        assert result.passed is False
        assert "not a valid YAML mapping" in result.message


class TestDoctorConnectors:
    """Tests for connector credential checks."""

    def test_no_connectors_configured(self, tmp_path: Path) -> None:
        """No connector checks when no connectors in config."""
        config = tmp_path / ".intake.yaml"
        config.write_text("llm:\n  model: test\n")
        checks = DoctorChecks()
        results = checks._check_connectors(str(config))
        assert results == []

    def test_jira_credentials_pass(self, tmp_path: Path) -> None:
        """Jira check passes when credentials are set."""
        config = tmp_path / ".intake.yaml"
        config.write_text(
            "connectors:\n  jira:\n    url: https://jira.example.com\n"
            "    token_env: JIRA_TOKEN\n    email_env: JIRA_EMAIL\n"
        )
        checks = DoctorChecks()
        with patch.dict(os.environ, {"JIRA_TOKEN": "tok", "JIRA_EMAIL": "a@b.com"}):
            results = checks._check_connectors(str(config))
        assert len(results) == 1
        assert results[0].passed is True
        assert "Jira" in results[0].name

    def test_jira_credentials_fail(self, tmp_path: Path) -> None:
        """Jira check fails when credentials are missing."""
        config = tmp_path / ".intake.yaml"
        config.write_text("connectors:\n  jira:\n    url: https://jira.example.com\n")
        checks = DoctorChecks()
        env = {k: v for k, v in os.environ.items() if k not in {"JIRA_API_TOKEN", "JIRA_EMAIL"}}
        with patch.dict(os.environ, env, clear=True):
            results = checks._check_connectors(str(config))
        assert len(results) == 1
        assert results[0].passed is False
        assert "Missing" in results[0].message

    def test_confluence_credentials_pass(self, tmp_path: Path) -> None:
        """Confluence check passes when credentials are set."""
        config = tmp_path / ".intake.yaml"
        config.write_text("connectors:\n  confluence:\n    url: https://wiki.example.com\n")
        checks = DoctorChecks()
        with patch.dict(
            os.environ,
            {
                "CONFLUENCE_API_TOKEN": "tok",
                "CONFLUENCE_EMAIL": "a@b.com",
            },
        ):
            results = checks._check_connectors(str(config))
        assert len(results) == 1
        assert results[0].passed is True

    def test_github_token_pass(self, tmp_path: Path) -> None:
        """GitHub check passes when token is set."""
        config = tmp_path / ".intake.yaml"
        config.write_text("connectors:\n  github:\n    token_env: GITHUB_TOKEN\n")
        checks = DoctorChecks()
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test123"}):
            results = checks._check_connectors(str(config))
        assert len(results) == 1
        assert results[0].passed is True

    def test_github_token_fail(self, tmp_path: Path) -> None:
        """GitHub check fails when token is missing."""
        config = tmp_path / ".intake.yaml"
        config.write_text("connectors:\n  github:\n    token_env: GH_CUSTOM_TOKEN\n")
        checks = DoctorChecks()
        env = {k: v for k, v in os.environ.items() if k != "GH_CUSTOM_TOKEN"}
        with patch.dict(os.environ, env, clear=True):
            results = checks._check_connectors(str(config))
        assert len(results) == 1
        assert results[0].passed is False

    def test_no_config_file(self) -> None:
        """No checks when config file doesn't exist."""
        checks = DoctorChecks()
        results = checks._check_connectors("/nonexistent/.intake.yaml")
        assert results == []

    def test_multiple_connectors(self, tmp_path: Path) -> None:
        """Multiple connector checks when multiple are configured."""
        config = tmp_path / ".intake.yaml"
        config.write_text(
            "connectors:\n"
            "  jira:\n    url: https://jira.example.com\n"
            "  confluence:\n    url: https://wiki.example.com\n"
            "  github:\n    token_env: GITHUB_TOKEN\n"
        )
        checks = DoctorChecks()
        with patch.dict(
            os.environ,
            {
                "JIRA_API_TOKEN": "t",
                "JIRA_EMAIL": "e",
                "CONFLUENCE_API_TOKEN": "t",
                "CONFLUENCE_EMAIL": "e",
                "GITHUB_TOKEN": "ghp",
            },
        ):
            results = checks._check_connectors(str(config))
        assert len(results) == 3
        assert all(r.passed for r in results)


class TestDoctorFix:
    """Tests for the doctor --fix auto-fix functionality."""

    def test_fix_creates_config(self, tmp_path: Path) -> None:
        config_path = str(tmp_path / ".intake.yaml")
        checks = DoctorChecks()
        results = [
            DiagnosticResult(
                name="Configuration file",
                passed=True,
                message="No config",
                auto_fixable=True,
                fix_action="create_config",
            )
        ]
        fix_results = checks.fix(results, config_path=config_path)
        assert len(fix_results) == 1
        assert fix_results[0].success is True
        assert Path(config_path).exists()
        content = Path(config_path).read_text()
        assert "llm:" in content
        assert "model:" in content

    def test_fix_skips_existing_config(self, tmp_yaml_config: Path) -> None:
        checks = DoctorChecks()
        results = [
            DiagnosticResult(
                name="Configuration file",
                passed=True,
                message="Already exists",
                auto_fixable=True,
                fix_action="create_config",
            )
        ]
        fix_results = checks.fix(results, config_path=str(tmp_yaml_config))
        assert len(fix_results) == 1
        assert fix_results[0].success is False
        assert "already exists" in fix_results[0].message

    def test_fix_skips_passing_checks(self) -> None:
        checks = DoctorChecks()
        results = [
            DiagnosticResult(
                name="Python version",
                passed=True,
                message="OK",
            )
        ]
        fix_results = checks.fix(results)
        assert fix_results == []

    def test_fix_skips_non_fixable(self) -> None:
        checks = DoctorChecks()
        results = [
            DiagnosticResult(
                name="LLM API key",
                passed=False,
                message="Not set",
                auto_fixable=False,
            )
        ]
        fix_results = checks.fix(results)
        assert fix_results == []

    def test_fix_install_package_unknown(self) -> None:
        checks = DoctorChecks()
        results = [
            DiagnosticResult(
                name="Unknown package (nonexistent)",
                passed=False,
                message="Not installed",
                auto_fixable=True,
                fix_action="install_package",
            )
        ]
        fix_results = checks.fix(results)
        assert len(fix_results) == 1
        assert fix_results[0].success is False
        assert "Could not determine" in fix_results[0].message

    def test_find_pip_returns_string(self) -> None:
        result = DoctorChecks._find_pip()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_optional_deps_have_fix_action(self) -> None:
        checks = DoctorChecks()
        results = checks._check_optional_deps()
        for r in results:
            if not r.passed:
                assert r.auto_fixable is True
                assert r.fix_action == "install_package"

    def test_config_missing_has_fix_action(self) -> None:
        checks = DoctorChecks()
        result = checks._check_config("/nonexistent/.intake.yaml")
        assert result.auto_fixable is True
        assert result.fix_action == "create_config"
