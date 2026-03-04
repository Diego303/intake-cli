"""Kiro exporter — generates Kiro-native requirements, design, and tasks files.

Produces:
- requirements.md: Kiro-format requirements with acceptance criteria checkboxes
- design.md: Design document in Kiro format
- tasks.md: Tasks with status and verification checkboxes
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import structlog
from jinja2 import Environment, PackageLoader

from intake.export._helpers import (
    load_acceptance_checks,
    parse_tasks,
    read_spec_file,
)
from intake.plugins.protocols import ExportResult, PluginMeta

logger = structlog.get_logger()


class KiroExporter:
    """Export spec in Kiro's native document format.

    Generates requirements.md, design.md, and tasks.md in a format
    that Kiro can directly consume as project specification files.
    """

    @property
    def meta(self) -> PluginMeta:
        """Plugin metadata."""
        return PluginMeta(
            name="kiro",
            version="0.3.0",
            description="Export spec for Kiro",
        )

    @property
    def supported_agents(self) -> list[str]:
        """Agent names this exporter targets."""
        return ["kiro"]

    def export(self, spec_dir: str, output_dir: str) -> ExportResult:
        """Export the spec to Kiro format.

        Args:
            spec_dir: Path to the spec directory.
            output_dir: Path to write exported files.

        Returns:
            ExportResult with created files and instructions.
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
        requirements_content = read_spec_file(spec_path, "requirements.md")
        design_content = read_spec_file(spec_path, "design.md")
        tasks_content = read_spec_file(spec_path, "tasks.md")
        tasks = parse_tasks(tasks_content)
        checks = load_acceptance_checks(spec_path)

        # Parse requirements into structured format
        requirements = self._parse_requirements(requirements_content, checks)

        # Attach command checks to tasks
        tasks_with_checks = self._attach_checks_to_tasks(tasks, checks)

        # 1. Generate requirements.md
        req_template = env.get_template("kiro_requirements.md.j2")
        req_content = req_template.render(
            spec_name=spec_name,
            requirements=requirements,
        )
        req_path = out_path / "requirements.md"
        req_path.write_text(req_content, encoding="utf-8")
        files_created.append(str(req_path))

        # 2. Generate design.md
        design_template = env.get_template("kiro_design.md.j2")
        design_rendered = design_template.render(
            spec_name=spec_name,
            design_content=design_content,
        )
        design_path = out_path / "design.md"
        design_path.write_text(design_rendered, encoding="utf-8")
        files_created.append(str(design_path))

        # 3. Generate tasks.md
        tasks_template = env.get_template("kiro_tasks.md.j2")
        tasks_rendered = tasks_template.render(
            spec_name=spec_name,
            tasks=tasks_with_checks,
        )
        tasks_path = out_path / "tasks.md"
        tasks_path.write_text(tasks_rendered, encoding="utf-8")
        files_created.append(str(tasks_path))

        # Copy spec files for reference
        spec_out = out_path / ".intake" / "spec"
        spec_out.mkdir(parents=True, exist_ok=True)
        for f in spec_path.iterdir():
            if f.is_file():
                dest = spec_out / f.name
                shutil.copy2(f, dest)
                files_created.append(str(dest))

        logger.info(
            "kiro_export_complete",
            output_dir=str(out_path),
            files=len(files_created),
            requirements=len(requirements),
            tasks=len(tasks),
        )

        return ExportResult(
            files_created=files_created,
            primary_file=str(req_path),
            instructions=(
                "Kiro export complete.\n"
                f"  - {len(requirements)} requirements in requirements.md\n"
                f"  - Design document in design.md\n"
                f"  - {len(tasks)} tasks in tasks.md\n"
                f"  - Open the project in Kiro to use the spec"
            ),
        )

    def _parse_requirements(
        self,
        requirements_content: str,
        checks: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        """Parse requirements.md into structured requirement objects.

        Extracts requirement blocks matching ``### FR-NNN``, ``### NFR-NNN``,
        or ``### REQ-NNN`` patterns and their acceptance criteria.

        Args:
            requirements_content: Raw requirements.md content.
            checks: Acceptance checks for cross-referencing.

        Returns:
            List of requirement dicts with id, title, description,
            acceptance_criteria keys.
        """
        if not requirements_content.strip():
            return []

        requirements: list[dict[str, object]] = []
        current_req: dict[str, object] | None = None
        description_lines: list[str] = []
        criteria: list[str] = []

        for line in requirements_content.splitlines():
            match = re.match(
                r"^###\s+((?:N?FR|REQ)-\d+)[:.]?\s*(.*)",
                line,
            )
            if match:
                if current_req is not None:
                    current_req["description"] = "\n".join(description_lines).strip()
                    current_req["acceptance_criteria"] = (
                        criteria
                        if criteria
                        else [
                            "Requirement is implemented and working",
                        ]
                    )
                    requirements.append(current_req)

                current_req = {
                    "id": match.group(1),
                    "title": match.group(2).strip(),
                    "description": "",
                    "acceptance_criteria": [],
                }
                description_lines = []
                criteria = []
            elif current_req is not None:
                # Detect acceptance criteria lines
                ac_match = re.match(r"^[-*]\s+(.+)", line)
                in_ac_section = (
                    any(
                        "acceptance" in prev.lower() or "criteria" in prev.lower()
                        for prev in description_lines[-3:]
                    )
                    if description_lines
                    else False
                )

                if ac_match and in_ac_section:
                    criteria.append(ac_match.group(1).strip())
                elif re.match(r"^#{1,2}\s+", line):
                    # New top-level section, save current
                    current_req["description"] = "\n".join(description_lines).strip()
                    current_req["acceptance_criteria"] = (
                        criteria
                        if criteria
                        else [
                            "Requirement is implemented and working",
                        ]
                    )
                    requirements.append(current_req)
                    current_req = None
                    description_lines = []
                    criteria = []
                else:
                    description_lines.append(line)

        if current_req is not None:
            current_req["description"] = "\n".join(description_lines).strip()
            current_req["acceptance_criteria"] = (
                criteria
                if criteria
                else [
                    "Requirement is implemented and working",
                ]
            )
            requirements.append(current_req)

        return requirements

    def _attach_checks_to_tasks(
        self,
        tasks: list[dict[str, str]],
        checks: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        """Attach relevant command checks to each task.

        Args:
            tasks: Parsed tasks from tasks.md.
            checks: All acceptance checks.

        Returns:
            Tasks with an added 'checks' key containing command strings.
        """
        command_checks = [c for c in checks if c.get("type") == "command" and c.get("command")]

        result: list[dict[str, object]] = []
        for task in tasks:
            task_dict: dict[str, object] = dict(task)
            task_checks: list[str] = []
            for check in command_checks:
                check_tags = str(check.get("tags", ""))
                check_name = str(check.get("name", ""))
                task_id = task.get("id", "")
                if (
                    f"task-{task_id}" in check_tags.lower()
                    or f"task {task_id}" in check_name.lower()
                ):
                    task_checks.append(str(check["command"]))
            task_dict["checks"] = task_checks
            result.append(task_dict)
        return result
