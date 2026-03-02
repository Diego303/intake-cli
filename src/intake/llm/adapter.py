"""LiteLLM wrapper with retry, cost tracking, and timeouts.

All LLM calls in the application go through this adapter.
Never call litellm directly from any other module.

Principles:
- Provider-agnostic: any model LiteLLM supports
- Cost tracking: each call logs tokens and cost
- Retry with exponential backoff
- Configurable timeout
- Structured output: forces JSON when requested
- Budget enforcement: stops if max_cost_per_spec is exceeded
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from intake.config.schema import LLMConfig

logger = structlog.get_logger()


class LLMError(Exception):
    """Base exception for LLM adapter errors."""

    def __init__(self, reason: str, suggestion: str = "") -> None:
        self.reason = reason
        self.suggestion = suggestion
        msg = f"LLM error: {reason}"
        if suggestion:
            msg += f"\n  Hint: {suggestion}"
        super().__init__(msg)


class CostLimitError(LLMError):
    """Raised when accumulated cost exceeds the configured budget."""

    def __init__(self, accumulated: float, limit: float) -> None:
        self.accumulated = accumulated
        self.limit = limit
        super().__init__(
            reason=(
                f"Accumulated cost ${accumulated:.4f} exceeds limit "
                f"of ${limit:.2f}"
            ),
            suggestion=(
                "Increase llm.max_cost_per_spec in your config, "
                "or use a cheaper model."
            ),
        )


class APIKeyMissingError(LLMError):
    """Raised when the required API key environment variable is not set."""

    def __init__(self, env_var: str) -> None:
        self.env_var = env_var
        super().__init__(
            reason=f"Environment variable {env_var} is not set.",
            suggestion=f"Set it with: export {env_var}=your-api-key",
        )


class LLMAdapter:
    """Wrapper over LiteLLM with retry, cost tracking, and timeouts.

    Args:
        config: LLM configuration with model, retries, timeout, budget.
    """

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self.total_cost: float = 0.0
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self._call_count: int = 0

    async def completion(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: str = "text",
        max_tokens: int = 8000,
        phase: str = "",
    ) -> dict[str, object] | str:
        """Send a prompt to the LLM and return the response.

        Args:
            system_prompt: Instructions for the model.
            user_prompt: Content to analyze.
            response_format: ``"text"`` or ``"json"``.
            max_tokens: Maximum tokens in the response.
            phase: Pipeline phase name for cost tracking.

        Returns:
            If response_format="json": parsed dict.
            If response_format="text": response string.

        Raises:
            LLMError: If the LLM fails after all retries.
            CostLimitError: If max_cost_per_spec is exceeded.
            APIKeyMissingError: If the API key env var is not set.
        """
        self._check_api_key()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]


        for attempt in range(1, self.config.max_retries + 1):
            try:
                content = await self._call_llm(messages, max_tokens, attempt, phase)

                if response_format == "json":
                    return self._parse_json(content)

                return content

            except json.JSONDecodeError as e:
                logger.warning(
                    "json_parse_failed",
                    attempt=attempt,
                    error=str(e),
                    phase=phase,
                )
                if attempt == self.config.max_retries:
                    raise LLMError(
                        reason=(
                            f"LLM did not return valid JSON after "
                            f"{self.config.max_retries} attempts"
                        ),
                        suggestion="Try a different model or simplify the prompt.",
                    ) from e

            except CostLimitError:
                raise

            except LLMError:
                raise

            except Exception as e:
                logger.warning(
                    "llm_call_failed",
                    attempt=attempt,
                    error=str(e),
                    phase=phase,
                )
                if attempt == self.config.max_retries:
                    raise LLMError(
                        reason=f"LLM failed after {self.config.max_retries} attempts: {e}",
                        suggestion="Check your API key, network connection, and model name.",
                    ) from e

                await asyncio.sleep(2 ** (attempt - 1))

        raise LLMError(
            reason="Could not complete the LLM call",
            suggestion="Check logs for details.",
        )

    async def _call_llm(
        self,
        messages: list[dict[str, str]],
        max_tokens: int,
        attempt: int,
        phase: str,
    ) -> str:
        """Execute a single LLM call and track costs."""
        from litellm import acompletion

        response = await acompletion(
            model=self.config.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=self.config.temperature,
            timeout=self.config.timeout,
        )

        self._track_usage(response, phase)
        self._check_budget()

        content: str = response.choices[0].message.content or ""

        logger.debug(
            "llm_response",
            model=self.config.model,
            input_tokens=self.total_input_tokens,
            output_tokens=self.total_output_tokens,
            attempt=attempt,
            phase=phase,
        )

        return content

    def _track_usage(self, response: object, phase: str) -> None:
        """Extract token usage and cost from the LLM response."""
        usage = getattr(response, "usage", None)
        if usage is None:
            return

        input_tokens = getattr(usage, "prompt_tokens", 0) or 0
        output_tokens = getattr(usage, "completion_tokens", 0) or 0
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self._call_count += 1

        try:
            from litellm import completion_cost
            cost = completion_cost(completion_response=response)
            self.total_cost += cost
        except Exception:
            pass

    def _check_budget(self) -> None:
        """Raise CostLimitError if the accumulated cost exceeds the budget."""
        if self.total_cost > self.config.max_cost_per_spec:
            raise CostLimitError(
                accumulated=self.total_cost,
                limit=self.config.max_cost_per_spec,
            )

    def _check_api_key(self) -> None:
        """Verify that the required API key environment variable is set."""
        if not os.environ.get(self.config.api_key_env):
            raise APIKeyMissingError(env_var=self.config.api_key_env)

    def _parse_json(self, content: str) -> dict[str, object]:
        """Parse JSON from LLM response, stripping markdown fences."""
        clean = content.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        return json.loads(clean.strip())  # type: ignore[no-any-return]

    @property
    def call_count(self) -> int:
        """Number of LLM calls made."""
        return self._call_count
