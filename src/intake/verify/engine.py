"""Verification engine for acceptance checks.

Runs checks defined in acceptance.yaml against a project directory.
Supports 4 check types: command, files_exist, pattern_present, pattern_absent.
"""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

import structlog
import yaml

logger = structlog.get_logger()


class VerifyError(Exception):
    """Error during verification execution."""

    def __init__(self, reason: str, suggestion: str = "") -> None:
        self.reason = reason
        self.suggestion = suggestion
        msg = f"Verification failed: {reason}"
        if suggestion:
            msg += f"\n  Hint: {suggestion}"
        super().__init__(msg)


@dataclass
class CheckResult:
    """Result of executing a single acceptance check."""

    id: str
    name: str
    passed: bool
    required: bool
    output: str = ""
    error: str = ""
    duration_ms: int = 0


@dataclass
class VerificationReport:
    """Aggregated results of running all acceptance checks."""

    spec_name: str
    total_checks: int
    passed: int
    failed: int
    skipped: int
    results: list[CheckResult] = field(default_factory=list)
    all_required_passed: bool = True

    @property
    def exit_code(self) -> int:
        """Semantic exit code: 0 = success, 1 = required check failed."""
        if self.all_required_passed:
            return 0
        return 1


class VerificationEngine:
    """Runs acceptance.yaml checks against a project.

    Supported check types:
    - command: run a shell command and validate exit code is 0
    - files_exist: verify that listed file paths exist
    - pattern_present: verify regex patterns exist in files matching a glob
    - pattern_absent: verify regex patterns do NOT exist in files matching a glob
    """

    def __init__(self, project_dir: str, timeout_per_check: int = 120) -> None:
        self.project_dir = Path(project_dir)
        self.timeout_per_check = timeout_per_check

    def run(
        self,
        acceptance_file: str,
        tags: list[str] | None = None,
        fail_fast: bool = False,
    ) -> VerificationReport:
        """Run all checks and produce a report.

        Args:
            acceptance_file: Path to the acceptance.yaml file.
            tags: Only run checks that have at least one of these tags.
            fail_fast: Stop at the first failing required check.

        Returns:
            VerificationReport with all results.

        Raises:
            VerifyError: If the acceptance file cannot be loaded.
        """
        checks = self._load_checks(acceptance_file)
        total_count = len(checks)

        if tags:

            def _has_matching_tag(c: dict[str, object]) -> bool:
                check_tags = c.get("tags", [])
                if not isinstance(check_tags, list):
                    return False
                return any(t in check_tags for t in tags)

            checks = [c for c in checks if _has_matching_tag(c)]

        results: list[CheckResult] = []

        for check in checks:
            result = self._run_check(check)
            results.append(result)

            status = "PASS" if result.passed else "FAIL"
            logger.info(
                "check_result",
                id=result.id,
                name=result.name,
                status=status,
                required=result.required,
                duration_ms=result.duration_ms,
            )

            if fail_fast and not result.passed and result.required:
                break

        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed)
        skipped = total_count - len(results)
        all_required = all(r.passed for r in results if r.required)

        report = VerificationReport(
            spec_name=Path(acceptance_file).parent.name,
            total_checks=total_count,
            passed=passed,
            failed=failed,
            skipped=skipped,
            results=results,
            all_required_passed=all_required,
        )

        logger.info(
            "verification_complete",
            spec=report.spec_name,
            passed=passed,
            failed=failed,
            skipped=skipped,
            exit_code=report.exit_code,
        )

        return report

    def _load_checks(self, path: str) -> list[dict[str, object]]:
        """Load and validate acceptance checks from YAML.

        Args:
            path: Path to the acceptance.yaml file.

        Returns:
            List of check definitions.

        Raises:
            VerifyError: If the file cannot be read or parsed.
        """
        acceptance_path = Path(path)
        if not acceptance_path.exists():
            raise VerifyError(
                reason=f"Acceptance file not found: {path}",
                suggestion="Run 'intake init' to generate acceptance.yaml first.",
            )

        try:
            with open(acceptance_path) as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise VerifyError(
                reason=f"Invalid YAML in {path}: {e}",
                suggestion="Check acceptance.yaml syntax.",
            ) from e

        if not isinstance(data, dict):
            raise VerifyError(
                reason=f"Expected a mapping in {path}, got {type(data).__name__}",
                suggestion="acceptance.yaml should have a top-level 'checks' key.",
            )

        checks = data.get("checks", [])
        if not isinstance(checks, list):
            raise VerifyError(
                reason="'checks' must be a list in acceptance.yaml",
                suggestion="Each check should be a mapping with id, name, type, etc.",
            )

        return checks

    def _run_check(self, check: dict[str, object]) -> CheckResult:
        """Execute a single check and return its result.

        Args:
            check: Check definition from acceptance.yaml.

        Returns:
            CheckResult with pass/fail status and output.
        """
        check_type = str(check.get("type", "command"))
        check_id = str(check.get("id", "unknown"))
        check_name = str(check.get("name", check_id))
        required = bool(check.get("required", True))

        start = time.monotonic()

        try:
            if check_type == "command":
                command = check.get("command", "")
                if not command:
                    passed, output = False, "No command specified"
                else:
                    passed, output = self._check_command(str(command))
            elif check_type == "files_exist":
                paths = check.get("paths", [])
                if not isinstance(paths, list):
                    paths = [str(paths)]
                passed, output = self._check_files_exist([str(p) for p in paths])
            elif check_type == "pattern_present":
                raw_pats = check.get("patterns", [])
                pat_list = [str(p) for p in raw_pats] if isinstance(raw_pats, list) else []
                passed, output = self._check_pattern(
                    glob_pattern=str(check.get("glob", "")),
                    patterns=pat_list,
                    present=True,
                )
            elif check_type == "pattern_absent":
                raw_pats = check.get("patterns", [])
                pat_list = [str(p) for p in raw_pats] if isinstance(raw_pats, list) else []
                passed, output = self._check_pattern(
                    glob_pattern=str(check.get("glob", "")),
                    patterns=pat_list,
                    present=False,
                )
            else:
                passed, output = False, f"Unknown check type: {check_type}"

            duration = int((time.monotonic() - start) * 1000)
            return CheckResult(
                id=check_id,
                name=check_name,
                passed=passed,
                required=required,
                output=output,
                duration_ms=duration,
            )
        except subprocess.TimeoutExpired:
            duration = int((time.monotonic() - start) * 1000)
            return CheckResult(
                id=check_id,
                name=check_name,
                passed=False,
                required=required,
                error=f"Check timed out after {self.timeout_per_check}s",
                duration_ms=duration,
            )
        except Exception as e:
            duration = int((time.monotonic() - start) * 1000)
            return CheckResult(
                id=check_id,
                name=check_name,
                passed=False,
                required=required,
                error=str(e),
                duration_ms=duration,
            )

    def _check_command(self, command: str) -> tuple[bool, str]:
        """Run a shell command and check exit code.

        Args:
            command: Shell command string to execute.

        Returns:
            Tuple of (passed, output_summary).
        """
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=self.timeout_per_check,
            cwd=str(self.project_dir),
        )
        # Truncate output to avoid excessive memory usage
        stdout = result.stdout[-1000:] if result.stdout else ""
        stderr = result.stderr[-500:] if result.stderr else ""
        output = stdout
        if stderr:
            output += f"\n--- stderr ---\n{stderr}"
        return result.returncode == 0, output.strip()

    def _check_files_exist(self, paths: list[str]) -> tuple[bool, str]:
        """Check that all listed file paths exist.

        Args:
            paths: List of relative file paths to check.

        Returns:
            Tuple of (all_exist, description).
        """
        if not paths:
            return False, "No paths specified"

        missing = [p for p in paths if not (self.project_dir / p).exists()]
        if missing:
            return False, f"Missing files: {', '.join(missing)}"
        return True, f"All {len(paths)} file(s) exist"

    def _check_pattern(
        self,
        glob_pattern: str,
        patterns: list[str],
        present: bool,
    ) -> tuple[bool, str]:
        """Check that regex patterns are present/absent in files matching a glob.

        Args:
            glob_pattern: Glob pattern to find files (e.g., "src/**/*.py").
            patterns: List of regex patterns to search for.
            present: If True, patterns must be found. If False, they must be absent.

        Returns:
            Tuple of (passed, description).
        """
        if not glob_pattern:
            return False, "No glob pattern specified"
        if not patterns:
            return False, "No patterns specified"

        files = list(self.project_dir.glob(glob_pattern))
        if not files:
            return False, f"No files matching '{glob_pattern}'"

        for file in files:
            if not file.is_file():
                continue
            try:
                content = file.read_text(errors="ignore")
            except OSError as e:
                logger.warning("file_read_skipped", file=str(file), error=str(e))
                continue

            for pattern in patterns:
                found = bool(re.search(pattern, content, re.IGNORECASE))
                if present and not found:
                    rel_path = file.relative_to(self.project_dir)
                    return False, f"Pattern '{pattern}' not found in {rel_path}"
                if not present and found:
                    rel_path = file.relative_to(self.project_dir)
                    return False, f"Forbidden pattern '{pattern}' found in {rel_path}"

        action = "present" if present else "absent"
        return True, f"All patterns {action} as expected in {len(files)} file(s)"
