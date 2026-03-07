"""Spec validation (quality gate) module.

Validates internal consistency of a generated spec without running
implementation code or making LLM calls. Purely offline checks.
"""

from __future__ import annotations

from intake.validate.checker import SpecValidator, ValidationIssue, ValidationReport

__all__ = ["SpecValidator", "ValidationIssue", "ValidationReport"]
