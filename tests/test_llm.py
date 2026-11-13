import json
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from storyteller import config
from storyteller.fake import FakeLLM
from storyteller.llm import AnthropicClient, BudgetExceeded, LLMError
from storyteller.models import Check, GateResult
from storyteller.trace import Trace

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


def status_error(code):
    response = httpx2.Response(code, request=httpx2.Request("POST", "https://example.invalid"))
    return anthropic.APIStatusError(f"HTTP {code}", response=response, body=None)


def make_client(replies, **kw):
    """AnthropicClient whose SDK call is replaced by a recorder (no network). Each reply is a
    str (one text block), an int (the SDK raises that HTTP status) or a full fake Message."""
    client = AnthropicClient(api_key="test-key", **kw)
    calls = []
    queue = list(replies)

    async def fake_create(**kwargs):
        calls.append(kwargs)
        item = queue.pop(0)
        if isinstance(item, int):
            raise status_error(item)
        return reply(item) if isinstance(item, str) else item

    client._client.messages.create = fake_create
    return client, calls


# ---- request shape --------------------------------------------------------------------------

async def test_structured_request_shape():
    client, calls = make_client([GOOD])
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
    assert "temperature" not in kw


async def test_text_call_has_no_output_config():
    client, calls = make_client(["a story"])
    assert await client.text("s", "u", stage="generate") == "a story"
    assert "output_config" not in calls[0]


async def test_empty_system_is_omitted():
    client, calls = make_client(["once"])
    await client.text("", "u", stage="baseline")
    assert "system" not in calls[0]


def test_base_url_is_fixed_and_sdk_retries_off(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://evil.example")
    client = AnthropicClient(api_key="k")
    assert str(client._client.base_url).rstrip("/") == "https://api.anthropic.com"
    assert client._client.max_retries == 0


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY not set"):
        AnthropicClient()


# ---- response mapping -----------------------------------------------------------------------

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


async def test_no_usage_raises():
    client, _ = make_client([reply("x", usage=None)])
    with pytest.raises(LLMError, match="no usage"):
        await client.text("s", "u", stage="gate")


# ---- retries --------------------------------------------------------------------------------

async def test_structured_retries_then_validates():
    client, calls = make_client(['{"bad":1}', GOOD])
    out = await client.structured("s", "u", GateResult, stage="gate")
    assert isinstance(out, GateResult) and out.safety.passed
    assert len(calls) == 2


async def test_structured_gives_up_after_retries():
    client, calls = make_client(['{"bad":1}'] * config.RETRIES)
    with pytest.raises(LLMError, match="failed after"):
        await client.structured("s", "u", GateResult, stage="gate")
    assert len(calls) == config.RETRIES


async def test_4xx_not_retried():
    client, calls = make_client([400, GOOD])
    with pytest.raises(LLMError, match="gate: HTTP 400"):
        await client.structured("s", "u", GateResult, stage="gate")
    assert len(calls) == 1


async def test_429_and_5xx_retried():
    client, calls = make_client([429, 503, GOOD])
    out = await client.structured("s", "u", GateResult, stage="gate")
    assert isinstance(out, GateResult) and len(calls) == 3


# ---- cost and budget ------------------------------------------------------------------------

async def test_cost_from_tokens_and_usage_callback():
    seen = []
    client, _ = make_client([reply("x", usage=(1000, 2000))], on_usage=lambda *a: seen.append(a))
    await client.text("s", "u", stage="gate")
    stage, pt, ct, cost, secs = seen[0]
    assert (stage, pt, ct) == ("gate", 1000, 2000) and secs >= 0
    assert cost == pytest.approx(1000 * 0.10e-6 + 2000 * 0.50e-6)
    assert client.total_cost == pytest.approx(cost)


async def test_budget_exceeded_raises(monkeypatch):
    monkeypatch.setattr(config, "MAX_RUN_COST_USD", 0.10)
    monkeypatch.setattr(config, "PRICE_IN_PER_TOKEN", 0.006)  # 10 input tokens = $0.06 a call
    monkeypatch.setattr(config, "PRICE_OUT_PER_TOKEN", 0.0)
    client, _ = make_client(["x", "y"])
    await client.text("s", "u", stage="a")
    with pytest.raises(BudgetExceeded):
        await client.text("s", "u", stage="b")


# ---- test doubles and trace -----------------------------------------------------------------

async def test_fake_llm_fifo_and_records_calls():
    fake = FakeLLM({
        "gate": [GateResult.model_validate_json(GOOD)],
        "generate": ["first", lambda system, user: f"echo:{user}"],
    })
    assert (await fake.structured("S", "U", GateResult, stage="gate")).safety.passed
    assert await fake.text("S", "U1", stage="generate") == "first"
    assert await fake.text("S", "U2", stage="generate") == "echo:U2"
    assert fake.calls[0] == ("gate", "S", "U")
    assert len(fake.calls) == 3
    with pytest.raises(AssertionError):
        await fake.text("S", "U", stage="generate")  # queue empty


def test_trace_stage_accumulates_and_writes_json(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RUNS_DIR", str(tmp_path))
    t = Trace("a story about a dragon!")
    with t.stage("gate"):
        pass
    with t.stage("gate"):
        pass
    t.set("status", "story")
    t.append("drafts", {"i": 1})
    t.on_usage("gate", 10, 5, 0.002, 0.1)
    path = t.write()
    data = json.load(open(path))
    assert data["request"] == "a story about a dragon!"
    assert data["status"] == "story" and data["drafts"] == [{"i": 1}]
    assert "gate" in data["timings"] and data["total_cost_usd"] == 0.002
    assert data["calls"][0]["stage"] == "gate"
    assert path.startswith(str(tmp_path))
