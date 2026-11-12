import json
from types import SimpleNamespace

import pytest

from storyteller import config
from storyteller.fake import FakeLLM
from storyteller.llm import BudgetExceeded, LLMError, OpenRouterClient
from storyteller.models import GateResult
from storyteller.trace import Trace

GOOD = GateResult(reason="fine", safe=True, relevant=True).model_dump_json()


def make_client(replies, cost=0.0, **kw):
    """OpenRouterClient whose SDK call is replaced by a recorder (no network)."""
    client = OpenRouterClient(api_key="test-key", **kw)
    calls = []
    queue = list(replies)

    async def fake_create(**kwargs):
        calls.append(kwargs)
        usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, cost=cost)
        msg = SimpleNamespace(content=queue.pop(0))
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)], usage=usage)

    client._client.chat.completions.create = fake_create
    return client, calls


async def test_structured_retries_then_validates():
    client, calls = make_client(['{"bad":1}', GOOD])
    out = await client.structured("s", "u", GateResult, stage="gate")
    assert isinstance(out, GateResult) and out.safe
    assert len(calls) == 2


async def test_structured_gives_up_after_retries():
    client, calls = make_client(['{"bad":1}'] * config.RETRIES)
    with pytest.raises(LLMError):
        await client.structured("s", "u", GateResult, stage="gate")
    assert len(calls) == config.RETRIES


async def test_never_sends_temperature():
    client, calls = make_client([GOOD])
    await client.structured("s", "u", GateResult, stage="gate")
    kw = calls[0]
    assert "temperature" not in kw
    assert kw["model"] == "anthropic/claude-haiku-5.5"
    assert kw["max_tokens"] == config.MAX_TOKENS
    assert kw["extra_body"]["reasoning"] == {"enabled": False}
    assert kw["extra_body"]["usage"] == {"include": True}
    assert kw["extra_body"]["provider"] == {"require_parameters": True}
    assert kw["response_format"]["type"] == "json_schema"
    assert kw["response_format"]["json_schema"]["strict"] is True


async def test_text_call_has_no_response_format():
    client, calls = make_client(["a story"])
    assert await client.text("s", "u", stage="generate") == "a story"
    assert "response_format" not in calls[0] and "temperature" not in calls[0]


async def test_budget_exceeded_raises(monkeypatch):
    monkeypatch.setattr(config, "MAX_RUN_COST_USD", 0.10)
    client, _ = make_client(["x", "y"], cost=0.06)
    await client.text("s", "u", stage="a")
    with pytest.raises(BudgetExceeded):
        await client.text("s", "u", stage="b")


async def test_usage_callback_receives_tokens_and_cost():
    seen = []
    client, _ = make_client(["x"], cost=0.001, on_usage=lambda *a: seen.append(a))
    await client.text("s", "u", stage="gate")
    stage, pt, ct, cost, secs = seen[0]
    assert (stage, pt, ct, cost) == ("gate", 10, 5, 0.001) and secs >= 0


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr("storyteller.llm.load_dotenv", lambda *a, **k: None)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY not set"):
        OpenRouterClient()


async def test_fake_llm_fifo_and_records_calls():
    fake = FakeLLM({
        "gate": [GateResult(reason="r", safe=True, relevant=True)],
        "generate": ["first", lambda system, user: f"echo:{user}"],
    })
    assert (await fake.structured("S", "U", GateResult, stage="gate")).safe
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
