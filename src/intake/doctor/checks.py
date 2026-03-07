"""Environment and configuration health checks.

Verifies everything needed for intake to work properly:
- Python version (3.12+)
- Required CLI dependencies
- API key environment variables
- .intake.yaml validity

Supports ``--fix`` mode that auto-creates config and installs missing packages.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import structlog
import yaml

from intake.config.defaults import API_KEY_ENV_VARS

logger = structlog.get_logger()


class DoctorError(Exception):
    """Base exception for doctor module errors."""


REQUIRED_PYTHON_VERSION = (3, 12)

# Maps import name -> human-readable description.
OPTIONAL_DEPENDENCIES: dict[str, str] = {
    "pdfplumber": "PDF parsing (pdfplumber)",
    "docx": "DOCX parsing (python-docx)",
    "bs4": "HTML parsing (beautifulsoup4)",
    "markdownify": "HTML-to-Markdown (markdownify)",
    "litellm": "LLM integration (litellm)",
    "jinja2": "Template rendering (jinja2)",
}

# Maps import name -> pip package name for auto-install.
IMPORT_TO_PIP: dict[str, str] = {
    "pdfplumber": "pdfplumber",
    "docx": "python-docx",
    "bs4": "beautifulsoup4",
    "markdownify": "markdownify",
    "litellm": "litellm",
    "jinja2": "jinja2",
}

_DEFAULT_CONFIG_TEMPLATE = """\
# intake configuration
# See: https://github.com/anthropics/intake-cli for full docs

llm:
  model: claude-sonnet-4
  # max_cost_per_spec: 0.50

project:
  name: ""
  language: en
  # stack: []

spec:
  output_dir: ./specs
"""


@dataclass
class DiagnosticResult:
    """Result of a single diagnostic check."""

    name: str
    passed: bool
    message: str
    fix_hint: str = ""
    auto_fixable: bool = False
    fix_action: str = ""


@dataclass
class FixResult:
    """Result of an auto-fix attempt."""

    name: str
    success: bool
    message: str


class DoctorChecks:
    """Environment and configuration health checks.

    Verifies everything needed for intake to work properly:
    - Python version
    - Required CLI dependencies
    - API key environment variables
    - .intake.yaml validity
    """

    def run_all(self, config_path: str = ".intake.yaml") -> list[DiagnosticResult]:
        """Run all diagnostic checks.

        Args:
            config_path: Path to the config file to validate.

        Returns:
            List of DiagnosticResult for each check performed.
        """
        results: list[DiagnosticResult] = []
        results.append(self._check_python_version())
        results.append(self._check_api_key())
        results.extend(self._check_optional_deps())
        results.append(self._check_config(config_path))
        results.extend(self._check_connectors(config_path))
        logger.info(
            "doctor_checks_complete",
            total=len(results),
            passed=sum(1 for r in results if r.passed),
            failed=sum(1 for r in results if not r.passed),
        )
        return results

    def fix(
        self, results: list[DiagnosticResult], config_path: str = ".intake.yaml"
    ) -> list[FixResult]:
        """Attempt to auto-fix failed checks.

        Iterates through diagnostic results and attempts to fix each
        auto-fixable failure. Currently supports:
        - Installing missing Python packages via pip
        - Creating a default .intake.yaml config file

        Args:
            results: Diagnostic results from run_all().
            config_path: Path to the config file to create if missing.

        Returns:
            List of FixResult for each attempted fix.
        """
        fixes: list[FixResult] = []
        for result in results:
            if not result.auto_fixable:
                continue
            # Skip passed checks unless they have a create action
            # (e.g. missing config is "passed" but still fixable)
            if result.passed and result.fix_action != "create_config":
                continue

            if result.fix_action == "install_package":
                fix = self._fix_install_package(result.name)
                fixes.append(fix)
            elif result.fix_action == "create_config":
                fix = self._fix_create_config(config_path)
                fixes.append(fix)

        return fixes

    def _check_python_version(self) -> DiagnosticResult:
        """Check that Python version meets minimum requirement."""
        version = sys.version_info
        if version >= REQUIRED_PYTHON_VERSION:
            return DiagnosticResult(
                name="Python version",
                passed=True,
                message=f"Python {version.major}.{version.minor}.{version.micro}",
            )
        return DiagnosticResult(
            name="Python version",
            passed=False,
            message=(
                f"Python {version.major}.{version.minor} found, "
                f"{REQUIRED_PYTHON_VERSION[0]}.{REQUIRED_PYTHON_VERSION[1]}+ required"
            ),
            fix_hint="Install Python 3.12+: https://python.org/downloads",
        )

    def _check_api_key(self) -> DiagnosticResult:
        """Check that at least one LLM API key is set."""
        for var in API_KEY_ENV_VARS:
            value = os.environ.get(var)
            if value:
                masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
                return DiagnosticResult(
                    name="LLM API key",
                    passed=True,
                    message=f"{var} is set ({masked})",
                )
        env_list = ", ".join(API_KEY_ENV_VARS)
        return DiagnosticResult(
            name="LLM API key",
            passed=False,
            message="No LLM API key found in environment",
            fix_hint=f"Set one of: {env_list}",
        )

    def _check_optional_deps(self) -> list[DiagnosticResult]:
        """Check that optional dependencies are installed."""
        results: list[DiagnosticResult] = []
        for module, description in OPTIONAL_DEPENDENCIES.items():
            try:
                __import__(module)
                results.append(
                    DiagnosticResult(
                        name=description,
                        passed=True,
                        message="Installed",
                    )
                )
            except ImportError:
                pip_name = IMPORT_TO_PIP.get(module, module)
                results.append(
                    DiagnosticResult(
                        name=description,
                        passed=False,
                        message="Not installed",
                        fix_hint=f"pip install {pip_name}",
                        auto_fixable=True,
                        fix_action="install_package",
                    )
                )
        return results

    def _check_config(self, config_path: str) -> DiagnosticResult:
        """Check that the config file is valid YAML (if it exists)."""
        path = Path(config_path)
        if not path.exists():
            return DiagnosticResult(
                name="Configuration file",
                passed=True,
                message=f"No {config_path} found (using defaults)",
                fix_hint="Run 'intake doctor --fix' to create a default config.",
                auto_fixable=True,
                fix_action="create_config",
            )
        try:
            raw = path.read_text(encoding="utf-8")
            data = yaml.safe_load(raw)
            if not isinstance(data, dict):
                return DiagnosticResult(
                    name="Configuration file",
                    passed=False,
                    message=f"{config_path} is not a valid YAML mapping",
                    fix_hint="The config file should contain key: value pairs.",
                )
            return DiagnosticResult(
                name="Configuration file",
                passed=True,
                message=f"{config_path} is valid YAML",
            )
        except yaml.YAMLError as e:
            return DiagnosticResult(
                name="Configuration file",
                passed=False,
                message=f"Invalid YAML in {config_path}: {e}",
                fix_hint="Check YAML syntax and indentation.",
            )

    def _check_connectors(self, config_path: str) -> list[DiagnosticResult]:
        """Check connector credentials when connectors are configured.

        Only checks credentials for connectors that have non-default URLs
        or tokens configured in .intake.yaml.

        Args:
            config_path: Path to the config file.

        Returns:
            List of DiagnosticResult for each configured connector.
        """
        results: list[DiagnosticResult] = []
        path = Path(config_path)
        if not path.exists():
            return results

        try:
            raw = path.read_text(encoding="utf-8")
            data = yaml.safe_load(raw)
            if not isinstance(data, dict):
                return results
        except yaml.YAMLError:
            return results

        connectors = data.get("connectors", {})
        if not isinstance(connectors, dict):
            return results

        # Check Jira credentials
        jira_cfg = connectors.get("jira", {})
        if isinstance(jira_cfg, dict) and jira_cfg.get("url"):
            token_env = jira_cfg.get("token_env", "JIRA_API_TOKEN")
            email_env = jira_cfg.get("email_env", "JIRA_EMAIL")
            token_set = bool(os.environ.get(token_env))
            email_set = bool(os.environ.get(email_env))
            if token_set and email_set:
                results.append(
                    DiagnosticResult(
                        name="Jira connector",
                        passed=True,
                        message=f"Credentials set ({token_env}, {email_env})",
                    )
                )
            else:
                missing = []
                if not token_set:
                    missing.append(token_env)
                if not email_set:
                    missing.append(email_env)
                results.append(
                    DiagnosticResult(
                        name="Jira connector",
                        passed=False,
                        message=f"Missing credentials: {', '.join(missing)}",
                        fix_hint=f"Set environment variables: {', '.join(missing)}",
                    )
                )

        # Check Confluence credentials
        confluence_cfg = connectors.get("confluence", {})
        if isinstance(confluence_cfg, dict) and confluence_cfg.get("url"):
            token_env = confluence_cfg.get("token_env", "CONFLUENCE_API_TOKEN")
            email_env = confluence_cfg.get("email_env", "CONFLUENCE_EMAIL")
            token_set = bool(os.environ.get(token_env))
            email_set = bool(os.environ.get(email_env))
            if token_set and email_set:
                results.append(
                    DiagnosticResult(
                        name="Confluence connector",
                        passed=True,
                        message=f"Credentials set ({token_env}, {email_env})",
                    )
                )
            else:
                missing = []
                if not token_set:
                    missing.append(token_env)
                if not email_set:
                    missing.append(email_env)
                results.append(
                    DiagnosticResult(
                        name="Confluence connector",
                        passed=False,
                        message=f"Missing credentials: {', '.join(missing)}",
                        fix_hint=f"Set environment variables: {', '.join(missing)}",
                    )
                )

        # Check GitHub credentials
        github_cfg = connectors.get("github", {})
        if isinstance(github_cfg, dict):
            token_env = github_cfg.get("token_env", "GITHUB_TOKEN")
            if os.environ.get(token_env):
                results.append(
                    DiagnosticResult(
                        name="GitHub connector",
                        passed=True,
                        message=f"Token set ({token_env})",
                    )
                )
            elif github_cfg.get("token_env"):
                # Only warn if explicitly configured
                results.append(
                    DiagnosticResult(
                        name="GitHub connector",
                        passed=False,
                        message=f"Missing token: {token_env}",
                        fix_hint=f"Set environment variable: {token_env}",
                    )
                )

        # Check GitLab credentials
        gitlab_cfg = connectors.get("gitlab", {})
        if isinstance(gitlab_cfg, dict) and gitlab_cfg.get("url"):
            # Only check if URL is non-default (i.e. not just "https://gitlab.com")
            token_env = gitlab_cfg.get("token_env", "GITLAB_TOKEN")
            if os.environ.get(token_env):
                results.append(
                    DiagnosticResult(
                        name="GitLab connector",
                        passed=True,
                        message=f"Token set ({token_env})",
                    )
                )
            elif gitlab_cfg.get("token_env"):
                results.append(
                    DiagnosticResult(
                        name="GitLab connector",
                        passed=False,
                        message=f"Missing token: {token_env}",
                        fix_hint=(
                            f"Set environment variable: {token_env}. "
                            f"Create a personal access token with 'read_api' scope."
                        ),
                    )
                )

        return results

    def _fix_install_package(self, description: str) -> FixResult:
        """Attempt to install a missing Python package via pip.

        Args:
            description: The human-readable dependency description.

        Returns:
            FixResult indicating success or failure.
        """
        pip_name: str | None = None
        for module, desc in OPTIONAL_DEPENDENCIES.items():
            if desc == description:
                pip_name = IMPORT_TO_PIP.get(module, module)
                break

        if not pip_name:
            return FixResult(
                name=description,
                success=False,
                message=f"Could not determine pip package for '{description}'",
            )

        pip_cmd = self._find_pip()
        logger.info("installing_package", package=pip_name, pip=pip_cmd)

        try:
            proc = subprocess.run(
                [pip_cmd, "install", pip_name],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if proc.returncode == 0:
                return FixResult(
                    name=description,
                    success=True,
                    message=f"Installed {pip_name}",
                )
            return FixResult(
                name=description,
                success=False,
                message=f"pip install failed: {proc.stderr.strip()[:200]}",
            )
        except subprocess.TimeoutExpired:
            return FixResult(
                name=description,
                success=False,
                message=f"Installation of {pip_name} timed out (120s)",
            )
        except FileNotFoundError:
            return FixResult(
                name=description,
                success=False,
                message=f"pip not found at '{pip_cmd}'",
            )

    def _fix_create_config(self, config_path: str) -> FixResult:
        """Create a default .intake.yaml configuration file.

        Args:
            config_path: Path where the config should be created.

        Returns:
            FixResult indicating success or failure.
        """
        path = Path(config_path)
        if path.exists():
            return FixResult(
                name="Configuration file",
                success=False,
                message=f"{config_path} already exists",
            )

        try:
            path.write_text(_DEFAULT_CONFIG_TEMPLATE, encoding="utf-8")
            logger.info("config_created", path=config_path)
            return FixResult(
                name="Configuration file",
                success=True,
                message=f"Created {config_path} with defaults",
            )
        except OSError as e:
            return FixResult(
                name="Configuration file",
                success=False,
                message=f"Could not create {config_path}: {e}",
            )

    @staticmethod
    def _find_pip() -> str:
        """Find the best available pip command.

        Returns:
            The pip command string (e.g. 'pip3.12', 'pip3', 'pip').
        """
        for candidate in ["pip3.12", "pip3", "pip"]:
            if shutil.which(candidate):
                return candidate
        return "pip"
