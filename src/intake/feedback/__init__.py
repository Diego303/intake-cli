"""Feedback loop — analyze verification failures and suggest fixes.

This module analyzes failed acceptance checks, identifies root causes,
and produces actionable suggestions (optionally amending the spec).

Note: This module uses the LLM for analysis, which is a documented
exception to the rule that only ``analyze/`` talks to the LLM.
The feedback module analyzes failures, not requirements.
"""

from __future__ import annotations

from intake.feedback.analyzer import (
    FailureAnalysis,
    FeedbackAnalyzer,
    FeedbackError,
    FeedbackResult,
    SpecAmendment,
)
from intake.feedback.spec_updater import (
    AmendmentPreview,
    ApplyResult,
    SpecUpdateError,
    SpecUpdater,
)
from intake.feedback.suggestions import SuggestionFormatter

__all__ = [
    "AmendmentPreview",
    "ApplyResult",
    "FailureAnalysis",
    "FeedbackAnalyzer",
    "FeedbackError",
    "FeedbackResult",
    "SpecAmendment",
    "SpecUpdateError",
    "SpecUpdater",
    "SuggestionFormatter",
]
