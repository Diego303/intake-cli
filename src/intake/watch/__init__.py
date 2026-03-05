"""Watch mode — monitor project files and re-run verification on changes.

Requires: pip install intake-ai-cli[watch]
"""

from __future__ import annotations

__all__ = ["WatchError"]


class WatchError(Exception):
    """Error during watch mode operations.

    Attributes:
        reason: Human-readable explanation.
        suggestion: Optional hint for the user.
    """

    def __init__(self, reason: str, suggestion: str = "") -> None:
        self.reason = reason
        self.suggestion = suggestion
        msg = f"Watch error: {reason}"
        if suggestion:
            msg += f"\n  Hint: {suggestion}"
        super().__init__(msg)
