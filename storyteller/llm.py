"""Anthropic Messages API client (via the anthropic SDK) with retries, usage capture and a
budget guard. pipeline.py makes one per turn; everything else sees LLMClient."""
import asyncio
import os
import time
from typing import Any, Callable, Protocol, TypeVar

import anthropic
from anthropic import AsyncAnthropic
from pydantic import BaseModel, ValidationError

from . import config

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """A call failed for good (retries used up, or a non-retryable error)."""


class BudgetExceeded(Exception):
    """The summed cost of this run passed config.MAX_RUN_COST_USD."""


class LLMClient(Protocol):
    async def text(self, system: str, user: str, *, stage: str) -> str: ...
    async def structured(self, system: str, user: str, schema: type[T], *, stage: str) -> T: ...


def _strict_schema(node: Any) -> Any:
    """Make pydantic's JSON schema acceptable to strict mode: every object gets
    additionalProperties=false and lists all its properties as required; 'default' is dropped."""
    # DECISION: post-process pydantic's schema ourselves instead of trusting it as-is, because
    # strict mode demands additionalProperties:false and all-required. Alternative: an SDK
    # helper (ties us to an SDK internal).
    if isinstance(node, dict):
        node = {k: _strict_schema(v) for k, v in node.items() if k != "default"}
        if node.get("type") == "object" and "properties" in node:
            node["additionalProperties"] = False
            node["required"] = list(node["properties"])
    elif isinstance(node, list):
        node = [_strict_schema(v) for v in node]
    return node


class AnthropicClient:
    def __init__(self, api_key: str | None = None, on_usage: Callable | None = None):
        # .env was already loaded by config.py at import time.
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        # DECISION: base_url passed explicitly, so an ANTHROPIC_BASE_URL env var can't redirect
        # the key and prompts. max_retries=0 because _with_retries already retries
        # config.RETRIES times; the SDK's own 2 retries inside that loop would multiply attempts.
        self._client = AsyncAnthropic(api_key=key, base_url=config.BASE_URL, max_retries=0)
        self.on_usage = on_usage  # called as (stage, prompt_tokens, completion_tokens, cost, seconds)
        self.total_cost = 0.0     # summed over this client's lifetime = one run

    async def text(self, system: str, user: str, *, stage: str) -> str:
        return await self._with_retries(system, user, None, stage)

    async def structured(self, system: str, user: str, schema: type[T], *, stage: str) -> T:
        return await self._with_retries(system, user, schema, stage)

    async def _with_retries(self, system, user, schema, stage):
        last: Exception | None = None
        for attempt in range(config.RETRIES):
            try:
                content = await self._raw_call(system, user, schema, stage)
                # Validation sits inside the retry loop: bad JSON is retried like an API error.
                return content if schema is None else schema.model_validate_json(content)
            except anthropic.APIStatusError as e:
                # DECISION: 4xx (except 429) is our bug, a bad key or a rejected schema;
                # retrying just burns time.
                if e.status_code < 500 and e.status_code != 429:
                    raise LLMError(f"{stage}: HTTP {e.status_code}: {e}") from e
                last = e
            except (anthropic.APIError, ValidationError) as e:  # connection, timeout, bad JSON
                last = e
            if attempt < config.RETRIES - 1:
                await asyncio.sleep(2 ** attempt)
        raise LLMError(f"{stage}: failed after {config.RETRIES} attempts: {last}") from last

    async def _raw_call(self, system, user, schema, stage) -> str:
        if self.total_cost >= config.MAX_RUN_COST_USD:  # refuse to start a call once over budget
            raise BudgetExceeded(f"run cost ${self.total_cost:.4f} >= ${config.MAX_RUN_COST_USD}")
        kwargs: dict[str, Any] = dict(
            model=config.MODEL,
            max_tokens=config.MAX_TOKENS,
            thinking=config.THINKING,
            messages=[{"role": "user", "content": user}],
            # NOTE: no temperature (current models reject it) and no effort (model default).
        )
        if system:  # baseline() sends no system prompt at all, like the original main.py
            kwargs["system"] = system
        if schema is not None:
            kwargs["output_config"] = {"format": {
                "type": "json_schema",
                "schema": _strict_schema(schema.model_json_schema()),
            }}
        start = time.monotonic()
        resp = await self._client.messages.create(**kwargs)
        seconds = time.monotonic() - start

        usage = resp.usage
        if usage is None:  # can't track spend without it, so fail loudly instead of guessing
            raise LLMError(f"{stage}: response had no usage data")
        # The API returns no dollar cost: price the token counts at the list price in config.
        cost = (usage.input_tokens * config.PRICE_IN_PER_TOKEN
                + usage.output_tokens * config.PRICE_OUT_PER_TOKEN)
        self.total_cost += cost
        if self.on_usage:
            self.on_usage(stage, usage.input_tokens, usage.output_tokens, cost, seconds)
        if self.total_cost > config.MAX_RUN_COST_USD:
            raise BudgetExceeded(f"run cost ${self.total_cost:.4f} > ${config.MAX_RUN_COST_USD}")

        if resp.stop_reason == "refusal":
            # DECISION: fatal, not retried. Haiku 5.5 has no server-side fallback, and the same
            # request would most likely be refused again (and billed again). Usage is recorded
            # above first, because a refused call can still be billed.
            category = getattr(resp.stop_details, "category", None)
            raise LLMError(f"{stage}: model refused (category: {category})")
        # Return the first text block; thinking or other blocks may come before it.
        return next((b.text for b in resp.content if b.type == "text"), "")
