"""Base protocol and exceptions for exporters."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


class ExportError(Exception):
    """Error during spec export."""

    def __init__(self, reason: str, suggestion: str = "") -> None:
        self.reason = reason
        self.suggestion = suggestion
        msg = f"Export failed: {reason}"
        if suggestion:
            msg += f"\n  Hint: {suggestion}"
        super().__init__(msg)


@runtime_checkable
class Exporter(Protocol):
    """Protocol for spec exporters.

    Each exporter transforms a spec directory into an agent-ready format.
    """

    def export(self, spec_dir: str, output_dir: str) -> list[str]:
        """Export a spec to the target format.

        Args:
            spec_dir: Path to the spec directory (contains the 6 spec files).
            output_dir: Path to write exported files.

        Returns:
            List of generated file paths.
        """
        ...
