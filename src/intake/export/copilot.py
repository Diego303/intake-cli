"""Copilot exporter — generates .github/copilot-instructions.md.

Produces:
- .github/copilot-instructions.md: Instructions file for GitHub Copilot
"""

from __future__ import annotations

import shutil
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


class CopilotExporter:
    """Export spec as GitHub Copilot instructions.

    Generates a ``.github/copilot-instructions.md`` file that provides
    spec context to GitHub Copilot.
    """

    @property
    def meta(self) -> PluginMeta:
        """Plugin metadata."""
        return PluginMeta(
            name="copilot",
            version="0.3.0",
            description="Export spec for GitHub Copilot",
        )

    @property
    def supported_agents(self) -> list[str]:
        """Agent names this exporter targets."""
        return ["copilot"]

    def export(self, spec_dir: str, output_dir: str) -> ExportResult:
        """Export the spec to Copilot format.

        Args:
            spec_dir: Path to the spec directory.
            output_dir: Path to write exported files.

        Returns:
            ExportResult with created files and instructions.
        """
        spec_path = Path(spec_dir)
        out_path = Path(output_dir)

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

        # Prepare summaries
        context_summary = summarize_content(context_content, max_lines=30)
        design_summary = summarize_content(design_content, max_lines=30)
        requirements_summary = summarize_content(requirements_content, max_lines=40)

        # Format checks for template
        acceptance_checks = self._format_checks(checks)

        # Generate .github/copilot-instructions.md
        github_dir = out_path / ".github"
        github_dir.mkdir(parents=True, exist_ok=True)

        template = env.get_template("copilot_instructions.md.j2")
        content = template.render(
            spec_name=spec_name,
            context_summary=context_summary,
            requirements_count=requirements_count,
            requirements_summary=requirements_summary,
            design_summary=design_summary,
            tasks=tasks,
            acceptance_checks=acceptance_checks,
        )

        instructions_path = github_dir / "copilot-instructions.md"
        instructions_path.write_text(content, encoding="utf-8")
        files_created.append(str(instructions_path))

        # Copy spec files for reference
        spec_out = out_path / ".intake" / "spec"
        spec_out.mkdir(parents=True, exist_ok=True)
        for f in spec_path.iterdir():
            if f.is_file():
                dest = spec_out / f.name
                shutil.copy2(f, dest)
                files_created.append(str(dest))

        logger.info(
            "copilot_export_complete",
            output_dir=str(out_path),
            files=len(files_created),
        )

        return ExportResult(
            files_created=files_created,
            primary_file=str(instructions_path),
            instructions=(
                "Copilot export complete.\n"
                "  - Instructions: .github/copilot-instructions.md\n"
                "  - Spec files copied to .intake/spec/\n"
                "  - Copilot will auto-load the instructions file"
            ),
        )

    def _format_checks(
        self,
        checks: list[dict[str, object]],
    ) -> list[dict[str, str]]:
        """Format acceptance checks for template rendering.

        Args:
            checks: Raw acceptance checks from YAML.

        Returns:
            List of dicts with name, command/pattern keys.
        """
        result: list[dict[str, str]] = []
        for check in checks:
            if not isinstance(check, dict):
                continue
            formatted: dict[str, str] = {
                "name": str(check.get("name", check.get("id", "unnamed"))),
            }
            if check.get("command"):
                formatted["command"] = str(check["command"])
            if check.get("pattern"):
                formatted["pattern"] = str(check["pattern"])
            result.append(formatted)
        return result
