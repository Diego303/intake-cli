"""Cursor exporter — generates .cursor/rules/intake-spec.mdc.

Produces:
- .cursor/rules/intake-spec.mdc: Cursor rules file with YAML frontmatter + Markdown
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


class CursorExporter:
    """Export spec as a Cursor rules file.

    Generates a ``.cursor/rules/intake-spec.mdc`` file that provides
    spec context to Cursor's AI assistant.
    """

    @property
    def meta(self) -> PluginMeta:
        """Plugin metadata."""
        return PluginMeta(
            name="cursor",
            version="0.3.0",
            description="Export spec for Cursor",
        )

    @property
    def supported_agents(self) -> list[str]:
        """Agent names this exporter targets."""
        return ["cursor"]

    def export(self, spec_dir: str, output_dir: str) -> ExportResult:
        """Export the spec to Cursor rules format.

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

        # Prepare check dicts for template
        acceptance_checks = self._format_checks(checks)

        # Generate .cursor/rules/intake-spec.mdc
        rules_dir = out_path / ".cursor" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)

        template = env.get_template("cursor_rules.mdc.j2")
        content = template.render(
            spec_name=spec_name,
            context_summary=context_summary,
            requirements_count=requirements_count,
            requirements_summary=requirements_summary,
            design_summary=design_summary,
            tasks=tasks,
            acceptance_checks=acceptance_checks,
        )

        rules_path = rules_dir / "intake-spec.mdc"
        rules_path.write_text(content, encoding="utf-8")
        files_created.append(str(rules_path))

        # Copy spec files for reference
        spec_out = out_path / ".intake" / "spec"
        spec_out.mkdir(parents=True, exist_ok=True)
        for f in spec_path.iterdir():
            if f.is_file():
                dest = spec_out / f.name
                shutil.copy2(f, dest)
                files_created.append(str(dest))

        logger.info(
            "cursor_export_complete",
            output_dir=str(out_path),
            files=len(files_created),
        )

        return ExportResult(
            files_created=files_created,
            primary_file=str(rules_path),
            instructions=(
                "Cursor export complete.\n"
                "  - Rules file: .cursor/rules/intake-spec.mdc\n"
                "  - Spec files copied to .intake/spec/\n"
                "  - The rules file will be auto-loaded by Cursor"
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
            List of dicts with name, type, command, pattern keys.
        """
        result: list[dict[str, str]] = []
        for check in checks:
            if not isinstance(check, dict):
                continue
            formatted: dict[str, str] = {
                "name": str(check.get("name", check.get("id", "unnamed"))),
                "type": str(check.get("type", "unknown")),
            }
            if check.get("command"):
                formatted["command"] = str(check["command"])
            if check.get("pattern"):
                formatted["pattern"] = str(check["pattern"])
            result.append(formatted)
        return result
