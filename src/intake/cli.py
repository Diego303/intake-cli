"""Thin CLI adapter for intake.

All commands follow the same structure:
1. Load config
2. Call the appropriate module
3. Display result with Rich
4. Exit with semantic code (0=success, 1=verification failure, 2=error)

No business logic lives here.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from intake import __version__
from intake.config.loader import load_config
from intake.doctor.checks import DoctorChecks
from intake.utils.logging import setup_logging

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="intake")
def main() -> None:
    """intake — From requirements in any format to verified implementation."""


@main.command()
@click.argument("description")
@click.option(
    "--source", "-s", multiple=True, required=True,
    help="Requirement source (repeatable). File path, or '-' for stdin.",
)
@click.option(
    "--model", "-m", default=None,
    help="LLM model for analysis (default: config or claude-sonnet-4).",
)
@click.option(
    "--lang", "-l", default=None,
    help="Language for generated spec content (default: config or 'en').",
)
@click.option(
    "--project-dir", "-p", default=".", type=click.Path(exists=True),
    help="Existing project directory (for stack auto-detection).",
)
@click.option(
    "--stack", default=None,
    help="Tech stack (auto-detected if omitted). E.g.: 'python,fastapi,postgresql'.",
)
@click.option(
    "--output", "-o", default=None, type=click.Path(),
    help="Output directory for the spec (default: ./specs/).",
)
@click.option(
    "--format", "-f", "export_format", default=None,
    type=click.Choice(["architect", "claude-code", "cursor", "kiro", "generic"]),
    help="Export format (default: config or 'generic').",
)
@click.option(
    "--preset", default=None,
    type=click.Choice(["minimal", "standard", "enterprise"]),
    help="Configuration preset. Overrides .intake.yaml defaults.",
)
@click.option(
    "--interactive", "-i", is_flag=True,
    help="Interactive mode: prompts before generating each section.",
)
@click.option("--dry-run", is_flag=True, help="Show what would be done without generating files.")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output.")
def init(
    description: str,
    source: tuple[str, ...],
    model: str | None,
    lang: str | None,
    project_dir: str,
    stack: str | None,
    output: str | None,
    export_format: str | None,
    preset: str | None,
    interactive: bool,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Generate a spec from requirement sources.

    DESCRIPTION is a short phrase describing what to build.

    Examples:

      intake init "OAuth2 authentication system" -s requirements.md

      intake init "Payments feature" -s jira.json -s confluence.html -s notes.md

      intake init "User endpoint" -s reqs.pdf --format architect

      intake init "API gateway" -s reqs.yaml --preset enterprise
    """
    setup_logging(verbose=verbose)

    # Build CLI overrides
    overrides: dict[str, str | None] = {}
    if model:
        overrides["llm.model"] = model
    if lang:
        overrides["project.language"] = lang
    if output:
        overrides["spec.output_dir"] = output
    if export_format:
        overrides["export.default_format"] = export_format

    try:
        config = load_config(cli_overrides=overrides, preset=preset)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(2)

    # Auto-detect stack if not provided
    if stack:
        config = config.model_copy(
            update={"project": config.project.model_copy(
                update={"stack": [s.strip() for s in stack.split(",")]},
            )},
        )
    elif not config.project.stack:
        from intake.utils.project_detect import detect_stack
        detected = detect_stack(project_dir)
        if detected:
            config = config.model_copy(
                update={"project": config.project.model_copy(
                    update={"stack": detected},
                )},
            )
            console.print(f"[dim]Detected stack: {', '.join(detected)}[/dim]")

    # Set project name from description
    spec_name = _slugify(description)
    if not config.project.name:
        config = config.model_copy(
            update={"project": config.project.model_copy(
                update={"name": spec_name},
            )},
        )

    if dry_run:
        console.print(f"[bold]Dry run:[/bold] would generate spec '{spec_name}'")
        console.print(f"  Sources: {', '.join(source)}")
        console.print(f"  Model: {config.llm.model}")
        console.print(f"  Output: {config.spec.output_dir}/{spec_name}/")
        console.print(f"  Stack: {', '.join(config.project.stack) or 'none'}")
        return

    try:
        # Phase 1: Ingest
        console.print("[bold]Phase 1:[/bold] Ingesting sources...")
        from intake.ingest.registry import create_default_registry
        registry = create_default_registry()
        parsed_sources = []
        for src in source:
            parsed = registry.parse(src)
            parsed_sources.append(parsed)
            console.print(f"  Parsed: {src} ({parsed.format}, {parsed.word_count} words)")

        # Phase 2: Analyze
        console.print("[bold]Phase 2:[/bold] Analyzing with LLM...")
        from intake.analyze.analyzer import Analyzer
        from intake.llm import LLMAdapter
        llm = LLMAdapter(config.llm)
        analyzer = Analyzer(config=config, llm=llm)
        result = asyncio.run(analyzer.analyze(parsed_sources))
        console.print(
            f"  Extracted: {result.requirement_count} requirements, "
            f"{len(result.conflicts)} conflicts, "
            f"{len(result.open_questions)} questions"
        )
        if result.risks:
            console.print(f"  Risks: {len(result.risks)} identified")

        # Phase 3: Generate
        console.print("[bold]Phase 3:[/bold] Generating spec files...")
        from intake.generate.spec_builder import SpecBuilder
        builder = SpecBuilder(config)
        generated_files = builder.generate(result, parsed_sources, spec_name)
        for f in generated_files:
            console.print(f"  Generated: {f}")

        # Phase 5: Export (optional, if format specified)
        if export_format:
            console.print(f"[bold]Phase 5:[/bold] Exporting ({export_format})...")
            from intake.export.registry import create_default_registry as create_export_registry
            export_registry = create_export_registry()
            spec_dir = str(Path(config.spec.output_dir) / spec_name)
            exporter = export_registry.get(export_format)
            export_out = str(Path(config.spec.output_dir) / spec_name / "export")
            exported = exporter.export(spec_dir, export_out)
            for f in exported:
                console.print(f"  Exported: {f}")

        # Summary
        console.print("")
        console.print(f"[green bold]Spec '{spec_name}' generated successfully.[/green bold]")
        console.print(f"  Output: {config.spec.output_dir}/{spec_name}/")
        console.print(f"  Cost: ${result.total_cost:.4f}")
        console.print(f"  Tasks: {result.task_count}")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        sys.exit(2)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(2)


@main.command()
@click.argument("spec_dir", type=click.Path(exists=True))
@click.option(
    "--source", "-s", multiple=True, required=True,
    help="New sources to add.",
)
@click.option(
    "--regenerate", is_flag=True,
    help="Regenerate the entire spec with new sources included.",
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output.")
def add(spec_dir: str, source: tuple[str, ...], regenerate: bool, verbose: bool) -> None:
    """Add sources to an existing spec (incremental by default).

    Only new sources are analyzed and merged into the existing spec.
    Use --regenerate to reprocess everything from scratch.

    Example:
      intake add ./specs/auth-oauth2 -s client-feedback.txt -s new-req.md
    """
    setup_logging(verbose=verbose)

    try:
        config = load_config()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(2)

    spec_path = Path(spec_dir)

    try:
        # Check for existing lock to detect staleness
        from intake.generate.lock import LOCK_FILENAME, SpecLock
        lock_path = spec_path / LOCK_FILENAME
        if lock_path.exists():
            SpecLock.from_yaml(str(lock_path))

        # Parse new sources
        console.print("[bold]Ingesting new sources...[/bold]")
        from intake.ingest.registry import create_default_registry
        registry = create_default_registry()
        new_parsed = []
        for src in source:
            parsed = registry.parse(src)
            new_parsed.append(parsed)
            console.print(f"  Parsed: {src} ({parsed.format}, {parsed.word_count} words)")

        # Analyze new sources
        console.print("[bold]Analyzing new sources...[/bold]")
        from intake.analyze.analyzer import Analyzer
        from intake.llm import LLMAdapter
        llm = LLMAdapter(config.llm)
        analyzer = Analyzer(config=config, llm=llm)
        result = asyncio.run(analyzer.analyze(new_parsed))
        console.print(
            f"  Extracted: {result.requirement_count} requirements"
        )

        # Regenerate spec with new analysis
        console.print("[bold]Regenerating spec files...[/bold]")
        from intake.generate.spec_builder import SpecBuilder
        builder = SpecBuilder(config)
        # Override output to write to the same spec directory
        config = config.model_copy(
            update={"spec": config.spec.model_copy(
                update={"output_dir": str(spec_path.parent)},
            )},
        )
        builder = SpecBuilder(config)
        generated = builder.generate(result, new_parsed, spec_path.name)
        for f in generated:
            console.print(f"  Updated: {f}")

        console.print(f"\n[green bold]Spec updated with {len(source)} new source(s).[/green bold]")
        console.print(f"  Cost: ${result.total_cost:.4f}")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        sys.exit(2)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(2)


@main.command()
@click.argument("spec_dir", type=click.Path(exists=True))
@click.option(
    "--project-dir", "-p", default=".", type=click.Path(exists=True),
    help="Project directory to verify against.",
)
@click.option(
    "--format", "-f", "report_format",
    type=click.Choice(["terminal", "json", "junit"]),
    default="terminal", help="Report format.",
)
@click.option("--tags", "-t", multiple=True, help="Only run checks with these tags.")
@click.option("--fail-fast", is_flag=True, help="Stop at the first failing check.")
def verify(
    spec_dir: str,
    project_dir: str,
    report_format: str,
    tags: tuple[str, ...],
    fail_fast: bool,
) -> None:
    """Verify if the implementation meets the spec.

    Runs the checks defined in acceptance.yaml against the project.

    Example:
      intake verify ./specs/auth-oauth2 -p ./my-project

    Exit codes:
      0 = all required checks passed
      1 = at least one required check failed
      2 = execution error
    """
    try:
        config = load_config()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(2)

    acceptance_file = str(Path(spec_dir) / "acceptance.yaml")

    try:
        from intake.verify.engine import VerificationEngine
        from intake.verify.reporter import get_reporter

        engine = VerificationEngine(
            project_dir=project_dir,
            timeout_per_check=config.verification.timeout_per_check,
        )
        report = engine.run(
            acceptance_file=acceptance_file,
            tags=list(tags) if tags else None,
            fail_fast=fail_fast,
        )

        reporter = get_reporter(report_format)
        output = reporter.render(report)

        # For non-terminal formats, print the output directly
        if report_format != "terminal":
            console.print(output)

        sys.exit(report.exit_code)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(2)


@main.command()
@click.argument("spec_dir", type=click.Path(exists=True))
@click.option(
    "--format", "-f", "export_format", required=True,
    type=click.Choice(["architect", "claude-code", "cursor", "kiro", "generic"]),
    help="Export format.",
)
@click.option(
    "--output", "-o", default=".", type=click.Path(),
    help="Output directory.",
)
def export(spec_dir: str, export_format: str, output: str) -> None:
    """Export a spec to a specific agent format.

    Example:
      intake export ./specs/auth-oauth2 -f architect -o ./
    """
    try:
        from intake.export.registry import create_default_registry

        registry = create_default_registry()
        exporter = registry.get(export_format)
        generated = exporter.export(spec_dir, output)

        for f in generated:
            console.print(f"  Generated: {f}")

        console.print(f"\n[green]Exported {len(generated)} file(s) to {output}[/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(2)


@main.command()
@click.argument("spec_dir", type=click.Path(exists=True))
def show(spec_dir: str) -> None:
    """Show a spec summary: requirements, tasks, checks, costs, risks.

    Example:
      intake show ./specs/auth-oauth2
    """
    spec_path = Path(spec_dir)

    try:
        # Load lock for metadata
        from intake.generate.lock import LOCK_FILENAME, SpecLock
        lock_path = spec_path / LOCK_FILENAME
        lock: SpecLock | None = None
        if lock_path.exists():
            lock = SpecLock.from_yaml(str(lock_path))

        # Summary table
        table = Table(title=f"Spec: {spec_path.name}", show_lines=True)
        table.add_column("Property", style="bold")
        table.add_column("Value")

        # List spec files
        spec_files = sorted(
            f.name for f in spec_path.iterdir()
            if f.is_file() and f.name != LOCK_FILENAME
        )
        table.add_row("Files", ", ".join(spec_files))

        if lock:
            table.add_row("Model", lock.model or "unknown")
            table.add_row("Requirements", str(lock.requirement_count))
            table.add_row("Tasks", str(lock.task_count))
            table.add_row("Cost", f"${lock.total_cost:.4f}")
            table.add_row("Created", lock.created_at)
            table.add_row("Sources", str(len(lock.source_hashes)))
        else:
            table.add_row("Lock", "[yellow]No spec.lock.yaml found[/yellow]")

        console.print(table)

        # Show quick counts from acceptance.yaml
        import yaml
        acceptance_path = spec_path / "acceptance.yaml"
        if acceptance_path.exists():
            with open(acceptance_path) as f:
                data = yaml.safe_load(f) or {}
            checks = data.get("checks", [])
            if isinstance(checks, list):
                console.print(f"\nAcceptance checks: {len(checks)}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(2)


@main.command("list")
@click.option(
    "--dir", "-d", "specs_dir", default="./specs",
    type=click.Path(), help="Specs directory.",
)
def list_specs(specs_dir: str) -> None:
    """List all specs in the project."""
    specs_path = Path(specs_dir)

    if not specs_path.exists():
        console.print(f"[yellow]No specs directory found at {specs_dir}[/yellow]")
        console.print("Run 'intake init' to generate your first spec.")
        return

    # Find spec directories (those containing at least requirements.md or acceptance.yaml)
    specs = []
    for item in sorted(specs_path.iterdir()):
        if item.is_dir():
            has_spec_files = (
                (item / "requirements.md").exists()
                or (item / "acceptance.yaml").exists()
            )
            if has_spec_files:
                specs.append(item)

    if not specs:
        console.print(f"[yellow]No specs found in {specs_dir}[/yellow]")
        console.print("Run 'intake init' to generate your first spec.")
        return

    table = Table(title="Specs", show_lines=True)
    table.add_column("Name", style="bold")
    table.add_column("Files", justify="right")
    table.add_column("Model")
    table.add_column("Requirements", justify="right")
    table.add_column("Tasks", justify="right")
    table.add_column("Created")

    from intake.generate.lock import LOCK_FILENAME, SpecLock

    for spec_dir in specs:
        file_count = sum(1 for f in spec_dir.iterdir() if f.is_file())
        lock_path = spec_dir / LOCK_FILENAME

        if lock_path.exists():
            lock = SpecLock.from_yaml(str(lock_path))
            table.add_row(
                spec_dir.name,
                str(file_count),
                lock.model or "—",
                str(lock.requirement_count),
                str(lock.task_count),
                lock.created_at[:10] if lock.created_at else "—",
            )
        else:
            table.add_row(spec_dir.name, str(file_count), "—", "—", "—", "—")

    console.print(table)


@main.command()
@click.argument("spec_a", type=click.Path(exists=True))
@click.argument("spec_b", type=click.Path(exists=True))
@click.option(
    "--section",
    type=click.Choice(["requirements", "design", "tasks", "acceptance", "all"]),
    default="all", help="Which section to compare.",
)
def diff(spec_a: str, spec_b: str, section: str) -> None:
    """Compare two spec versions and show changes.

    Useful after running ``intake add`` or ``intake regenerate`` to see
    what changed in the spec.

    Example:
      intake diff ./specs/auth-v1 ./specs/auth-v2
      intake diff ./specs/auth-v1 ./specs/auth-v2 --section requirements
    """
    try:
        from intake.diff.differ import SpecDiffer

        differ = SpecDiffer()
        sections = None if section == "all" else [section]
        result = differ.diff(spec_a, spec_b, sections=sections)

        if not result.has_changes:
            console.print("[green]No differences found.[/green]")
            return

        table = Table(title=f"Diff: {result.spec_a} → {result.spec_b}", show_lines=True)
        table.add_column("Section", style="bold")
        table.add_column("Change", style="cyan")
        table.add_column("ID")
        table.add_column("Summary")

        for change in result.changes:
            change_style = {
                "added": "[green]added[/green]",
                "removed": "[red]removed[/red]",
                "modified": "[yellow]modified[/yellow]",
            }.get(change.change_type, change.change_type)

            table.add_row(
                change.section, change_style, change.item_id, change.summary,
            )

        console.print(table)

        console.print(
            f"\nTotal: [green]+{len(result.added)}[/green] "
            f"[red]-{len(result.removed)}[/red] "
            f"[yellow]~{len(result.modified)}[/yellow]"
        )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(2)


@main.command()
@click.option("--fix", is_flag=True, help="Attempt to fix detected issues automatically.")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output.")
def doctor(fix: bool, verbose: bool) -> None:
    """Check environment and configuration health.

    Verifies:
    - Required dependencies are installed
    - API key environment variables are set
    - .intake.yaml is valid (if present)

    Example:
      intake doctor
      intake doctor --fix
    """
    setup_logging(verbose=verbose)
    checks = DoctorChecks()
    results = checks.run_all()

    table = Table(title="intake doctor", show_lines=True)
    table.add_column("Check", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Details")
    table.add_column("Fix", style="dim")

    for result in results:
        status = "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]"
        table.add_row(result.name, status, result.message, result.fix_hint)

    console.print(table)

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    fixable = [
        r for r in results
        if r.auto_fixable
        and (not r.passed or r.fix_action == "create_config")
    ]

    if failed == 0 and not fix:
        console.print(f"\n[green]All {passed} checks passed.[/green]")
        if fixable:
            console.print(
                f"[dim]{len(fixable)} optional fix(es) available. "
                f"Run 'intake doctor --fix' to apply.[/dim]"
            )
    elif fix and fixable:
        console.print(f"\n[bold]Applying {len(fixable)} fix(es)...[/bold]")
        fix_results = checks.fix(results)
        for fr in fix_results:
            icon = "[green]OK[/green]" if fr.success else "[red]FAIL[/red]"
            console.print(f"  {icon} {fr.name}: {fr.message}")

        successes = sum(1 for fr in fix_results if fr.success)
        failures = sum(1 for fr in fix_results if not fr.success)
        if failures == 0:
            console.print(f"\n[green]All {successes} fix(es) applied successfully.[/green]")
        else:
            console.print(
                f"\n[yellow]{successes} fix(es) applied, {failures} failed.[/yellow]"
            )
            sys.exit(1)
    elif failed > 0:
        console.print(f"\n[red]{failed} check(s) failed[/red], {passed} passed.")
        if fixable:
            console.print(
                f"[dim]{len(fixable)} fix(es) available. "
                f"Run 'intake doctor --fix' to apply.[/dim]"
            )
        sys.exit(1)


def _slugify(text: str) -> str:
    """Convert a description to a slug suitable for directory names.

    Args:
        text: Free-text description.

    Returns:
        Lowercase, hyphen-separated slug.
    """
    import re
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")[:50]
