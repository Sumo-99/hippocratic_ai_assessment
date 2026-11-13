"""Direct Anthropic Messages API client (via the anthropic SDK).

Only `_call` lives here: the retry loop, validation, budget guard and usage callback come from
BaseLLMClient, so behaviour matches OpenRouterClient call for call.
"""
import os
import time
from typing import Any, Callable

import anthropic
from anthropic import AsyncAnthropic

from . import config
from .llm import BaseLLMClient, LLMError, RetryableError, _strict_schema


class AnthropicClient(BaseLLMClient):
    def __init__(self, api_key: str | None = None, on_usage: Callable | None = None):
        # .env was already loaded by config.py at import time.
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        super().__init__(on_usage)
        # DECISION: max_retries=0. BaseLLMClient already retries config.RETRIES times; the SDK's
        # own 2 retries inside that loop would multiply the attempts.
        self._client = AsyncAnthropic(api_key=key, max_retries=0)

    async def _call(self, system, user, schema, stage) -> str:
        self._check_budget()
        kwargs: dict[str, Any] = dict(
            model=config.ANTHROPIC_MODEL,
            max_tokens=config.MAX_TOKENS,
            thinking=config.ANTHROPIC_THINKING,
            messages=[{"role": "user", "content": user}],
            # NOTE: no temperature (rejected by current models) and no effort (model default).
        )
        if system:  # baseline() sends no system prompt at all, like the original main.py
            kwargs["system"] = system
        if schema is not None:
            kwargs["output_config"] = {"format": {
                "type": "json_schema",
                "schema": _strict_schema(schema.model_json_schema()),
            }}
        start = time.monotonic()
        try:
            resp = await self._client.messages.create(**kwargs)
        except anthropic.APIStatusError as e:
            # DECISION: 4xx (except 429) is our bug, a bad key or a rejected schema; retrying
            # just burns time.
            if e.status_code < 500 and e.status_code != 429:
                raise LLMError(f"{stage}: HTTP {e.status_code}: {e}") from e
            raise RetryableError(e) from e
        except anthropic.APIError as e:  # connection, timeout
            raise RetryableError(e) from e
        seconds = time.monotonic() - start

        usage = resp.usage
        if usage is None:  # can't track spend without it, so fail loudly instead of guessing
            raise LLMError(f"{stage}: response had no usage data")
        cost = (usage.input_tokens * config.ANTHROPIC_PRICE_IN_PER_TOKEN
                + usage.output_tokens * config.ANTHROPIC_PRICE_OUT_PER_TOKEN)
        self._record_usage(stage, usage.input_tokens, usage.output_tokens, cost, seconds)

        if resp.stop_reason == "refusal":
            # DECISION: fatal, not retried. Haiku 5.5 has no server-side fallback, and the same
            # request would most likely be refused again (and billed again).
            category = getattr(resp.stop_details, "category", None)
            raise LLMError(f"{stage}: model refused (category: {category})")
        # Return the first text block; thinking or other blocks may come before it.
        return next((b.text for b in resp.content if b.type == "text"), "")
