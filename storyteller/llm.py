"""OpenRouter client (via the openai SDK) with retries, usage capture and a budget guard."""
import asyncio
import os
import time
from typing import Any, Callable, Protocol, TypeVar

import openai
from openai import AsyncOpenAI
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
    # strict mode demands additionalProperties:false and all-required. Alternative: openai's
    # to_strict_json_schema helper (ties us to an SDK internal).
    if isinstance(node, dict):
        node = {k: _strict_schema(v) for k, v in node.items() if k != "default"}
        if node.get("type") == "object" and "properties" in node:
            node["additionalProperties"] = False
            node["required"] = list(node["properties"])
    elif isinstance(node, list):
        node = [_strict_schema(v) for v in node]
    return node


class OpenRouterClient:
    def __init__(self, api_key: str | None = None, on_usage: Callable | None = None):
        # .env was already loaded by config.py at import time.
        key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY not set")
        self._client = AsyncOpenAI(base_url=config.BASE_URL, api_key=key)
        self.on_usage = on_usage  # called as (stage, prompt_tokens, completion_tokens, cost, seconds)
        self.total_cost = 0.0     # summed over this client's lifetime = one run

    async def text(self, system: str, user: str, *, stage: str) -> str:
        return await self._with_retries(system, user, None, stage)

    async def structured(self, system: str, user: str, schema: type[T], *, stage: str) -> T:
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": schema.__name__,
                "strict": True,
                "schema": _strict_schema(schema.model_json_schema()),
            },
        }
        return await self._with_retries(system, user, response_format, stage, schema)

    async def _with_retries(self, system, user, response_format, stage, schema=None):
        last: Exception | None = None
        for attempt in range(config.RETRIES):
            try:
                content = await self._raw_call(system, user, response_format, stage)
                # Validation sits inside the retry loop: bad JSON is retried like an API error.
                return content if schema is None else schema.model_validate_json(content)
            except openai.APIStatusError as e:
                # DECISION: 4xx (except 429) is our bug or a bad key; retrying just burns time.
                if e.status_code < 500 and e.status_code != 429:
                    raise LLMError(f"{stage}: HTTP {e.status_code}: {e}") from e
                last = e
            except (openai.APIError, ValidationError) as e:  # connection, timeout, 429, 5xx, bad JSON
                last = e
            if attempt < config.RETRIES - 1:
                await asyncio.sleep(2 ** attempt)
        raise LLMError(f"{stage}: failed after {config.RETRIES} attempts: {last}") from last

    async def _raw_call(self, system, user, response_format, stage) -> str:
        if self.total_cost >= config.MAX_RUN_COST_USD:  # refuse to start a call once over budget
            raise BudgetExceeded(f"run cost ${self.total_cost:.4f} >= ${config.MAX_RUN_COST_USD}")
        messages = [{"role": "user", "content": user}]
        if system:  # baseline() sends no system prompt at all, like the original main.py
            messages.insert(0, {"role": "system", "content": system})
        kwargs: dict[str, Any] = dict(
            model=config.MODEL,
            messages=messages,
            max_tokens=config.MAX_TOKENS,
            # NOTE: no temperature, the model rejects it.
            extra_body={
                "reasoning": {"enabled": False},   # no hidden (billed) reasoning tokens
                "usage": {"include": True},        # OpenRouter adds usage.cost
                "provider": {"require_parameters": True},  # only providers that honor json_schema
            },
        )
        if response_format is not None:
            kwargs["response_format"] = response_format
        start = time.monotonic()
        resp = await self._client.chat.completions.create(**kwargs)
        seconds = time.monotonic() - start

        usage = resp.usage
        if usage is None:  # can't track spend without it, so fail loudly instead of guessing
            raise LLMError(f"{stage}: response had no usage data")
        cost = float(getattr(usage, "cost", 0.0) or 0.0)  # extra field, not in the SDK's typed model
        if cost == 0.0:
            # DECISION: if OpenRouter omits usage.cost, estimate it from token counts so the
            # budget guard still works instead of silently reading every call as free.
            cost = (usage.prompt_tokens * config.PRICE_IN_PER_TOKEN
                    + usage.completion_tokens * config.PRICE_OUT_PER_TOKEN)
        self.total_cost += cost
        if self.on_usage:
            self.on_usage(stage, usage.prompt_tokens, usage.completion_tokens, cost, seconds)
        if self.total_cost > config.MAX_RUN_COST_USD:
            raise BudgetExceeded(f"run cost ${self.total_cost:.4f} > ${config.MAX_RUN_COST_USD}")
        return resp.choices[0].message.content or ""
