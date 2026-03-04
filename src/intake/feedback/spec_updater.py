"""Apply spec amendments proposed by the feedback analyzer.

Provides preview and apply modes for proposed spec changes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from intake.feedback.analyzer import FeedbackResult, SpecAmendment

logger = structlog.get_logger()


class SpecUpdateError(Exception):
    """Error when applying a spec amendment."""

    def __init__(self, reason: str, suggestion: str = "") -> None:
        self.reason = reason
        self.suggestion = suggestion
        msg = f"Spec update error: {reason}"
        if suggestion:
            msg += f"\n  Hint: {suggestion}"
        super().__init__(msg)


@dataclass
class AmendmentPreview:
    """Preview of a proposed spec amendment.

    Attributes:
        amendment: The proposed amendment.
        current_content: Current content of the section (if found).
        proposed_content: What the section would look like after.
        applicable: Whether the amendment can be applied.
        reason: Why it can/cannot be applied.
    """

    amendment: SpecAmendment
    current_content: str
    proposed_content: str
    applicable: bool
    reason: str


@dataclass
class ApplyResult:
    """Result of applying spec amendments.

    Attributes:
        applied: Number of amendments successfully applied.
        skipped: Number of amendments skipped.
        details: Per-amendment status messages.
    """

    applied: int = 0
    skipped: int = 0
    details: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.details is None:
            self.details = []


class SpecUpdater:
    """Preview and apply spec amendments from feedback analysis.

    Args:
        spec_dir: Path to the spec directory to modify.
    """

    def __init__(self, spec_dir: str) -> None:
        self.spec_path = Path(spec_dir)
        if not self.spec_path.is_dir():
            raise SpecUpdateError(
                reason=f"Spec directory not found: {spec_dir}",
                suggestion="Provide a valid path to an existing spec directory.",
            )

    def preview(self, result: FeedbackResult) -> list[AmendmentPreview]:
        """Preview all proposed amendments without applying them.

        Args:
            result: FeedbackResult containing amendments.

        Returns:
            List of AmendmentPreview objects.
        """
        previews: list[AmendmentPreview] = []
        for failure in result.failures:
            if failure.spec_amendment is None:
                continue
            preview = self._preview_amendment(failure.spec_amendment)
            previews.append(preview)
        return previews

    def apply(self, result: FeedbackResult) -> ApplyResult:
        """Apply all applicable amendments to spec files.

        Args:
            result: FeedbackResult containing amendments.

        Returns:
            ApplyResult with counts and details.
        """
        apply_result = ApplyResult()

        for failure in result.failures:
            if failure.spec_amendment is None:
                continue

            amendment = failure.spec_amendment
            preview = self._preview_amendment(amendment)

            if not preview.applicable:
                apply_result.skipped += 1
                apply_result.details.append(
                    f"Skipped {amendment.target_file}/{amendment.section}: {preview.reason}"
                )
                continue

            try:
                self._apply_amendment(amendment)
                apply_result.applied += 1
                apply_result.details.append(
                    f"Applied {amendment.action} to {amendment.target_file}/{amendment.section}"
                )
                logger.info(
                    "spec_amendment_applied",
                    file=amendment.target_file,
                    section=amendment.section,
                    action=amendment.action,
                )
            except SpecUpdateError as e:
                apply_result.skipped += 1
                apply_result.details.append(
                    f"Failed {amendment.target_file}/{amendment.section}: {e.reason}"
                )

        return apply_result

    def _preview_amendment(self, amendment: SpecAmendment) -> AmendmentPreview:
        """Generate a preview for a single amendment.

        Args:
            amendment: The proposed amendment.

        Returns:
            AmendmentPreview with current and proposed content.
        """
        target_path = self.spec_path / amendment.target_file
        if not target_path.exists():
            if amendment.action == "add":
                return AmendmentPreview(
                    amendment=amendment,
                    current_content="",
                    proposed_content=amendment.content,
                    applicable=True,
                    reason="File will be created with new section.",
                )
            return AmendmentPreview(
                amendment=amendment,
                current_content="",
                proposed_content="",
                applicable=False,
                reason=f"Target file {amendment.target_file} does not exist.",
            )

        content = target_path.read_text(encoding="utf-8")
        current_section = self._find_section(content, amendment.section)

        if amendment.action == "add":
            return AmendmentPreview(
                amendment=amendment,
                current_content="",
                proposed_content=amendment.content,
                applicable=True,
                reason="New section will be appended.",
            )
        elif amendment.action == "remove":
            if not current_section:
                return AmendmentPreview(
                    amendment=amendment,
                    current_content="",
                    proposed_content="",
                    applicable=False,
                    reason=f"Section '{amendment.section}' not found in file.",
                )
            return AmendmentPreview(
                amendment=amendment,
                current_content=current_section,
                proposed_content="",
                applicable=True,
                reason="Section will be removed.",
            )
        else:  # modify
            return AmendmentPreview(
                amendment=amendment,
                current_content=current_section,
                proposed_content=amendment.content,
                applicable=True,
                reason="Section will be updated." if current_section else "Section will be added.",
            )

    def _apply_amendment(self, amendment: SpecAmendment) -> None:
        """Apply a single amendment to a spec file.

        Args:
            amendment: The amendment to apply.

        Raises:
            SpecUpdateError: If the amendment cannot be applied.
        """
        target_path = self.spec_path / amendment.target_file

        if amendment.action == "add":
            if target_path.exists():
                content = target_path.read_text(encoding="utf-8")
                if not content.endswith("\n"):
                    content += "\n"
                content += f"\n{amendment.content}\n"
                target_path.write_text(content, encoding="utf-8")
            else:
                target_path.write_text(amendment.content + "\n", encoding="utf-8")
            return

        if not target_path.exists():
            raise SpecUpdateError(
                reason=f"Cannot {amendment.action} in nonexistent file: {amendment.target_file}",
            )

        content = target_path.read_text(encoding="utf-8")

        if amendment.action == "remove":
            updated = self._remove_section(content, amendment.section)
            target_path.write_text(updated, encoding="utf-8")
        elif amendment.action == "modify":
            updated = self._replace_section(
                content,
                amendment.section,
                amendment.content,
            )
            target_path.write_text(updated, encoding="utf-8")

    def _find_section(self, content: str, section_id: str) -> str:
        """Find a section by its heading ID in Markdown content.

        Args:
            content: Full file content.
            section_id: Section identifier (e.g., "FR-001").

        Returns:
            Section content including heading, or empty string if not found.
        """
        pattern = self._section_pattern(section_id)
        match = pattern.search(content)
        if match:
            return match.group(0).strip()
        return ""

    def _remove_section(self, content: str, section_id: str) -> str:
        """Remove a section from Markdown content.

        Args:
            content: Full file content.
            section_id: Section identifier to remove.

        Returns:
            Content with section removed.
        """
        pattern = self._section_pattern(section_id)
        result = pattern.sub("", content)
        # Clean up extra blank lines
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result.strip() + "\n"

    def _replace_section(
        self,
        content: str,
        section_id: str,
        new_content: str,
    ) -> str:
        """Replace a section in Markdown content, or append if not found.

        Args:
            content: Full file content.
            section_id: Section identifier to replace.
            new_content: New section content.

        Returns:
            Updated content.
        """
        pattern = self._section_pattern(section_id)
        if pattern.search(content):
            return pattern.sub(new_content + "\n\n", content)

        # Section not found — append
        if not content.endswith("\n"):
            content += "\n"
        return content + f"\n{new_content}\n"

    def _section_pattern(self, section_id: str) -> re.Pattern[str]:
        """Build a regex pattern that matches a markdown section by ID.

        Matches from the heading containing section_id up to (but not
        including) the next heading of same or higher level, or EOF.

        Args:
            section_id: Section identifier to match.

        Returns:
            Compiled regex pattern.
        """
        return re.compile(
            rf"^(#{{2,3}}\s+.*{re.escape(section_id)}.*\n)"
            rf"((?:(?!^#{{2,3}}\s).*\n?)*)",
            re.MULTILINE,
        )
