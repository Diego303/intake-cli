"""Tests for analyze/risks.py — risk assessment parsing."""

from __future__ import annotations

from intake.analyze.risks import parse_risks


def _sample_risk_json() -> dict:
    """Return a realistic LLM risk assessment response."""
    return {
        "risks": [
            {
                "id": "RISK-01",
                "requirement_ids": ["FR-01", "NFR-03"],
                "description": "JWT token expiry may cause session issues",
                "probability": "medium",
                "impact": "high",
                "category": "security",
                "mitigation": "Implement token refresh mechanism",
            },
            {
                "id": "RISK-02",
                "requirement_ids": ["FR-02"],
                "description": "Email delivery latency",
                "probability": "low",
                "impact": "medium",
                "category": "integration",
                "mitigation": "Use async email queue with retry",
            },
        ]
    }


class TestParseRisks:
    """Tests for parse_risks()."""

    def test_parses_valid_risks(self) -> None:
        risks = parse_risks(_sample_risk_json())
        assert len(risks) == 2
        assert risks[0].id == "RISK-01"
        assert risks[0].probability == "medium"
        assert risks[0].impact == "high"
        assert risks[0].category == "security"

    def test_parses_requirement_ids(self) -> None:
        risks = parse_risks(_sample_risk_json())
        assert risks[0].requirement_ids == ["FR-01", "NFR-03"]

    def test_handles_empty_json(self) -> None:
        risks = parse_risks({})
        assert risks == []

    def test_filters_risk_without_description(self) -> None:
        raw = {
            "risks": [
                {
                    "id": "RISK-01",
                    "requirement_ids": ["FR-01"],
                    "description": "",
                    "probability": "medium",
                    "impact": "high",
                    "category": "technical",
                    "mitigation": "Some fix",
                }
            ]
        }
        risks = parse_risks(raw)
        assert len(risks) == 0

    def test_filters_risk_without_mitigation(self) -> None:
        raw = {
            "risks": [
                {
                    "id": "RISK-01",
                    "requirement_ids": ["FR-01"],
                    "description": "Some risk",
                    "probability": "medium",
                    "impact": "high",
                    "category": "technical",
                    "mitigation": "",
                }
            ]
        }
        risks = parse_risks(raw)
        assert len(risks) == 0

    def test_handles_missing_requirement_ids(self) -> None:
        raw = {
            "risks": [
                {
                    "id": "RISK-01",
                    "description": "Some risk",
                    "probability": "low",
                    "impact": "low",
                    "category": "scope",
                    "mitigation": "Monitor scope changes",
                }
            ]
        }
        risks = parse_risks(raw)
        assert len(risks) == 1
        assert risks[0].requirement_ids == []

    def test_defaults_to_medium_and_technical(self) -> None:
        raw = {
            "risks": [
                {
                    "id": "RISK-01",
                    "description": "Vague risk",
                    "mitigation": "Fix it",
                }
            ]
        }
        risks = parse_risks(raw)
        assert len(risks) == 1
        assert risks[0].probability == "medium"
        assert risks[0].impact == "medium"
        assert risks[0].category == "technical"
