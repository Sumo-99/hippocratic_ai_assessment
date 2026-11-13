"""Behaviour every backend must share. Each test runs against both clients with a faked SDK call."""
from types import SimpleNamespace

import anthropic
import httpx2
import openai
import pytest

from storyteller import config
from storyteller.llm import BudgetExceeded, LLMError, OpenRouterClient
from storyteller.llm_anthropic import AnthropicClient
from storyteller.models import Check, GateResult

GOOD = GateResult(safety=Check(evidence="fine", passed=True),
                  relevance=Check(evidence="fine", passed=True)).model_dump_json()


def status_error(cls, code):
    response = httpx2.Response(code, request=httpx2.Request("POST", "https://example.invalid"))
    return cls(f"HTTP {code}", response=response, body=None)


def openrouter_reply(text, cost):
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, cost=cost)
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
                           usage=usage)


def anthropic_reply(text, _cost):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)],
                           stop_reason="end_turn", stop_details=None,
                           usage=SimpleNamespace(input_tokens=10, output_tokens=5))


BACKENDS = {
    # name: (client class, attribute path of the SDK call, reply builder, SDK status error)
    "openrouter": (OpenRouterClient, ("chat", "completions"), openrouter_reply,
                   openai.APIStatusError),
    "anthropic": (AnthropicClient, ("messages",), anthropic_reply, anthropic.APIStatusError),
}


@pytest.fixture(params=list(BACKENDS))
def make(request, monkeypatch):
    """make(*items, cost=0.0, on_usage=None) -> (client, calls). A str item is a successful
    reply with that text; an int item makes the SDK raise its status error with that code."""
    cls, path, build_reply, err_cls = BACKENDS[request.param]

    def _make(*items, cost=0.0, on_usage=None):
        if request.param == "anthropic":  # no dollar cost in the response: price 10 input tokens
            monkeypatch.setattr(config, "ANTHROPIC_PRICE_IN_PER_TOKEN", cost / 10)
            monkeypatch.setattr(config, "ANTHROPIC_PRICE_OUT_PER_TOKEN", 0.0)
        client = cls(api_key="test-key", on_usage=on_usage)
        calls, queue = [], list(items)

        async def fake_create(**kwargs):
            calls.append(kwargs)
            item = queue.pop(0)
            if isinstance(item, int):
                raise status_error(err_cls, item)
            return build_reply(item, cost)

        target = client._client
        for name in path:
            target = getattr(target, name)
        target.create = fake_create
        return client, calls

    return _make


async def test_retry_then_validate(make):
    client, calls = make('{"bad":1}', GOOD)
    out = await client.structured("s", "u", GateResult, stage="gate")
    assert isinstance(out, GateResult) and len(calls) == 2


async def test_gives_up_after_retries(make):
    client, calls = make(*['{"bad":1}'] * config.RETRIES)
    with pytest.raises(LLMError, match="failed after"):
        await client.structured("s", "u", GateResult, stage="gate")
    assert len(calls) == config.RETRIES


async def test_4xx_not_retried(make):
    client, calls = make(400, GOOD)
    with pytest.raises(LLMError, match="gate: HTTP 400"):
        await client.structured("s", "u", GateResult, stage="gate")
    assert len(calls) == 1


async def test_429_and_5xx_retried(make):
    client, calls = make(429, 503, GOOD)
    out = await client.structured("s", "u", GateResult, stage="gate")
    assert isinstance(out, GateResult) and len(calls) == 3


async def test_budget_exceeded(make, monkeypatch):
    monkeypatch.setattr(config, "MAX_RUN_COST_USD", 0.10)
    client, _ = make("x", "y", cost=0.06)
    await client.text("s", "u", stage="a")
    with pytest.raises(BudgetExceeded):
        await client.text("s", "u", stage="b")


async def test_usage_callback_shape(make):
    seen = []
    client, _ = make("x", cost=0.001, on_usage=lambda *a: seen.append(a))
    await client.text("s", "u", stage="gate")
    stage, pt, ct, cost, secs = seen[0]
    assert (stage, pt, ct) == ("gate", 10, 5)
    assert cost == pytest.approx(0.001) and secs >= 0
