"""Spec comparison between two versions.

Compares requirements, tasks, and acceptance checks by ID.
Detects added, removed, and modified items.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import structlog
import yaml

logger = structlog.get_logger()


class DiffError(Exception):
    """Error during spec comparison."""

    def __init__(self, reason: str, suggestion: str = "") -> None:
        self.reason = reason
        self.suggestion = suggestion
        msg = f"Diff failed: {reason}"
        if suggestion:
            msg += f"\n  Hint: {suggestion}"
        super().__init__(msg)


@dataclass
class DiffEntry:
    """A single change between two spec versions."""

    section: str  # "requirements" | "tasks" | "acceptance" | "design"
    change_type: str  # "added" | "removed" | "modified"
    item_id: str  # e.g., "FR-01", "task-3"
    old_value: str = ""
    new_value: str = ""
    summary: str = ""


@dataclass
class SpecDiff:
    """Result of comparing two spec versions."""

    spec_a: str
    spec_b: str
    changes: list[DiffEntry] = field(default_factory=list)

    @property
    def added(self) -> list[DiffEntry]:
        """Items present in spec_b but not in spec_a."""
        return [c for c in self.changes if c.change_type == "added"]

    @property
    def removed(self) -> list[DiffEntry]:
        """Items present in spec_a but not in spec_b."""
        return [c for c in self.changes if c.change_type == "removed"]

    @property
    def modified(self) -> list[DiffEntry]:
        """Items present in both but with different content."""
        return [c for c in self.changes if c.change_type == "modified"]

    @property
    def has_changes(self) -> bool:
        """True if there are any differences."""
        return len(self.changes) > 0


class SpecDiffer:
    """Compare two spec versions and report differences.

    Compares:
    - requirements.md: added/removed/modified requirements (by FR/NFR ID)
    - tasks.md: added/removed/modified tasks (by task number)
    - acceptance.yaml: added/removed checks (by check ID)
    """

    def diff(
        self,
        spec_a_dir: str,
        spec_b_dir: str,
        sections: list[str] | None = None,
    ) -> SpecDiff:
        """Compare two spec directories.

        Args:
            spec_a_dir: Path to the first (older) spec directory.
            spec_b_dir: Path to the second (newer) spec directory.
            sections: Sections to compare. Defaults to all.

        Returns:
            SpecDiff with all detected changes.

        Raises:
            DiffError: If a spec directory does not exist.
        """
        path_a = Path(spec_a_dir)
        path_b = Path(spec_b_dir)

        if not path_a.exists():
            raise DiffError(
                reason=f"Spec directory not found: {spec_a_dir}",
                suggestion="Check the path and try again.",
            )
        if not path_b.exists():
            raise DiffError(
                reason=f"Spec directory not found: {spec_b_dir}",
                suggestion="Check the path and try again.",
            )

        result = SpecDiff(spec_a=spec_a_dir, spec_b=spec_b_dir)

        target_sections = sections or [
            "requirements",
            "tasks",
            "acceptance",
        ]

        if "requirements" in target_sections:
            result.changes.extend(
                self._diff_markdown_by_ids(
                    path_a / "requirements.md",
                    path_b / "requirements.md",
                    section="requirements",
                    id_pattern=r"^###?\s+((?:FR|NFR)-\d+)",
                )
            )

        if "tasks" in target_sections:
            result.changes.extend(
                self._diff_markdown_by_ids(
                    path_a / "tasks.md",
                    path_b / "tasks.md",
                    section="tasks",
                    id_pattern=r"^###?\s+(?:Task\s+)?(\d+)",
                )
            )

        if "acceptance" in target_sections:
            result.changes.extend(
                self._diff_acceptance(
                    path_a / "acceptance.yaml",
                    path_b / "acceptance.yaml",
                )
            )

        logger.info(
            "spec_diff_complete",
            spec_a=spec_a_dir,
            spec_b=spec_b_dir,
            added=len(result.added),
            removed=len(result.removed),
            modified=len(result.modified),
        )

        return result

    def _diff_markdown_by_ids(
        self,
        file_a: Path,
        file_b: Path,
        section: str,
        id_pattern: str,
    ) -> list[DiffEntry]:
        """Compare two markdown files by extracting sections with IDs.

        Args:
            file_a: Path to the first markdown file.
            file_b: Path to the second markdown file.
            section: Section name for DiffEntry (e.g., "requirements").
            id_pattern: Regex to extract section IDs from headings.

        Returns:
            List of DiffEntry for added/removed/modified items.
        """
        items_a = self._extract_sections(file_a, id_pattern) if file_a.exists() else {}
        items_b = self._extract_sections(file_b, id_pattern) if file_b.exists() else {}

        changes: list[DiffEntry] = []

        # Check for added and modified items
        for item_id in items_b:
            if item_id not in items_a:
                changes.append(
                    DiffEntry(
                        section=section,
                        change_type="added",
                        item_id=item_id,
                        new_value=items_b[item_id],
                        summary=f"Added {item_id}",
                    )
                )
            elif items_a[item_id] != items_b[item_id]:
                changes.append(
                    DiffEntry(
                        section=section,
                        change_type="modified",
                        item_id=item_id,
                        old_value=items_a[item_id],
                        new_value=items_b[item_id],
                        summary=f"Modified {item_id}",
                    )
                )

        # Check for removed items
        for item_id in items_a:
            if item_id not in items_b:
                changes.append(
                    DiffEntry(
                        section=section,
                        change_type="removed",
                        item_id=item_id,
                        old_value=items_a[item_id],
                        summary=f"Removed {item_id}",
                    )
                )

        return changes

    def _diff_acceptance(
        self,
        file_a: Path,
        file_b: Path,
    ) -> list[DiffEntry]:
        """Compare two acceptance.yaml files by check ID.

        Args:
            file_a: Path to the first acceptance.yaml.
            file_b: Path to the second acceptance.yaml.

        Returns:
            List of DiffEntry for added/removed checks.
        """
        checks_a = self._load_checks(file_a) if file_a.exists() else {}
        checks_b = self._load_checks(file_b) if file_b.exists() else {}

        changes: list[DiffEntry] = []

        for check_id in checks_b:
            if check_id not in checks_a:
                changes.append(
                    DiffEntry(
                        section="acceptance",
                        change_type="added",
                        item_id=check_id,
                        summary=f"Added check: {check_id}",
                    )
                )

        for check_id in checks_a:
            if check_id not in checks_b:
                changes.append(
                    DiffEntry(
                        section="acceptance",
                        change_type="removed",
                        item_id=check_id,
                        summary=f"Removed check: {check_id}",
                    )
                )

        return changes

    def _extract_sections(
        self,
        path: Path,
        id_pattern: str,
    ) -> dict[str, str]:
        """Extract sections from markdown keyed by matched ID.

        Args:
            path: Path to the markdown file.
            id_pattern: Regex with one capture group for the ID.

        Returns:
            Dict mapping section ID to section content.
        """
        content = path.read_text(errors="ignore")
        sections: dict[str, str] = {}
        current_id: str | None = None
        current_lines: list[str] = []

        for line in content.splitlines():
            match = re.match(id_pattern, line)
            if match:
                if current_id is not None:
                    sections[current_id] = "\n".join(current_lines).strip()
                current_id = match.group(1)
                current_lines = [line]
            elif current_id is not None:
                current_lines.append(line)

        if current_id is not None:
            sections[current_id] = "\n".join(current_lines).strip()

        return sections

    def _load_checks(self, path: Path) -> dict[str, dict[str, object]]:
        """Load acceptance checks keyed by ID.

        Args:
            path: Path to acceptance.yaml.

        Returns:
            Dict mapping check ID to check definition.
        """
        try:
            with open(path) as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError:
            return {}

        if not isinstance(data, dict):
            return {}

        checks = data.get("checks", [])
        if not isinstance(checks, list):
            return {}

        return {str(c["id"]): c for c in checks if isinstance(c, dict) and "id" in c}
