"""Tests for MCP prompts (without requiring the mcp package)."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

mcp_available = importlib.util.find_spec("mcp") is not None
pytestmark = pytest.mark.skipif(not mcp_available, reason="mcp package not installed")

from intake.mcp.prompts import _build_implement_prompt, _build_verify_prompt  # noqa: E402


@pytest.fixture()
def spec_path(tmp_path: Path) -> Path:
    """Create a minimal spec directory."""
    spec = tmp_path / "auth"
    spec.mkdir()

    (spec / "context.md").write_text("# Context\n\nPython + FastAPI\n")
    (spec / "requirements.md").write_text(
        "# Requirements\n\n## FR-01: Login\n\nEmail/password login.\n"
    )
    (spec / "tasks.md").write_text("# Tasks\n\n## Task 1: Implement login\n\n**Status:** pending\n")
    return spec


class TestBuildImplementPrompt:
    """Tests for _build_implement_prompt."""

    def test_includes_spec_context(self, spec_path: Path) -> None:
        messages = _build_implement_prompt(spec_path, "auth")
        # Should be a list with one message
        assert len(messages) == 1
        msg = messages[0]
        # Check the content contains spec information
        text = msg.content.text
        assert "auth" in text
        assert "context.md" in text
        assert "requirements.md" in text
        assert "tasks.md" in text

    def test_includes_implementation_instructions(self, spec_path: Path) -> None:
        messages = _build_implement_prompt(spec_path, "auth")
        text = messages[0].content.text
        assert "next pending task" in text
        assert "intake_verify" in text
        assert "intake_update_task" in text

    def test_handles_missing_files(self, tmp_path: Path) -> None:
        empty_spec = tmp_path / "empty-spec"
        empty_spec.mkdir()
        messages = _build_implement_prompt(empty_spec, "empty-spec")
        assert len(messages) == 1
        # Should still produce a prompt, just without file content
        assert "empty-spec" in messages[0].content.text

    def test_message_role_is_user(self, spec_path: Path) -> None:
        messages = _build_implement_prompt(spec_path, "auth")
        assert messages[0].role == "user"

    def test_content_type_is_text(self, spec_path: Path) -> None:
        messages = _build_implement_prompt(spec_path, "auth")
        assert messages[0].content.type == "text"

    def test_includes_design_reference(self, spec_path: Path) -> None:
        messages = _build_implement_prompt(spec_path, "auth")
        text = messages[0].content.text
        assert "design" in text.lower()


class TestBuildVerifyPrompt:
    """Tests for _build_verify_prompt."""

    def test_includes_verify_instructions(self, spec_path: Path) -> None:
        messages = _build_verify_prompt(spec_path, "auth")
        assert len(messages) == 1
        text = messages[0].content.text
        assert "intake_verify" in text
        assert "auth" in text
        assert "failing check" in text.lower()

    def test_includes_fix_loop_instructions(self, spec_path: Path) -> None:
        messages = _build_verify_prompt(spec_path, "auth")
        text = messages[0].content.text
        assert "Fix the code" in text
        assert "Re-run" in text

    def test_includes_repeat_until_pass(self, spec_path: Path) -> None:
        messages = _build_verify_prompt(spec_path, "auth")
        text = messages[0].content.text
        assert "Repeat" in text
        assert "all required checks pass" in text

    def test_message_role_is_user(self, spec_path: Path) -> None:
        messages = _build_verify_prompt(spec_path, "auth")
        assert messages[0].role == "user"
