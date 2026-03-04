"""Claude Code exporter — generates CLAUDE.md, task files, and verify.sh.

Produces:
- CLAUDE.md: Appends/replaces ``## intake Spec`` section
- .intake/tasks/TASK-NNN.md: One file per task
- .intake/verify.sh: Shell script for acceptance checks
- .intake/spec-summary.md: Quick reference summary
- .intake/spec/: Copy of the 6 spec files for reference
"""

from __future__ import annotations

import re
import shutil
import stat
from pathlib import Path

import structlog
from jinja2 import Environment, PackageLoader

from intake.export._helpers import (
    count_requirements,
    load_acceptance_checks,
    parse_tasks,
    read_spec_file,
    summarize_content,
)
from intake.plugins.protocols import ExportResult, PluginMeta

logger = structlog.get_logger()

INTAKE_SPEC_SECTION = "## intake Spec"


class ClaudeCodeExporter:
    """Export spec for Claude Code consumption.

    Generates a CLAUDE.md section plus structured task files and
    verification scripts in the ``.intake/`` directory.
    """

    @property
    def meta(self) -> PluginMeta:
        """Plugin metadata."""
        return PluginMeta(
            name="claude-code",
            version="0.3.0",
            description="Export spec for Claude Code",
        )

    @property
    def supported_agents(self) -> list[str]:
        """Agent names this exporter targets."""
        return ["claude-code"]

    def export(self, spec_dir: str, output_dir: str) -> ExportResult:
        """Export the spec to Claude Code format.

        Args:
            spec_dir: Path to the spec directory.
            output_dir: Path to write exported files.

        Returns:
            ExportResult with created files and instructions.

        Raises:
            ExportError: If export fails.
        """
        spec_path = Path(spec_dir)
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        env = Environment(
            loader=PackageLoader("intake", "templates"),
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        files_created: list[str] = []
        spec_name = spec_path.name

        # Load spec data
        context_content = read_spec_file(spec_path, "context.md")
        requirements_content = read_spec_file(spec_path, "requirements.md")
        design_content = read_spec_file(spec_path, "design.md")
        tasks_content = read_spec_file(spec_path, "tasks.md")
        tasks = parse_tasks(tasks_content)
        checks = load_acceptance_checks(spec_path)
        requirements_count = count_requirements(requirements_content)

        # Prepare template data
        context_summary = summarize_content(context_content, max_lines=20)
        design_summary = summarize_content(design_content, max_lines=20)

        # 1. Generate/update CLAUDE.md
        claude_md_path = out_path / "CLAUDE.md"
        claude_section = self._render_claude_section(
            env,
            spec_name,
            context_summary,
            design_summary,
            tasks,
            checks,
            requirements_count,
            spec_path,
        )
        self._update_claude_md(claude_md_path, claude_section)
        files_created.append(str(claude_md_path))

        # 2. Generate task files
        intake_dir = out_path / ".intake"
        tasks_dir = intake_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        task_template = env.get_template("claude_task.md.j2")
        for task in tasks:
            task_checks = self._find_task_checks(task, checks)
            task_data = {**task, "checks": task_checks}
            task_content = task_template.render(
                task=task_data,
                context_summary=context_summary,
            )
            task_path = tasks_dir / f"TASK-{task['id'].zfill(3)}.md"
            task_path.write_text(task_content, encoding="utf-8")
            files_created.append(str(task_path))

        # 3. Generate verify.sh
        verify_path = intake_dir / "verify.sh"
        command_checks = self._extract_command_checks(checks)
        verify_template = env.get_template("verify_sh.j2")
        verify_content = verify_template.render(
            spec_name=spec_name,
            checks=command_checks,
        )
        verify_path.write_text(verify_content, encoding="utf-8")
        verify_path.chmod(verify_path.stat().st_mode | stat.S_IEXEC)
        files_created.append(str(verify_path))

        # 4. Generate spec-summary.md
        summary_path = intake_dir / "spec-summary.md"
        summary_content = self._build_spec_summary(
            spec_name,
            context_summary,
            requirements_count,
            len(tasks),
            len(checks),
        )
        summary_path.write_text(summary_content, encoding="utf-8")
        files_created.append(str(summary_path))

        # 5. Copy spec files
        spec_out = intake_dir / "spec"
        spec_out.mkdir(exist_ok=True)
        for f in spec_path.iterdir():
            if f.is_file():
                dest = spec_out / f.name
                shutil.copy2(f, dest)
                files_created.append(str(dest))

        logger.info(
            "claude_code_export_complete",
            output_dir=str(out_path),
            files=len(files_created),
            tasks=len(tasks),
        )

        return ExportResult(
            files_created=files_created,
            primary_file=str(claude_md_path),
            instructions=(
                "Claude Code export complete.\n"
                f"  - CLAUDE.md updated with spec section\n"
                f"  - {len(tasks)} task files in .intake/tasks/\n"
                f"  - Run `bash .intake/verify.sh` to check acceptance criteria"
            ),
        )

    def _render_claude_section(
        self,
        env: Environment,
        spec_name: str,
        context_summary: str,
        design_summary: str,
        tasks: list[dict[str, str]],
        checks: list[dict[str, object]],
        requirements_count: int,
        spec_path: Path,
    ) -> str:
        """Render the intake spec section for CLAUDE.md.

        Args:
            env: Jinja2 environment.
            spec_name: Name of the spec.
            context_summary: Summarized context.
            design_summary: Summarized design.
            tasks: Parsed task list.
            checks: Acceptance checks.
            requirements_count: Number of requirements.
            spec_path: Path to spec directory.

        Returns:
            Rendered markdown section.
        """
        template = env.get_template("claude_md.j2")
        spec_files = [f.name for f in sorted(spec_path.iterdir()) if f.is_file()]
        return template.render(
            spec_name=spec_name,
            context_summary=context_summary,
            design_summary=design_summary,
            tasks=tasks,
            acceptance_count=len(checks),
            requirements_count=requirements_count,
            spec_files=spec_files,
        )

    def _update_claude_md(self, claude_md_path: Path, new_section: str) -> None:
        """Append or replace the intake spec section in CLAUDE.md.

        If the file exists and contains an ``## intake Spec`` section,
        that section is replaced. Otherwise the section is appended.

        Args:
            claude_md_path: Path to CLAUDE.md.
            new_section: Rendered section content.
        """
        if claude_md_path.exists():
            existing = claude_md_path.read_text(encoding="utf-8")
            # Replace existing section (from header to next ## or end of file)
            pattern = re.compile(
                r"^## intake Spec\b.*?(?=^## (?!intake Spec)|\Z)",
                re.MULTILINE | re.DOTALL,
            )
            if pattern.search(existing):
                updated = pattern.sub(new_section.rstrip() + "\n", existing)
                claude_md_path.write_text(updated, encoding="utf-8")
                return
            # Append to existing file
            separator = "\n\n" if not existing.endswith("\n\n") else ""
            claude_md_path.write_text(
                existing + separator + new_section,
                encoding="utf-8",
            )
        else:
            claude_md_path.write_text(new_section, encoding="utf-8")

    def _find_task_checks(
        self,
        task: dict[str, str],
        checks: list[dict[str, object]],
    ) -> list[str]:
        """Find acceptance checks related to a task.

        Args:
            task: Task dict with id and description.
            checks: All acceptance checks.

        Returns:
            List of check commands relevant to this task.
        """
        task_id = task.get("id", "")
        result: list[str] = []
        for check in checks:
            if check.get("type") != "command":
                continue
            # Match by task_id reference or task association
            check_tags = str(check.get("tags", ""))
            check_name = str(check.get("name", ""))
            if task_id and (
                f"task-{task_id}" in check_tags.lower() or f"task {task_id}" in check_name.lower()
            ):
                command = check.get("command")
                if command:
                    result.append(str(command))
        return result

    def _extract_command_checks(
        self,
        checks: list[dict[str, object]],
    ) -> list[dict[str, str]]:
        """Extract command checks for verify.sh.

        Args:
            checks: All acceptance checks.

        Returns:
            List of dicts with name and command keys.
        """
        result: list[dict[str, str]] = []
        for check in checks:
            if check.get("type") != "command" or not check.get("command"):
                continue
            name = str(check.get("name", check.get("id", "unnamed")))
            command = str(check["command"])
            # Escape single quotes for shell safety
            safe_command = command.replace("'", "'\\''")
            safe_name = name.replace("'", "'\\''")
            result.append({"name": safe_name, "command": safe_command})
        return result

    def _build_spec_summary(
        self,
        spec_name: str,
        context_summary: str,
        requirements_count: int,
        task_count: int,
        check_count: int,
    ) -> str:
        """Build a quick-reference spec summary.

        Args:
            spec_name: Name of the spec.
            context_summary: Summarized project context.
            requirements_count: Number of requirements.
            task_count: Number of tasks.
            check_count: Number of acceptance checks.

        Returns:
            Markdown summary string.
        """
        return (
            f"# Spec Summary: {spec_name}\n\n"
            f"- **Requirements:** {requirements_count}\n"
            f"- **Tasks:** {task_count}\n"
            f"- **Acceptance checks:** {check_count}\n\n"
            f"## Context\n\n{context_summary}\n"
        )
