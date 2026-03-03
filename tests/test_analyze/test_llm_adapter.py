"""Tests for llm/adapter.py — LLM wrapper with mocked litellm."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from intake.config.schema import LLMConfig
from intake.llm import APIKeyMissingError, CostLimitError, LLMAdapter, LLMError


def _make_response(
    content: str = "Hello",
    input_tokens: int = 10,
    output_tokens: int = 20,
) -> SimpleNamespace:
    """Create a mock LiteLLM response."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
        ),
    )


@pytest.fixture()
def _set_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the API key environment variable."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")


@pytest.mark.asyncio
@pytest.mark.usefixtures("_set_api_key")
async def test_completion_returns_text() -> None:
    """Text mode returns raw string content."""
    config = LLMConfig()
    adapter = LLMAdapter(config)
    mock_response = _make_response("Hello world")

    with (
        patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response),
        patch("litellm.completion_cost", return_value=0.001),
    ):
        result = await adapter.completion(
            system_prompt="You are helpful.",
            user_prompt="Say hello.",
        )

    assert result == "Hello world"
    assert adapter.call_count == 1


@pytest.mark.asyncio
@pytest.mark.usefixtures("_set_api_key")
async def test_completion_returns_json() -> None:
    """JSON mode returns parsed dict."""
    config = LLMConfig()
    adapter = LLMAdapter(config)
    mock_response = _make_response('{"key": "value"}')

    with (
        patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response),
        patch("litellm.completion_cost", return_value=0.001),
    ):
        result = await adapter.completion(
            system_prompt="Return JSON.",
            user_prompt="Give me data.",
            response_format="json",
        )

    assert isinstance(result, dict)
    assert result["key"] == "value"


@pytest.mark.asyncio
@pytest.mark.usefixtures("_set_api_key")
async def test_completion_strips_json_fences() -> None:
    """JSON mode strips markdown code fences."""
    config = LLMConfig()
    adapter = LLMAdapter(config)
    mock_response = _make_response('```json\n{"key": "value"}\n```')

    with (
        patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response),
        patch("litellm.completion_cost", return_value=0.001),
    ):
        result = await adapter.completion(
            system_prompt="Return JSON.",
            user_prompt="Give me data.",
            response_format="json",
        )

    assert isinstance(result, dict)
    assert result["key"] == "value"


@pytest.mark.asyncio
@pytest.mark.usefixtures("_set_api_key")
async def test_tracks_token_usage() -> None:
    """Token counts are accumulated across calls."""
    config = LLMConfig()
    adapter = LLMAdapter(config)
    mock_response = _make_response("OK", input_tokens=100, output_tokens=50)

    with (
        patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response),
        patch("litellm.completion_cost", return_value=0.005),
    ):
        await adapter.completion(system_prompt="Test", user_prompt="Test")
        await adapter.completion(system_prompt="Test", user_prompt="Test")

    assert adapter.total_input_tokens == 200
    assert adapter.total_output_tokens == 100
    assert adapter.call_count == 2


@pytest.mark.asyncio
async def test_raises_on_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """APIKeyMissingError when env var is not set."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    config = LLMConfig()
    adapter = LLMAdapter(config)

    with pytest.raises(APIKeyMissingError, match="ANTHROPIC_API_KEY"):
        await adapter.completion(system_prompt="Test", user_prompt="Test")


@pytest.mark.asyncio
@pytest.mark.usefixtures("_set_api_key")
async def test_raises_cost_limit_error() -> None:
    """CostLimitError when budget is exceeded."""
    config = LLMConfig(max_cost_per_spec=0.01)
    adapter = LLMAdapter(config)
    mock_response = _make_response("OK")

    with (
        patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response),
        patch("litellm.completion_cost", return_value=0.02),
        pytest.raises(CostLimitError),
    ):
        await adapter.completion(system_prompt="Test", user_prompt="Test")


@pytest.mark.asyncio
@pytest.mark.usefixtures("_set_api_key")
async def test_retries_on_failure() -> None:
    """Retries on transient errors, succeeds on final attempt."""
    config = LLMConfig(max_retries=3)
    adapter = LLMAdapter(config)
    mock_response = _make_response("OK")

    call_count = {"n": 0}

    async def flaky_completion(**kwargs: object) -> SimpleNamespace:
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise ConnectionError("Transient failure")
        return mock_response

    with (
        patch("litellm.acompletion", new_callable=AsyncMock, side_effect=flaky_completion),
        patch("litellm.completion_cost", return_value=0.001),
    ):
        result = await adapter.completion(
            system_prompt="Test",
            user_prompt="Test",
        )

    assert result == "OK"
    assert call_count["n"] == 3


@pytest.mark.asyncio
@pytest.mark.usefixtures("_set_api_key")
async def test_raises_llm_error_after_all_retries() -> None:
    """LLMError after exhausting retries."""
    config = LLMConfig(max_retries=2)
    adapter = LLMAdapter(config)

    with (
        patch(
            "litellm.acompletion",
            new_callable=AsyncMock,
            side_effect=ConnectionError("Persistent failure"),
        ),
        pytest.raises(LLMError, match="2 attempts"),
    ):
        await adapter.completion(system_prompt="Test", user_prompt="Test")
