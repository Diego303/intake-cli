"""File watcher with selective re-verification.

Uses ``watchfiles`` (Rust-based, efficient) to monitor the project
directory. On file change, determines which checks are affected
and re-runs them.

Requires: pip install intake-ai-cli[watch]
"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from intake.verify.engine import VerificationEngine, VerificationReport
from intake.watch import WatchError

if TYPE_CHECKING:
    from intake.config.schema import WatchConfig

logger = structlog.get_logger()

# Maximum number of changed files to display in the terminal.
MAX_CHANGED_FILES_DISPLAY = 5


class SpecWatcher:
    """Watch project files and re-run verification on changes.

    Uses ``watchfiles`` to monitor the project directory with
    configurable debouncing and ignore patterns.

    Args:
        spec_dir: Path to the spec directory containing acceptance.yaml.
        project_dir: Path to the project to watch.
        config: Watch configuration with debounce and ignore settings.
        tags: Optional list of tags to filter checks.
    """

    def __init__(
        self,
        spec_dir: str,
        project_dir: str,
        config: WatchConfig,
        tags: list[str] | None = None,
    ) -> None:
        self.spec_dir = Path(spec_dir)
        self.project_dir = Path(project_dir)
        self.config = config
        self.tags = tags
        self.engine = VerificationEngine(project_dir)
        self._last_report: VerificationReport | None = None
        self._acceptance_file = str(self.spec_dir / "acceptance.yaml")

    @property
    def last_report(self) -> VerificationReport | None:
        """Last verification report, or None if not yet run."""
        return self._last_report

    def run(self) -> None:
        """Start watching. Blocks until interrupted with Ctrl+C.

        Raises:
            ImportError: If watchfiles is not installed.
            WatchError: If the spec directory is invalid.
        """
        try:
            from watchfiles import watch
        except ImportError:
            raise ImportError(
                "Watch mode requires the watchfiles package. "
                "Install with: pip install intake-ai-cli[watch]"
            ) from None

        from rich.console import Console

        if not self.spec_dir.exists():
            raise WatchError(
                reason=f"Spec directory not found: {self.spec_dir}",
                suggestion="Run 'intake init' first to generate a spec.",
            )

        acceptance_path = Path(self._acceptance_file)
        if not acceptance_path.exists():
            raise WatchError(
                reason=f"acceptance.yaml not found in {self.spec_dir}",
                suggestion="Run 'intake init' to generate acceptance.yaml.",
            )

        console = Console()
        console.print(f"[bold]Watching[/bold] {self.project_dir} for changes...")
        console.print(f"[bold]Spec:[/bold] {self.spec_dir.name}")
        console.print("Press Ctrl+C to stop.\n")

        # Initial verification run
        self._run_and_display(console)

        # Watch for changes
        ignore_patterns = self.config.ignore_patterns
        debounce_ms = int(self.config.debounce_seconds * 1000)

        try:
            for changes in watch(
                str(self.project_dir),
                debounce=debounce_ms,
                recursive=True,
            ):
                changed_files = self._extract_changed_files(changes)
                relevant = self._filter_ignored(changed_files, ignore_patterns)

                if not relevant:
                    continue

                self._display_changes(console, relevant)
                self._run_and_display(console)

        except KeyboardInterrupt:
            console.print("\n[bold]Watch stopped.[/bold]")

        logger.info(
            "watch_stopped",
            spec=self.spec_dir.name,
            last_passed=self._last_report.all_required_passed if self._last_report else None,
        )

    def run_once(self) -> VerificationReport:
        """Run verification once without watching.

        Useful for testing and programmatic use.

        Returns:
            VerificationReport from the verification engine.
        """
        report = self.engine.run(
            self._acceptance_file,
            tags=self.tags,
        )
        self._last_report = report
        return report

    def _run_and_display(self, console: object) -> None:
        """Run checks and display results.

        Args:
            console: Rich Console instance for output.
        """
        from rich.console import Console as RichConsole

        assert isinstance(console, RichConsole)

        report = self.engine.run(self._acceptance_file, tags=self.tags)
        self._last_report = report

        color = "green" if report.all_required_passed else "red"
        status = "ALL PASSED" if report.all_required_passed else "FAILURES DETECTED"

        console.print(
            f"\n[bold {color}]{status}[/bold {color}] "
            f"({report.passed}/{report.total_checks} checks)"
        )

        for r in report.results:
            if not r.passed:
                console.print(f"  [red]FAIL {r.id}:[/red] {r.name}")
                if r.output:
                    console.print(f"     {r.output[:150]}")

    def _extract_changed_files(
        self,
        changes: set[tuple[object, str]],
    ) -> list[str]:
        """Extract relative file paths from watchfiles change set.

        Args:
            changes: Set of (change_type, path) tuples from watchfiles.

        Returns:
            List of relative file paths as strings.
        """
        result: list[str] = []
        for _change_type, file_path in changes:
            try:
                rel = str(Path(file_path).relative_to(self.project_dir))
                result.append(rel)
            except ValueError:
                result.append(file_path)
        return result

    def _filter_ignored(
        self,
        files: list[str],
        patterns: list[str],
    ) -> list[str]:
        """Filter out files matching ignore patterns.

        Checks the full path, the filename, and each path component
        against every pattern so that e.g. ``.git`` matches
        ``.git/objects/abc``.

        Args:
            files: List of file paths to check.
            patterns: Glob patterns to ignore.

        Returns:
            Files that do not match any ignore pattern.
        """
        return [f for f in files if not self._matches_any(f, patterns)]

    @staticmethod
    def _matches_any(filepath: str, patterns: list[str]) -> bool:
        """Check if a filepath matches any of the ignore patterns."""
        parts = Path(filepath).parts
        for p in patterns:
            if fnmatch.fnmatch(filepath, p):
                return True
            if any(fnmatch.fnmatch(part, p) for part in parts):
                return True
        return False

    def _display_changes(self, console: object, relevant: list[str]) -> None:
        """Display changed files in the terminal.

        Args:
            console: Rich Console instance.
            relevant: List of changed file paths.
        """
        from rich.console import Console as RichConsole

        assert isinstance(console, RichConsole)

        display_files = relevant[:MAX_CHANGED_FILES_DISPLAY]
        extra = len(relevant) - MAX_CHANGED_FILES_DISPLAY
        suffix = f"... (+{extra} more)" if extra > 0 else ""
        console.print(f"\n[dim]Changed: {', '.join(display_files)}{suffix}[/dim]")
