"""Tests for analyze/extraction.py — parsing LLM JSON into typed models."""

from __future__ import annotations

from intake.analyze.extraction import parse_extraction


def _sample_extraction_json() -> dict:
    """Return a realistic LLM extraction response."""
    return {
        "functional_requirements": [
            {
                "id": "FR-01",
                "title": "User login",
                "description": (
                    "When a user submits credentials, "
                    "the system shall authenticate and return a session token."
                ),
                "acceptance_criteria": [
                    "AC-01.1: Valid credentials return 200",
                    "AC-01.2: Invalid credentials return 401",
                ],
                "source": "Source 1",
                "priority": "high",
            },
            {
                "id": "FR-02",
                "title": "Password reset",
                "description": (
                    "When a user requests a password reset, the system shall send an email."
                ),
                "acceptance_criteria": ["AC-02.1: Email sent within 30 seconds"],
                "source": "Source 1",
                "priority": "medium",
            },
        ],
        "non_functional_requirements": [
            {
                "id": "NFR-01",
                "title": "Response time",
                "description": "The system shall respond to API requests within 200ms p95.",
                "acceptance_criteria": ["AC-NFR-01.1: p95 latency < 200ms"],
                "source": "Source 1",
                "priority": "high",
            },
        ],
        "conflicts": [
            {
                "id": "CONFLICT-01",
                "description": "Auth method disagreement",
                "source_a": {"source": "Source 1", "says": "Use JWT"},
                "source_b": {"source": "Source 2", "says": "Use sessions"},
                "recommendation": "Use JWT for statelessness",
                "severity": "medium",
            },
        ],
        "open_questions": [
            {
                "id": "Q-01",
                "question": "What OAuth providers should be supported?",
                "context": "Requirements mention OAuth but no providers specified",
                "source": "Source 1",
                "recommendation": "Clarify with stakeholders",
            },
        ],
        "dependencies": ["authlib", "redis"],
    }


class TestParseExtraction:
    """Tests for parse_extraction()."""

    def test_parses_functional_requirements(self) -> None:
        result = parse_extraction(_sample_extraction_json())
        assert len(result.functional_requirements) == 2
        assert result.functional_requirements[0].id == "FR-01"
        assert result.functional_requirements[0].type == "functional"
        assert result.functional_requirements[0].priority == "high"

    def test_parses_non_functional_requirements(self) -> None:
        result = parse_extraction(_sample_extraction_json())
        assert len(result.non_functional_requirements) == 1
        assert result.non_functional_requirements[0].id == "NFR-01"
        assert result.non_functional_requirements[0].type == "non_functional"

    def test_parses_conflicts(self) -> None:
        result = parse_extraction(_sample_extraction_json())
        assert len(result.conflicts) == 1
        assert result.conflicts[0].id == "CONFLICT-01"
        assert result.conflicts[0].source_a["source"] == "Source 1"

    def test_parses_open_questions(self) -> None:
        result = parse_extraction(_sample_extraction_json())
        assert len(result.open_questions) == 1
        assert result.open_questions[0].id == "Q-01"
        assert "OAuth" in result.open_questions[0].question

    def test_parses_acceptance_criteria(self) -> None:
        result = parse_extraction(_sample_extraction_json())
        req = result.functional_requirements[0]
        assert len(req.acceptance_criteria) == 2
        assert "AC-01.1" in req.acceptance_criteria[0]

    def test_handles_empty_json(self) -> None:
        result = parse_extraction({})
        assert len(result.functional_requirements) == 0
        assert len(result.non_functional_requirements) == 0
        assert len(result.conflicts) == 0
        assert len(result.open_questions) == 0

    def test_handles_missing_fields_gracefully(self) -> None:
        raw = {
            "functional_requirements": [
                {"id": "FR-01"}  # Missing most fields
            ]
        }
        result = parse_extraction(raw)
        assert len(result.functional_requirements) == 1
        req = result.functional_requirements[0]
        assert req.id == "FR-01"
        assert req.title == ""
        assert req.priority == "medium"

    def test_all_requirements_property(self) -> None:
        result = parse_extraction(_sample_extraction_json())
        all_reqs = result.all_requirements
        assert len(all_reqs) == 3

    def test_requirement_count_property(self) -> None:
        result = parse_extraction(_sample_extraction_json())
        assert result.requirement_count == 3
