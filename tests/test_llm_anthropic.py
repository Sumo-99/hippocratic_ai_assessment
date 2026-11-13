"""AnthropicClient: request shape and response mapping. The SDK call is faked; no network."""
from types import SimpleNamespace

import pytest

from storyteller import config
from storyteller.llm import LLMError
from storyteller.llm_anthropic import AnthropicClient
from storyteller.models import Check, GateResult

GOOD = GateResult(safety=Check(evidence="fine", passed=True),
                  relevance=Check(evidence="fine", passed=True)).model_dump_json()


def text_block(text):
    return SimpleNamespace(type="text", text=text)


def reply(content, stop_reason="end_turn", usage=(10, 5), stop_details=None):
    """A fake anthropic Message. `content` is a str (one text block) or a list of blocks."""
    blocks = [text_block(content)] if isinstance(content, str) else content
    u = None if usage is None else SimpleNamespace(input_tokens=usage[0], output_tokens=usage[1])
    return SimpleNamespace(content=blocks, stop_reason=stop_reason, stop_details=stop_details,
                           usage=u)


def make_client(replies, **kw):
    """AnthropicClient whose SDK call is replaced by a recorder (no network)."""
    client = AnthropicClient(api_key="test-key", **kw)
    calls = []
    queue = list(replies)

    async def fake_create(**kwargs):
        calls.append(kwargs)
        return queue.pop(0)

    client._client.messages.create = fake_create
    return client, calls


async def test_request_shape_structured():
    client, calls = make_client([reply(GOOD)])
    out = await client.structured("s", "u", GateResult, stage="gate")
    assert out.safety.passed
    kw = calls[0]
    assert kw["model"] == "claude-haiku-5-5"
    assert kw["max_tokens"] == config.MAX_TOKENS
    assert kw["thinking"] == {"type": "disabled"}
    assert kw["system"] == "s"
    assert kw["messages"] == [{"role": "user", "content": "u"}]
    assert kw["output_config"]["format"]["type"] == "json_schema"
    assert kw["output_config"]["format"]["schema"]["additionalProperties"] is False
    assert "temperature" not in kw and "extra_body" not in kw and "response_format" not in kw


async def test_text_call_has_no_output_config():
    client, calls = make_client([reply("a story")])
    assert await client.text("s", "u", stage="generate") == "a story"
    assert "output_config" not in calls[0]


async def test_empty_system_is_omitted():
    client, calls = make_client([reply("once")])
    await client.text("", "u", stage="baseline")
    assert "system" not in calls[0]


async def test_picks_first_text_block():
    thinking = SimpleNamespace(type="thinking", thinking="", signature="x")
    client, _ = make_client([reply([thinking, text_block("story"), text_block("extra")])])
    assert await client.text("s", "u", stage="generate") == "story"


async def test_no_text_block_returns_empty():
    client, _ = make_client([reply([])])
    assert await client.text("s", "u", stage="generate") == ""


async def test_refusal_is_fatal_not_retried():
    details = SimpleNamespace(type="refusal", category="general_harms", explanation="no")
    client, calls = make_client([reply([], stop_reason="refusal", stop_details=details)] * 3)
    with pytest.raises(LLMError, match="refus"):
        await client.text("s", "u", stage="generate")
    assert len(calls) == 1


async def test_cost_from_tokens_and_callback():
    seen = []
    client, _ = make_client([reply("x", usage=(1000, 2000))], on_usage=lambda *a: seen.append(a))
    await client.text("s", "u", stage="gate")
    stage, pt, ct, cost, secs = seen[0]
    assert (stage, pt, ct) == ("gate", 1000, 2000) and secs >= 0
    assert cost == pytest.approx(1000 * 0.10e-6 + 2000 * 0.50e-6)
    assert client.total_cost == pytest.approx(cost)


async def test_no_usage_raises():
    client, _ = make_client([reply("x", usage=None)])
    with pytest.raises(LLMError, match="no usage"):
        await client.text("s", "u", stage="gate")


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY not set"):
        AnthropicClient()


def test_sdk_retries_disabled():
    assert AnthropicClient(api_key="k")._client.max_retries == 0
