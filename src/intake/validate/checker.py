"""Spec internal consistency validator.

Runs offline — no LLM, no network, no subprocess. Pure Python parsing
and checks. Must complete in <1s for typical specs.

Checks five categories:
1. STRUCTURE: Required files exist and are non-empty.
2. CROSS-REFERENCES: Tasks reference valid requirements; acceptance checks
   reference valid requirements; every requirement is covered.
3. CONSISTENCY: Task DAG has no cycles; task IDs are sequential.
4. ACCEPTANCE: Check definitions are valid (type, command, regex).
5. COMPLETENESS: Functional requirements have implementing tasks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import structlog
import yaml

from intake.config.schema import ValidateConfig

logger = structlog.get_logger()


class ValidationError(Exception):
    """Base exception for validation errors."""


@dataclass
class ValidationIssue:
    """A single validation issue found in the spec.

    Attributes:
        severity: Error (blocks validation) or warning (advisory).
        category: Category of the check that found this issue.
        message: Human-readable description of the issue.
        file: Which spec file has the issue.
        item_id: Optional ID of the affected item (e.g. "FR-03").
        suggestion: Optional fix suggestion.
    """

    severity: Literal["error", "warning"]
    category: str
    message: str
    file: str
    item_id: str = ""
    suggestion: str = ""


@dataclass
class ValidationReport:
    """Result of spec validation.

    Attributes:
        spec_dir: Path to the validated spec directory.
        issues: List of all issues found.
        files_checked: Number of files inspected.
        requirements_found: Number of requirement IDs found.
        tasks_found: Number of task IDs found.
        checks_found: Number of acceptance check IDs found.
    """

    spec_dir: str
    issues: list[ValidationIssue] = field(default_factory=list)
    files_checked: int = 0
    requirements_found: int = 0
    tasks_found: int = 0
    checks_found: int = 0

    @property
    def errors(self) -> list[ValidationIssue]:
        """All error-severity issues."""
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """All warning-severity issues."""
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def is_valid(self) -> bool:
        """True if no errors were found."""
        return len(self.errors) == 0

    @property
    def exit_code(self) -> int:
        """Exit code for CLI: 0=valid, 1=errors found."""
        return 0 if self.is_valid else 1


# Regex patterns for ID extraction.
_REQUIREMENT_ID_PATTERN: re.Pattern[str] = re.compile(r"\b((?:FR|NFR)-\d+)\b")
_TASK_HEADER_PATTERN: re.Pattern[str] = re.compile(
    r"###?\s+(?:Task\s+)?(\d+)[:\.\s]+(.+?)(?=\n###?\s|\Z)",
    re.DOTALL,
)
_DEPENDENCY_PATTERN: re.Pattern[str] = re.compile(
    r"(?:depends?\s+on|after|requires)\s+(?:task\s+)?(\d+)",
    re.IGNORECASE,
)

# Valid acceptance check types.
VALID_CHECK_TYPES = frozenset({"command", "files_exist", "pattern_present", "pattern_absent"})


class SpecValidator:
    """Validates internal consistency of a generated spec.

    Runs all checks synchronously and returns a ValidationReport.
    100% offline — no network, no LLM, no subprocess.
    """

    def __init__(self, config: ValidateConfig | None = None) -> None:
        self.config = config or ValidateConfig()

    def validate(self, spec_dir: str) -> ValidationReport:
        """Run all validation checks on a spec directory.

        Args:
            spec_dir: Path to the spec directory to validate.

        Returns:
            ValidationReport with all issues found.
        """
        path = Path(spec_dir)
        report = ValidationReport(spec_dir=spec_dir)

        if not path.exists() or not path.is_dir():
            report.issues.append(
                ValidationIssue(
                    severity="error",
                    category="structure",
                    message=f"Spec directory does not exist: {spec_dir}",
                    file=spec_dir,
                )
            )
            return report

        # 1. Structure checks
        self._check_structure(path, report)

        # 2. Parse all IDs
        requirement_ids = self._extract_requirement_ids(path, report)
        task_ids, task_deps, task_req_refs = self._extract_task_info(path, report)
        check_ids, check_req_refs = self._extract_check_info(path, report)

        report.requirements_found = len(requirement_ids)
        report.tasks_found = len(task_ids)
        report.checks_found = len(check_ids)

        # 3. Cross-reference checks
        self._check_cross_references(
            requirement_ids,
            task_ids,
            task_deps,
            task_req_refs,
            check_req_refs,
            report,
        )

        # 4. Consistency checks
        self._check_consistency(task_ids, task_deps, report)

        # 5. Acceptance checks validation
        self._check_acceptance_validity(path, report)

        # 6. Completeness checks
        self._check_completeness(requirement_ids, task_req_refs, report)

        # Apply strict mode: warnings become errors
        if self.config.strict:
            for issue in report.issues:
                if issue.severity == "warning":
                    issue.severity = "error"

        logger.info(
            "spec_validation_complete",
            spec_dir=spec_dir,
            errors=len(report.errors),
            warnings=len(report.warnings),
            valid=report.is_valid,
        )

        return report

    def _check_structure(self, path: Path, report: ValidationReport) -> None:
        """Check that required files exist and are non-empty."""
        for fname in self.config.required_sections:
            fpath = path / fname
            if not fpath.exists():
                report.issues.append(
                    ValidationIssue(
                        severity="error",
                        category="structure",
                        message=f"Required file missing: {fname}",
                        file=fname,
                        suggestion=(
                            f"Run 'intake regenerate {path} --only "
                            f"{fname.split('.')[0]}' to regenerate."
                        ),
                    )
                )
            elif fpath.stat().st_size == 0:
                report.issues.append(
                    ValidationIssue(
                        severity="error",
                        category="structure",
                        message=f"File is empty: {fname}",
                        file=fname,
                    )
                )
            report.files_checked += 1

        # Check optional files
        for fname in ["design.md", "context.md", "sources.md"]:
            fpath = path / fname
            if not fpath.exists():
                report.issues.append(
                    ValidationIssue(
                        severity="warning",
                        category="structure",
                        message=f"Optional file missing: {fname}",
                        file=fname,
                    )
                )

    def _extract_requirement_ids(self, path: Path, report: ValidationReport) -> set[str]:
        """Extract all FR-XX and NFR-XX IDs from requirements.md."""
        reqs_file = path / "requirements.md"
        if not reqs_file.exists():
            return set()

        content = reqs_file.read_text(errors="ignore")
        ids = set(_REQUIREMENT_ID_PATTERN.findall(content))

        if not ids:
            report.issues.append(
                ValidationIssue(
                    severity="warning",
                    category="completeness",
                    message="No requirement IDs (FR-XX/NFR-XX) found in requirements.md",
                    file="requirements.md",
                    suggestion="Requirements should use IDs like FR-01, NFR-01.",
                )
            )

        return ids

    def _extract_task_info(
        self, path: Path, report: ValidationReport
    ) -> tuple[set[str], dict[str, list[str]], dict[str, set[str]]]:
        """Extract task IDs, dependencies, and requirement references.

        Returns:
            Tuple of (task_ids, task_deps, task_req_refs).
        """
        tasks_file = path / "tasks.md"
        task_ids: set[str] = set()
        task_deps: dict[str, list[str]] = {}
        task_req_refs: dict[str, set[str]] = {}

        if not tasks_file.exists():
            return task_ids, task_deps, task_req_refs

        content = tasks_file.read_text(errors="ignore")

        for match in _TASK_HEADER_PATTERN.finditer(content):
            tid = match.group(1)
            body = match.group(2)
            task_ids.add(tid)

            # Find dependency references
            dep_matches = _DEPENDENCY_PATTERN.findall(body)
            task_deps[tid] = dep_matches

            # Find requirement references
            req_refs = set(_REQUIREMENT_ID_PATTERN.findall(body))
            task_req_refs[tid] = req_refs

        return task_ids, task_deps, task_req_refs

    def _extract_check_info(
        self, path: Path, report: ValidationReport
    ) -> tuple[set[str], dict[str, set[str]]]:
        """Extract check IDs and their requirement references from acceptance.yaml.

        Returns:
            Tuple of (check_ids, check_req_refs).
        """
        accept_file = path / "acceptance.yaml"
        check_ids: set[str] = set()
        check_req_refs: dict[str, set[str]] = {}

        if not accept_file.exists():
            return check_ids, check_req_refs

        try:
            with open(accept_file, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            report.issues.append(
                ValidationIssue(
                    severity="error",
                    category="structure",
                    message=f"Invalid YAML in acceptance.yaml: {e}",
                    file="acceptance.yaml",
                )
            )
            return check_ids, check_req_refs

        if not isinstance(data, dict):
            return check_ids, check_req_refs

        for check in data.get("checks", []):
            if not isinstance(check, dict):
                continue
            cid = check.get("id", "")
            if cid:
                check_ids.add(cid)

            # Extract requirement refs from check name/tags
            name = check.get("name", "")
            tags = check.get("tags", [])
            tag_str = " ".join(tags) if isinstance(tags, list) else ""
            refs = set(_REQUIREMENT_ID_PATTERN.findall(f"{name} {tag_str}"))
            check_req_refs[cid] = refs

        return check_ids, check_req_refs

    def _check_cross_references(
        self,
        requirement_ids: set[str],
        task_ids: set[str],
        task_deps: dict[str, list[str]],
        task_req_refs: dict[str, set[str]],
        check_req_refs: dict[str, set[str]],
        report: ValidationReport,
    ) -> None:
        """Verify cross-references between spec files."""
        # Tasks referencing non-existent requirements
        for tid, refs in task_req_refs.items():
            for ref in refs:
                if ref not in requirement_ids:
                    report.issues.append(
                        ValidationIssue(
                            severity="error",
                            category="cross_reference",
                            message=(
                                f"Task {tid} references {ref}, which does not "
                                f"exist in requirements.md"
                            ),
                            file="tasks.md",
                            item_id=f"Task {tid}",
                            suggestion=(
                                f"Add {ref} to requirements.md or remove "
                                f"the reference from task {tid}."
                            ),
                        )
                    )

        # Tasks with non-existent dependencies
        for tid, deps in task_deps.items():
            for dep in deps:
                if dep not in task_ids:
                    report.issues.append(
                        ValidationIssue(
                            severity="error",
                            category="cross_reference",
                            message=(f"Task {tid} depends on task {dep}, which does not exist"),
                            file="tasks.md",
                            item_id=f"Task {tid}",
                        )
                    )

        # Acceptance checks referencing non-existent requirements
        for cid, refs in check_req_refs.items():
            for ref in refs:
                if ref not in requirement_ids:
                    report.issues.append(
                        ValidationIssue(
                            severity="error",
                            category="cross_reference",
                            message=(
                                f"Check {cid} references {ref}, which does not "
                                f"exist in requirements.md"
                            ),
                            file="acceptance.yaml",
                            item_id=f"Check {cid}",
                            suggestion=(
                                f"Add {ref} to requirements.md or remove "
                                f"the reference from check {cid}."
                            ),
                        )
                    )

        # Orphaned requirements (not referenced by any task or check)
        all_referenced: set[str] = set()
        for refs in task_req_refs.values():
            all_referenced.update(refs)
        for refs in check_req_refs.values():
            all_referenced.update(refs)

        orphaned = requirement_ids - all_referenced
        if len(orphaned) > self.config.max_orphaned_requirements:
            for req_id in sorted(orphaned):
                report.issues.append(
                    ValidationIssue(
                        severity="warning",
                        category="cross_reference",
                        message=(
                            f"Requirement {req_id} is not referenced by any "
                            f"task or acceptance check"
                        ),
                        file="requirements.md",
                        item_id=req_id,
                        suggestion=(
                            f"Add a task that implements {req_id}, or "
                            f"remove it if it is no longer needed."
                        ),
                    )
                )

    def _check_consistency(
        self,
        task_ids: set[str],
        task_deps: dict[str, list[str]],
        report: ValidationReport,
    ) -> None:
        """Check task DAG for cycles and sequential IDs."""
        # Check for cycles using DFS
        visited: set[str] = set()
        in_stack: set[str] = set()

        def _has_cycle(node: str) -> bool:
            if node in in_stack:
                return True
            if node in visited:
                return False
            visited.add(node)
            in_stack.add(node)
            for dep in task_deps.get(node, []):
                if _has_cycle(dep):
                    return True
            in_stack.discard(node)
            return False

        for tid in sorted(task_ids):
            if _has_cycle(tid):
                report.issues.append(
                    ValidationIssue(
                        severity="error",
                        category="consistency",
                        message=f"Circular dependency detected involving task {tid}",
                        file="tasks.md",
                        item_id=f"Task {tid}",
                        suggestion="Review task dependencies and break the cycle.",
                    )
                )
                break  # One cycle error is enough

        # Check sequential IDs
        if task_ids:
            numeric_ids = sorted(int(t) for t in task_ids if t.isdigit())
            if numeric_ids:
                expected = set(range(1, max(numeric_ids) + 1))
                missing = expected - set(numeric_ids)
                if missing:
                    report.issues.append(
                        ValidationIssue(
                            severity="warning",
                            category="consistency",
                            message=f"Task IDs have gaps: missing {sorted(missing)}",
                            file="tasks.md",
                        )
                    )

    def _check_acceptance_validity(self, path: Path, report: ValidationReport) -> None:
        """Validate acceptance.yaml check definitions."""
        accept_file = path / "acceptance.yaml"
        if not accept_file.exists():
            return

        try:
            with open(accept_file, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError:
            return  # Already reported in _extract_check_info

        if not isinstance(data, dict):
            return

        for i, check in enumerate(data.get("checks", [])):
            if not isinstance(check, dict):
                continue
            cid = check.get("id", f"check-{i}")

            if "id" not in check:
                report.issues.append(
                    ValidationIssue(
                        severity="error",
                        category="acceptance",
                        message=f"Check at index {i} is missing 'id' field",
                        file="acceptance.yaml",
                    )
                )

            check_type = check.get("type", "command")
            if check_type not in VALID_CHECK_TYPES:
                report.issues.append(
                    ValidationIssue(
                        severity="error",
                        category="acceptance",
                        message=(
                            f"Check '{cid}' has invalid type '{check_type}'. "
                            f"Valid: {sorted(VALID_CHECK_TYPES)}"
                        ),
                        file="acceptance.yaml",
                        item_id=cid,
                    )
                )

            if check_type == "command" and not check.get("command"):
                report.issues.append(
                    ValidationIssue(
                        severity="error",
                        category="acceptance",
                        message=f"Check '{cid}' (type: command) has empty command",
                        file="acceptance.yaml",
                        item_id=cid,
                    )
                )

            if check_type == "files_exist":
                paths = check.get("paths", [])
                if not paths:
                    report.issues.append(
                        ValidationIssue(
                            severity="error",
                            category="acceptance",
                            message=f"Check '{cid}' (type: files_exist) has no paths",
                            file="acceptance.yaml",
                            item_id=cid,
                        )
                    )

            if check_type in ("pattern_present", "pattern_absent"):
                patterns = check.get("patterns", [])
                if isinstance(patterns, list):
                    for pattern in patterns:
                        try:
                            re.compile(pattern)
                        except re.error as e:
                            report.issues.append(
                                ValidationIssue(
                                    severity="error",
                                    category="acceptance",
                                    message=(f"Check '{cid}' has invalid regex '{pattern}': {e}"),
                                    file="acceptance.yaml",
                                    item_id=cid,
                                )
                            )

    def _check_completeness(
        self,
        requirement_ids: set[str],
        task_req_refs: dict[str, set[str]],
        report: ValidationReport,
    ) -> None:
        """Check that functional requirements have implementing tasks."""
        functional_ids = {r for r in requirement_ids if r.startswith("FR-")}
        referenced_by_tasks: set[str] = set()
        for refs in task_req_refs.values():
            referenced_by_tasks.update(refs)

        unimplemented = functional_ids - referenced_by_tasks
        for req_id in sorted(unimplemented):
            report.issues.append(
                ValidationIssue(
                    severity="warning",
                    category="completeness",
                    message=f"Functional requirement {req_id} has no implementing task",
                    file="requirements.md",
                    item_id=req_id,
                    suggestion=(
                        f"Add a task for {req_id} in tasks.md, or mark it as out of scope."
                    ),
                )
            )
