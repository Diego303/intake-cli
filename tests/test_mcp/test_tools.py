"""Tests for MCP tools (without requiring the mcp package)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


@pytest.fixture()
def spec_dir(tmp_path: Path) -> Path:
    """Create a minimal spec directory for testing."""
    spec = tmp_path / "specs" / "test-spec"
    spec.mkdir(parents=True)

    (spec / "requirements.md").write_text(
        "# Requirements\n\n"
        "## FR-01: User login\n\n"
        "The system shall support email/password login.\n\n"
        "## FR-02: Password reset\n\n"
        "The system shall support password reset via email.\n"
    )
    (spec / "tasks.md").write_text(
        "# Tasks\n\n"
        "## Task 1: Implement login\n\n"
        "Implement the login endpoint.\n\n"
        "**Status:** pending\n\n"
        "## Task 2: Implement reset\n\n"
        "Implement password reset.\n\n"
        "**Status:** in_progress\n\n"
        "## Task 3: Add tests\n\n"
        "Write integration tests.\n\n"
        "**Status:** done\n"
    )
    (spec / "context.md").write_text("# Context\n\nTech stack: Python, FastAPI, PostgreSQL\n")
    (spec / "design.md").write_text("# Design\n\nREST API with JWT auth.\n")
    (spec / "acceptance.yaml").write_text(
        yaml.dump(
            {
                "checks": [
                    {
                        "id": "check-1",
                        "name": "files exist",
                        "type": "files_exist",
                        "paths": ["README.md"],
                        "required": True,
                    },
                    {
                        "id": "check-2",
                        "name": "src exists",
                        "type": "files_exist",
                        "paths": ["src/"],
                        "required": False,
                        "tags": ["build"],
                    },
                ]
            }
        )
    )
    (spec / "sources.md").write_text("# Sources\n\n- requirements.md\n")

    return tmp_path / "specs"


class TestHandleShow:
    """Tests for _handle_show."""

    def test_show_existing_spec(self, spec_dir: Path) -> None:
        from intake.mcp.tools import _handle_show

        result = _handle_show(str(spec_dir), "test-spec")
        assert "# Spec: test-spec" in result
        assert "requirements.md" in result
        assert "tasks.md" in result
        assert "context.md" in result

    def test_show_includes_design(self, spec_dir: Path) -> None:
        from intake.mcp.tools import _handle_show

        result = _handle_show(str(spec_dir), "test-spec")
        assert "design.md" in result
        assert "JWT auth" in result

    def test_show_nonexistent_spec(self, spec_dir: Path) -> None:
        from intake.mcp.tools import _handle_show

        result = _handle_show(str(spec_dir), "nonexistent")
        assert "not found" in result

    def test_show_truncates_large_content(self, spec_dir: Path) -> None:
        from intake.mcp.tools import MAX_SECTION_LENGTH, _handle_show

        # Write a large file
        large_content = "x" * (MAX_SECTION_LENGTH + 500)
        (spec_dir / "test-spec" / "requirements.md").write_text(large_content)

        result = _handle_show(str(spec_dir), "test-spec")
        # The content should be truncated to MAX_SECTION_LENGTH
        assert len(result) < len(large_content) + 500


class TestHandleGetContext:
    """Tests for _handle_get_context."""

    def test_get_context_existing(self, spec_dir: Path) -> None:
        from intake.mcp.tools import _handle_get_context

        result = _handle_get_context(str(spec_dir), "test-spec")
        assert "Python, FastAPI" in result

    def test_get_context_missing(self, spec_dir: Path) -> None:
        from intake.mcp.tools import _handle_get_context

        result = _handle_get_context(str(spec_dir), "nonexistent")
        assert "No context.md found" in result


class TestHandleGetTasks:
    """Tests for _handle_get_tasks."""

    def test_get_all_tasks(self, spec_dir: Path) -> None:
        from intake.mcp.tools import _handle_get_tasks

        result = _handle_get_tasks(str(spec_dir), "test-spec", "all")
        assert "Task 1" in result
        assert "Task 2" in result
        assert "Task 3" in result

    def test_get_tasks_filtered_by_pending(self, spec_dir: Path) -> None:
        from intake.mcp.tools import _handle_get_tasks

        result = _handle_get_tasks(str(spec_dir), "test-spec", "pending")
        assert "pending" in result.lower()

    def test_get_tasks_filtered_by_done(self, spec_dir: Path) -> None:
        from intake.mcp.tools import _handle_get_tasks

        result = _handle_get_tasks(str(spec_dir), "test-spec", "done")
        assert "done" in result.lower()

    def test_get_tasks_filtered_by_in_progress(self, spec_dir: Path) -> None:
        from intake.mcp.tools import _handle_get_tasks

        result = _handle_get_tasks(str(spec_dir), "test-spec", "in_progress")
        assert "in_progress" in result.lower()

    def test_get_tasks_filtered_nonexistent_status(self, spec_dir: Path) -> None:
        from intake.mcp.tools import _handle_get_tasks

        result = _handle_get_tasks(str(spec_dir), "test-spec", "blocked")
        # Should either have no results or say no tasks found
        assert "blocked" in result.lower() or "no tasks" in result.lower()

    def test_get_tasks_missing_spec(self, spec_dir: Path) -> None:
        from intake.mcp.tools import _handle_get_tasks

        result = _handle_get_tasks(str(spec_dir), "nonexistent", "all")
        assert "No tasks.md found" in result


class TestHandleUpdateTask:
    """Tests for _handle_update_task."""

    def test_update_task_success(self, spec_dir: Path) -> None:
        from intake.mcp.tools import _handle_update_task

        result = _handle_update_task(str(spec_dir), "test-spec", "1", "in_progress", "")
        assert "updated" in result.lower()

    def test_update_task_invalid_id(self, spec_dir: Path) -> None:
        from intake.mcp.tools import _handle_update_task

        result = _handle_update_task(str(spec_dir), "test-spec", "not-a-number", "done", "")
        assert "Invalid task ID" in result

    def test_update_task_missing_spec(self, spec_dir: Path) -> None:
        from intake.mcp.tools import _handle_update_task

        result = _handle_update_task(str(spec_dir), "nonexistent", "1", "done", "")
        assert "No tasks.md found" in result

    def test_update_task_with_note(self, spec_dir: Path) -> None:
        from intake.mcp.tools import _handle_update_task

        result = _handle_update_task(
            str(spec_dir), "test-spec", "1", "done", "Completed with tests"
        )
        assert "updated" in result.lower()

    def test_update_task_nonexistent_task_id(self, spec_dir: Path) -> None:
        from intake.mcp.tools import _handle_update_task

        result = _handle_update_task(str(spec_dir), "test-spec", "999", "done", "")
        # Should fail since task 999 doesn't exist
        assert "999" in result


class TestHandleVerify:
    """Tests for _handle_verify."""

    def test_verify_runs_checks(self, spec_dir: Path, tmp_path: Path) -> None:
        from intake.mcp.tools import _handle_verify

        # Create the required file so the check passes
        project = tmp_path / "project"
        project.mkdir()
        (project / "README.md").write_text("# Hello")

        result = _handle_verify(str(spec_dir), str(project), "test-spec", None)
        assert "Verification:" in result
        assert "passed" in result

    def test_verify_failing_check(self, spec_dir: Path, tmp_path: Path) -> None:
        from intake.mcp.tools import _handle_verify

        # Don't create README.md, so the check fails
        project = tmp_path / "empty-project"
        project.mkdir()

        result = _handle_verify(str(spec_dir), str(project), "test-spec", None)
        assert "FAIL" in result

    def test_verify_missing_acceptance(self, spec_dir: Path) -> None:
        from intake.mcp.tools import _handle_verify

        result = _handle_verify(str(spec_dir), ".", "nonexistent", None)
        assert "error" in result.lower() or "not found" in result.lower()

    def test_verify_with_tags(self, spec_dir: Path, tmp_path: Path) -> None:
        from intake.mcp.tools import _handle_verify

        project = tmp_path / "project-tags"
        project.mkdir()
        (project / "README.md").write_text("# Hello")

        result = _handle_verify(str(spec_dir), str(project), "test-spec", ["build"])
        assert "Verification:" in result

    def test_verify_with_nonexistent_tag(self, spec_dir: Path, tmp_path: Path) -> None:
        from intake.mcp.tools import _handle_verify

        project = tmp_path / "project-notag"
        project.mkdir()

        result = _handle_verify(str(spec_dir), str(project), "test-spec", ["nonexistent-tag"])
        assert "Verification:" in result


class TestHandleListSpecs:
    """Tests for _handle_list_specs."""

    def test_list_specs_with_specs(self, spec_dir: Path) -> None:
        from intake.mcp.tools import _handle_list_specs

        result = _handle_list_specs(str(spec_dir))
        assert "test-spec" in result

    def test_list_specs_empty_dir(self, tmp_path: Path) -> None:
        from intake.mcp.tools import _handle_list_specs

        empty = tmp_path / "empty-specs"
        empty.mkdir()
        result = _handle_list_specs(str(empty))
        assert "No specs found" in result

    def test_list_specs_missing_dir(self) -> None:
        from intake.mcp.tools import _handle_list_specs

        result = _handle_list_specs("/nonexistent/path")
        assert "not found" in result

    def test_list_specs_multiple(self, spec_dir: Path) -> None:
        from intake.mcp.tools import _handle_list_specs

        # Create a second spec
        spec2 = spec_dir / "another-spec"
        spec2.mkdir()
        (spec2 / "requirements.md").write_text("# Requirements\n")

        result = _handle_list_specs(str(spec_dir))
        assert "test-spec" in result
        assert "another-spec" in result

    def test_list_specs_ignores_dirs_without_requirements(self, spec_dir: Path) -> None:
        from intake.mcp.tools import _handle_list_specs

        # Create a dir without requirements.md
        (spec_dir / "not-a-spec").mkdir()

        result = _handle_list_specs(str(spec_dir))
        assert "not-a-spec" not in result
        assert "test-spec" in result


class TestHandleFeedback:
    """Tests for _handle_feedback."""

    @pytest.mark.asyncio
    async def test_feedback_returns_verify_results(self, spec_dir: Path, tmp_path: Path) -> None:
        from intake.mcp.tools import _handle_feedback

        project = tmp_path / "project2"
        project.mkdir()

        result = await _handle_feedback(str(spec_dir), str(project), "test-spec")
        assert "Verification:" in result
        assert "intake feedback" in result

    @pytest.mark.asyncio
    async def test_feedback_with_passing_checks(self, spec_dir: Path, tmp_path: Path) -> None:
        from intake.mcp.tools import _handle_feedback

        project = tmp_path / "project-pass"
        project.mkdir()
        (project / "README.md").write_text("# Test")

        result = await _handle_feedback(str(spec_dir), str(project), "test-spec")
        assert "Verification:" in result
        assert "passed" in result


class TestConstants:
    """Tests for module-level constants."""

    def test_spec_files_tuple(self) -> None:
        from intake.mcp.tools import SPEC_FILES

        assert "requirements.md" in SPEC_FILES
        assert "tasks.md" in SPEC_FILES
        assert "context.md" in SPEC_FILES
        assert "design.md" in SPEC_FILES

    def test_max_section_length(self) -> None:
        from intake.mcp.tools import MAX_SECTION_LENGTH

        assert MAX_SECTION_LENGTH > 0
        assert isinstance(MAX_SECTION_LENGTH, int)
