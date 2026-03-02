"""Phase 3 — Spec file generation from analysis results."""

from __future__ import annotations

from intake.generate.lock import SpecLock, create_lock
from intake.generate.spec_builder import GenerateError, SpecBuilder

__all__ = ["GenerateError", "SpecBuilder", "SpecLock", "create_lock"]
