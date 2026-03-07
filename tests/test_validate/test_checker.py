"""Tests for the spec validator (quality gate)."""

from __future__ import annotations

from pathlib import Path

import pytest

from intake.config.schema import ValidateConfig
from intake.validate.checker import SpecValidator

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def validator() -> SpecValidator:
    """Create a SpecValidator with default config."""
    return SpecValidator()


@pytest.fixture
def strict_validator() -> SpecValidator:
    """Create a SpecValidator in strict mode."""
    return SpecValidator(ValidateConfig(strict=True))


@pytest.fixture
def valid_spec_dir() -> str:
    """Path to the valid spec fixture."""
    return str(FIXTURES_DIR / "valid_spec")


@pytest.fixture
def broken_spec_dir() -> str:
    """Path to the broken spec fixture."""
    return str(FIXTURES_DIR / "broken_spec")


class TestStructureChecks:
    """Tests for required file structure validation."""

    def test_valid_spec_passes_structure(
        self, validator: SpecValidator, valid_spec_dir: str
    ) -> None:
        report = validator.validate(valid_spec_dir)
        structure_errors = [i for i in report.errors if i.category == "structure"]
        assert len(structure_errors) == 0

    def test_nonexistent_dir_reports_error(self, validator: SpecValidator) -> None:
        report = validator.validate("/nonexistent/path")
        assert not report.is_valid
        assert report.issues[0].category == "structure"
        assert "does not exist" in report.issues[0].message

    def test_missing_required_file_reports_error(
        self, validator: SpecValidator, tmp_path: Path
    ) -> None:
        # Create spec dir with only requirements.md
        (tmp_path / "requirements.md").write_text("# Reqs\n### FR-01: Test")
        report = validator.validate(str(tmp_path))
        structure_errors = [i for i in report.errors if i.category == "structure"]
        assert len(structure_errors) >= 1  # tasks.md and acceptance.yaml missing

    def test_empty_file_reports_error(self, validator: SpecValidator, tmp_path: Path) -> None:
        (tmp_path / "requirements.md").write_text("")
        (tmp_path / "tasks.md").write_text("# Tasks")
        (tmp_path / "acceptance.yaml").write_text("checks: []")
        report = validator.validate(str(tmp_path))
        empty_errors = [
            i for i in report.errors if "empty" in i.message.lower() and i.category == "structure"
        ]
        assert len(empty_errors) == 1

    def test_optional_files_generate_warnings(
        self, validator: SpecValidator, broken_spec_dir: str
    ) -> None:
        report = validator.validate(broken_spec_dir)
        optional_warnings = [
            i for i in report.warnings if i.category == "structure" and "Optional" in i.message
        ]
        assert len(optional_warnings) >= 1


class TestCrossReferences:
    """Tests for cross-reference validation."""

    def test_valid_spec_has_no_cross_ref_errors(
        self, validator: SpecValidator, valid_spec_dir: str
    ) -> None:
        report = validator.validate(valid_spec_dir)
        xref_errors = [i for i in report.errors if i.category == "cross_reference"]
        assert len(xref_errors) == 0

    def test_task_referencing_nonexistent_requirement(
        self, validator: SpecValidator, broken_spec_dir: str
    ) -> None:
        report = validator.validate(broken_spec_dir)
        xref_errors = [
            i for i in report.errors if i.category == "cross_reference" and "FR-99" in i.message
        ]
        assert len(xref_errors) >= 1

    def test_orphaned_requirement_generates_warning(
        self, validator: SpecValidator, broken_spec_dir: str
    ) -> None:
        report = validator.validate(broken_spec_dir)
        orphan_warnings = [
            i for i in report.warnings if i.category == "cross_reference" and "FR-05" in i.message
        ]
        assert len(orphan_warnings) >= 1


class TestConsistency:
    """Tests for task DAG consistency."""

    def test_valid_spec_has_sequential_ids(
        self, validator: SpecValidator, valid_spec_dir: str
    ) -> None:
        report = validator.validate(valid_spec_dir)
        gap_warnings = [
            i for i in report.warnings if i.category == "consistency" and "gaps" in i.message
        ]
        assert len(gap_warnings) == 0

    def test_circular_dependency_detected(
        self, validator: SpecValidator, broken_spec_dir: str
    ) -> None:
        report = validator.validate(broken_spec_dir)
        cycle_errors = [
            i for i in report.errors if i.category == "consistency" and "Circular" in i.message
        ]
        assert len(cycle_errors) >= 1

    def test_gap_in_task_ids_generates_warning(
        self, validator: SpecValidator, broken_spec_dir: str
    ) -> None:
        report = validator.validate(broken_spec_dir)
        gap_warnings = [
            i for i in report.warnings if i.category == "consistency" and "gaps" in i.message
        ]
        assert len(gap_warnings) >= 1


class TestAcceptanceValidity:
    """Tests for acceptance.yaml check validation."""

    def test_valid_acceptance_yaml(self, validator: SpecValidator, valid_spec_dir: str) -> None:
        report = validator.validate(valid_spec_dir)
        acceptance_errors = [i for i in report.errors if i.category == "acceptance"]
        assert len(acceptance_errors) == 0

    def test_missing_id_field(self, validator: SpecValidator, broken_spec_dir: str) -> None:
        report = validator.validate(broken_spec_dir)
        missing_id = [
            i for i in report.errors if i.category == "acceptance" and "missing 'id'" in i.message
        ]
        assert len(missing_id) >= 1

    def test_invalid_check_type(self, validator: SpecValidator, broken_spec_dir: str) -> None:
        report = validator.validate(broken_spec_dir)
        bad_type = [
            i for i in report.errors if i.category == "acceptance" and "invalid type" in i.message
        ]
        assert len(bad_type) >= 1

    def test_empty_command(self, validator: SpecValidator, broken_spec_dir: str) -> None:
        report = validator.validate(broken_spec_dir)
        empty_cmd = [
            i for i in report.errors if i.category == "acceptance" and "empty command" in i.message
        ]
        assert len(empty_cmd) >= 1

    def test_no_paths_in_files_exist(self, validator: SpecValidator, broken_spec_dir: str) -> None:
        report = validator.validate(broken_spec_dir)
        no_paths = [
            i for i in report.errors if i.category == "acceptance" and "no paths" in i.message
        ]
        assert len(no_paths) >= 1

    def test_invalid_regex_pattern(self, validator: SpecValidator, broken_spec_dir: str) -> None:
        report = validator.validate(broken_spec_dir)
        bad_regex = [
            i for i in report.errors if i.category == "acceptance" and "invalid regex" in i.message
        ]
        assert len(bad_regex) >= 1


class TestCompleteness:
    """Tests for completeness checks."""

    def test_valid_spec_all_fr_implemented(
        self, validator: SpecValidator, valid_spec_dir: str
    ) -> None:
        report = validator.validate(valid_spec_dir)
        unimpl = [
            i
            for i in report.warnings
            if i.category == "completeness" and "no implementing task" in i.message
        ]
        assert len(unimpl) == 0

    def test_unimplemented_fr_generates_warning(
        self, validator: SpecValidator, broken_spec_dir: str
    ) -> None:
        report = validator.validate(broken_spec_dir)
        unimpl = [
            i
            for i in report.warnings
            if i.category == "completeness" and "no implementing task" in i.message
        ]
        # FR-05 has no implementing task
        assert len(unimpl) >= 1


class TestReportProperties:
    """Tests for ValidationReport properties."""

    def test_valid_spec_is_valid(self, validator: SpecValidator, valid_spec_dir: str) -> None:
        report = validator.validate(valid_spec_dir)
        assert report.is_valid is True
        assert report.exit_code == 0

    def test_broken_spec_is_invalid(self, validator: SpecValidator, broken_spec_dir: str) -> None:
        report = validator.validate(broken_spec_dir)
        assert report.is_valid is False
        assert report.exit_code == 1

    def test_counts_populated(self, validator: SpecValidator, valid_spec_dir: str) -> None:
        report = validator.validate(valid_spec_dir)
        assert report.requirements_found > 0
        assert report.tasks_found > 0
        assert report.checks_found > 0

    def test_strict_mode_promotes_warnings(
        self, strict_validator: SpecValidator, broken_spec_dir: str
    ) -> None:
        report = strict_validator.validate(broken_spec_dir)
        # In strict mode, all warnings become errors
        assert len(report.warnings) == 0
        assert len(report.errors) > 0


class TestInvalidYaml:
    """Tests for invalid acceptance.yaml handling."""

    def test_invalid_yaml_reports_error(self, validator: SpecValidator, tmp_path: Path) -> None:
        (tmp_path / "requirements.md").write_text("# Reqs\n### FR-01: Test")
        (tmp_path / "tasks.md").write_text("# Tasks\n### Task 1: Test\nFR-01")
        (tmp_path / "acceptance.yaml").write_text("invalid: yaml: [broken: {")
        report = validator.validate(str(tmp_path))
        yaml_errors = [
            i for i in report.errors if i.category == "structure" and "Invalid YAML" in i.message
        ]
        assert len(yaml_errors) >= 1
