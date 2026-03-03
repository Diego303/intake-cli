"""Tests for analyze/analyzer.py — the main orchestrator.

All LLM calls are mocked. No network calls in tests.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from intake.analyze.analyzer import AnalyzeError, Analyzer
from intake.config.schema import IntakeConfig
from intake.ingest.base import ParsedContent
from intake.llm import LLMAdapter


def _sample_extraction_response() -> dict:
    """LLM response for the extraction phase."""
    return {
        "functional_requirements": [
            {
                "id": "FR-01",
                "title": "User authentication",
                "description": (
                    "When a user submits credentials, the system shall validate and return a token."
                ),
                "acceptance_criteria": ["AC-01.1: Returns JWT on valid login"],
                "source": "Source 1",
                "priority": "high",
            },
        ],
        "non_functional_requirements": [
            {
                "id": "NFR-01",
                "title": "Response time",
                "description": "API responds within 200ms p95.",
                "acceptance_criteria": ["AC-NFR-01.1: p95 < 200ms"],
                "source": "Source 1",
                "priority": "medium",
            },
        ],
        "conflicts": [],
        "open_questions": [
            {
                "id": "Q-01",
                "question": "Which OAuth providers?",
                "context": "Not specified in sources",
                "source": "Source 1",
                "recommendation": "Ask stakeholders",
            },
        ],
        "dependencies": ["pyjwt"],
    }


def _sample_risk_response() -> dict:
    """LLM response for the risk assessment phase."""
    return {
        "risks": [
            {
                "id": "RISK-01",
                "requirement_ids": ["FR-01"],
                "description": "Token security risk",
                "probability": "medium",
                "impact": "high",
                "category": "security",
                "mitigation": "Use short-lived tokens with refresh",
            },
        ]
    }


def _sample_design_response() -> dict:
    """LLM response for the design phase."""
    return {
        "components": ["auth-module"],
        "files_to_create": [{"path": "src/auth.py", "description": "Auth handler"}],
        "files_to_modify": [],
        "tech_decisions": [
            {
                "decision": "Use JWT",
                "justification": "Stateless auth",
                "requirement": "FR-01",
            }
        ],
        "tasks": [
            {
                "id": 1,
                "title": "Create auth module",
                "description": "Implement JWT authentication",
                "files": ["src/auth.py"],
                "dependencies": [],
                "checks": ["pytest tests/test_auth.py"],
                "estimated_minutes": 20,
            }
        ],
        "acceptance_checks": [
            {
                "id": "tests-pass",
                "name": "Tests pass",
                "type": "command",
                "command": "pytest -q",
                "required": True,
                "tags": ["test"],
            }
        ],
        "dependencies": ["pyjwt"],
    }


def _make_source(text: str = "Build a user auth system", source: str = "reqs.md") -> ParsedContent:
    """Create a test ParsedContent."""
    return ParsedContent(
        text=text,
        format="markdown",
        source=source,
        metadata={},
        sections=[{"title": "Requirements", "content": text}],
    )


def _make_mock_llm() -> LLMAdapter:
    """Create a mock LLM adapter that returns canned responses."""
    config = IntakeConfig().llm
    llm = LLMAdapter(config)

    responses = [
        _sample_extraction_response(),
        _sample_risk_response(),
        _sample_design_response(),
    ]
    call_index = {"i": 0}

    async def mock_completion(**kwargs: object) -> dict:
        idx = call_index["i"]
        call_index["i"] += 1
        return responses[idx] if idx < len(responses) else {}

    llm.completion = AsyncMock(side_effect=mock_completion)  # type: ignore[method-assign]
    return llm


@pytest.mark.asyncio
async def test_analyzer_produces_complete_result() -> None:
    """End-to-end: single source → valid AnalysisResult."""
    config = IntakeConfig()
    llm = _make_mock_llm()
    analyzer = Analyzer(config=config, llm=llm)

    sources = [_make_source()]
    result = await analyzer.analyze(sources)

    assert len(result.functional_requirements) == 1
    assert result.functional_requirements[0].id == "FR-01"
    assert len(result.non_functional_requirements) == 1
    assert len(result.open_questions) == 1
    assert result.requirement_count == 2


@pytest.mark.asyncio
async def test_analyzer_calls_risk_assessment() -> None:
    """Risk assessment is called when config.spec.risk_assessment=True."""
    config = IntakeConfig()
    llm = _make_mock_llm()
    analyzer = Analyzer(config=config, llm=llm)

    sources = [_make_source()]
    result = await analyzer.analyze(sources)

    assert len(result.risks) == 1
    assert result.risks[0].id == "RISK-01"
    assert result.risks[0].category == "security"


@pytest.mark.asyncio
async def test_analyzer_skips_risk_when_disabled() -> None:
    """Risk assessment is skipped when config.spec.risk_assessment=False."""
    config = IntakeConfig()
    config.spec.risk_assessment = False
    llm = _make_mock_llm()
    analyzer = Analyzer(config=config, llm=llm)

    sources = [_make_source()]
    result = await analyzer.analyze(sources)

    assert result.risks == []
    # Only 2 calls: extraction + design (no risk)
    assert llm.completion.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_analyzer_produces_design() -> None:
    """Design phase produces tasks and acceptance checks."""
    config = IntakeConfig()
    llm = _make_mock_llm()
    analyzer = Analyzer(config=config, llm=llm)

    sources = [_make_source()]
    result = await analyzer.analyze(sources)

    assert len(result.design.tasks) == 1
    assert result.design.tasks[0].title == "Create auth module"
    assert len(result.design.acceptance_checks) == 1
    assert result.task_count == 1


@pytest.mark.asyncio
async def test_analyzer_combines_multiple_sources() -> None:
    """Multiple sources are combined with headers."""
    config = IntakeConfig()
    llm = _make_mock_llm()
    analyzer = Analyzer(config=config, llm=llm)

    sources = [
        _make_source("Auth requirements", "auth.md"),
        _make_source("Payment requirements", "pay.md"),
    ]
    await analyzer.analyze(sources)

    # Verify the extraction call received combined text
    call_args = llm.completion.call_args_list[0]  # type: ignore[attr-defined]
    user_prompt = call_args.kwargs.get("user_prompt", call_args[1].get("user_prompt", ""))
    assert "SOURCE 1" in user_prompt
    assert "SOURCE 2" in user_prompt


@pytest.mark.asyncio
async def test_analyzer_raises_on_empty_sources() -> None:
    """AnalyzeError raised when no sources are provided."""
    config = IntakeConfig()
    llm = _make_mock_llm()
    analyzer = Analyzer(config=config, llm=llm)

    with pytest.raises(AnalyzeError, match="No sources provided"):
        await analyzer.analyze([])


@pytest.mark.asyncio
async def test_analyzer_sets_metadata() -> None:
    """Result includes model_used from config."""
    config = IntakeConfig()
    llm = _make_mock_llm()
    analyzer = Analyzer(config=config, llm=llm)

    sources = [_make_source()]
    result = await analyzer.analyze(sources)

    assert result.model_used == config.llm.model
