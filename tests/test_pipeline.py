"""Pipeline tests. FakeLLM replies are callables that look at the prompt, so each stage behaves
like a tiny deterministic model. Every story starts with a tag word (v0, v1, v2, ...) that says
which round wrote it; the fake judge decides what fails from that tag."""
import json
import os
from string import Template

import pytest

from storyteller import config, pipeline, prompts
from storyteller.fake import FakeLLM
from storyteller.llm import BudgetExceeded
from storyteller.models import (Character, Check, DraftVersion, Evaluation, Extraction, GateResult, JudgeResult,
                                Verdict)

DIMS = config.HARD + [d for d in config.SOFT if d != "length"]
PAD = " ".join(["word"] * 600)  # keeps every fake story inside WORD_RANGE
MANY = 50                       # plenty of scripted replies for a callable stage


@pytest.fixture(autouse=True)
def isolate(monkeypatch, tmp_path):
    monkeypatch.setattr(prompts, "load", lambda name: Template(f"<{name}>"))
    monkeypatch.setattr(config, "RUNS_DIR", str(tmp_path / "runs"))


# ---- fake stage behaviour ----------------------------------------------------------------

def gate_ok(*_):
    return GateResult(safety=Check(evidence="fine", passed=True),
                      relevance=Check(evidence="fine", passed=True))


def gate_no(*_):
    return GateResult(safety=Check(evidence="fine", passed=True),
                      relevance=Check(evidence="That isn't a story request.", passed=False))


def extraction(*_):
    return Extraction(characters=[Character(name="Alice", role=None),
                                  Character(name="Bob", role="Alice's cat")], setting=None, premise="fly to the moon",
                      listener=None, category="adventure")


def generate(*_):
    return f"v0 {PAD}"


def make_revise():
    """The n-th revise call returns a story tagged vn, whatever story it was given."""
    count = [0]

    def revise(*_):
        count[0] += 1
        return f"v{count[0]} {PAD}"
    return revise


def tag_of(story):
    return story.split()[0]


def judge_from(fails_for):
    """fails_for(tag) -> set of failing dimension names for that version."""
    def reply(_system, user):
        fail = fails_for(tag_of(user.removeprefix("STORY:\n")))
        return JudgeResult(**{d: Verdict(evidence="e", passed=d not in fail, fix=f"fix {d}")
                              for d in DIMS})
    return reply


def fake(judge, gate=gate_ok):
    return FakeLLM({"gate": [gate], "extract": [extraction], "generate": [generate] * MANY,
                    "revise": [make_revise()] * MANY, "judge": [judge] * MANY})


def stages(llm):
    return [c[0] for c in llm.calls]


def revise_inputs(llm):
    """The tag of the story each revise call started from."""
    return [tag_of(c[2].split("Story:\n", 1)[1]) for c in llm.calls if c[0] == "revise"]


def read_trace(result):
    with open(result.trace_path) as f:
        return json.load(f)


# ---- gate ---------------------------------------------------------------------------------

async def test_rejected_request_stops_before_extraction():
    llm = fake(judge_from(lambda t: set()), gate=gate_no)
    result = await pipeline.run("how do I fix my car", llm)
    assert result.status == "rejected" and result.story is None
    assert "isn't a story request" in result.message
    assert stages(llm) == ["gate"]  # no extraction, no writing, no judging


# ---- the revision loop --------------------------------------------------------------------

async def test_first_draft_that_passes_needs_no_revision():
    llm = fake(judge_from(lambda t: set()))
    result = await pipeline.run("Alice and her cat Bob fly to the moon", llm)
    assert result.status == "story" and tag_of(result.story) == "v0"
    assert stages(llm) == ["gate", "extract", "generate", "judge"]


async def test_revision_loop_respects_max_rounds():
    llm = fake(judge_from(lambda t: {"engagement"}))  # never fixed
    result = await pipeline.run("x", llm)
    assert stages(llm).count("revise") == config.MAX_ROUNDS
    assert result.status == "story"  # soft failures never block the story


async def test_revision_loop_honours_changed_max_rounds(monkeypatch):
    monkeypatch.setattr(config, "MAX_ROUNDS", 1)
    llm = fake(judge_from(lambda t: {"engagement"}))
    await pipeline.run("x", llm)
    assert stages(llm).count("revise") == 1


async def test_loop_stops_once_everything_passes():
    llm = fake(judge_from(lambda t: {"engagement"} if t == "v0" else set()))
    result = await pipeline.run("x", llm)
    assert stages(llm).count("revise") == 1 and tag_of(result.story) == "v1"


async def test_feedback_sends_hard_failures_first():
    llm = fake(judge_from(lambda t: {"wind_down", "engagement"} if t == "v0" else set()))
    await pipeline.run("x", llm)
    first_revise_user = next(c[2] for c in llm.calls if c[0] == "revise")
    assert "fix wind_down" in first_revise_user and "engagement" not in first_revise_user


async def test_the_walkthrough_example():
    """v0: wind_down (hard) + engagement. v1: engagement only. v2: consistency (hard).
    v3: everything passes. The guard throws v2 away, so round 3 revises v1 again."""
    fails = {"v0": {"wind_down", "engagement"}, "v1": {"engagement"},
             "v2": {"consistency"}, "v3": set()}
    llm = fake(judge_from(lambda t: fails[t]))
    result = await pipeline.run("Alice and her cat Bob fly to the moon", llm)
    assert revise_inputs(llm) == ["v0", "v1", "v1"]  # round 3 starts from the kept v1
    trace = read_trace(result)
    assert [g["kept_round"] for g in trace["guard"]] == [1, 1, 3]
    assert result.status == "story" and trace["final"]["all_passed"]


# ---- the regression guard (pure code) -----------------------------------------------------

def version(rnd, hard=()):
    judge = JudgeResult(**{d: Verdict(evidence="e", passed=d not in hard, fix=None)
                           for d in DIMS})
    ev = Evaluation(judge=judge, word_count=600, length_ok=True, hard_failures=list(hard),
                    soft_failures=[])
    return DraftVersion(round=rnd, text=f"v{rnd}", evaluation=ev, feedback_sent=None)


def test_guard_keeps_previous_when_new_fails_more_hard_checks():
    prev, new = version(1), version(2, hard=["consistency"])
    assert pipeline.keep_better(prev, new) is prev


def test_guard_takes_new_when_it_fails_fewer_hard_checks():
    prev, new = version(0, hard=["wind_down"]), version(1)
    assert pipeline.keep_better(prev, new) is new


def test_guard_tie_goes_to_new():
    prev, new = version(1, hard=["wind_down"]), version(2, hard=["consistency"])
    assert pipeline.keep_better(prev, new) is new


def test_guard_never_trades_safe_for_unsafe():
    prev = version(1, hard=["wind_down", "consistency"])
    new = version(2, hard=["safety"])
    assert pipeline.keep_better(prev, new) is prev


# ---- the final safety check ---------------------------------------------------------------

async def test_final_draft_failing_safety_is_never_shown():
    llm = fake(judge_from(lambda t: {"safety"}))
    result = await pipeline.run("x", llm)
    assert result.status == "safety_message" and result.story is None
    assert result.message == pipeline.CANNED_SAFETY_MESSAGE
    assert read_trace(result)["final"]["status"] == "safety_message"


async def test_other_hard_failures_at_the_cap_still_show_the_story():
    llm = fake(judge_from(lambda t: {"wind_down"}))
    result = await pipeline.run("x", llm)
    assert result.status == "story" and result.story is not None
    assert read_trace(result)["final"]["hard_failures"] == ["wind_down"]


# ---- trace, budget, errors ----------------------------------------------------------------

async def test_trace_written_with_required_keys():
    llm = fake(judge_from(lambda t: {"engagement"} if t == "v0" else set()))
    trace = read_trace(await pipeline.run("x", llm))
    for key in ("request", "gate", "extraction", "spec", "versions", "guard", "final",
                "timings", "usage", "total_cost_usd", "latency_budget_exceeded"):
        assert key in trace
    assert trace["versions"][1]["feedback_sent"] == "- engagement: fix engagement"


async def test_budget_exceeded_returns_error_and_writes_trace():
    def over(*_):
        raise BudgetExceeded("over")
    llm = fake(over)
    result = await pipeline.run("x", llm)
    assert result.status == "error" and result.message == pipeline.BUDGET_MESSAGE
    trace = read_trace(result)
    assert "over" in trace["error"] and trace["final"]["status"] == "error"


async def test_trace_written_even_when_run_raises():
    def crash(*_):
        raise RuntimeError("unexpected")
    llm = fake(judge_from(lambda t: set()), gate=crash)
    with pytest.raises(RuntimeError):
        await pipeline.run("a dragon", llm)
    assert len(os.listdir(config.RUNS_DIR)) == 1


async def test_missing_key_still_writes_trace(monkeypatch):
    def no_key(**_):
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    monkeypatch.setattr(pipeline, "build_client", no_key)
    with pytest.raises(RuntimeError):
        await pipeline.run("a dragon")
    assert len(os.listdir(config.RUNS_DIR)) == 1


async def test_run_without_llm_builds_one_client_wired_to_trace(monkeypatch):
    made = []

    class Client(FakeLLM):
        def __init__(self, on_usage=None):
            super().__init__({"gate": [gate_no]})
            self.on_usage = on_usage
            made.append(self)

    monkeypatch.setattr(pipeline, "build_client", Client)
    await pipeline.run("x")
    assert len(made) == 1 and made[0].on_usage.__self__.__class__ is pipeline.Trace


# ---- baseline and CLI ---------------------------------------------------------------------

async def test_baseline_is_one_plain_call():
    llm = FakeLLM({"baseline": ["once upon a time"]})
    assert await pipeline.baseline("a cat story", llm) == "once upon a time"
    assert llm.calls == [("baseline", "", "a cat story")]


async def test_verbose_details_print_from_trace(capsys):
    import main
    llm = fake(judge_from(lambda t: {"engagement"} if t == "v0" else set()))
    result = await pipeline.run("x", llm)
    main.print_details(result.trace_path)
    out = capsys.readouterr().out
    assert "category: adventure" in out and "revisions: 1" in out and "final: PASS" in out
    assert "total cost: $0.0000" in out and result.trace_path in out


# ---- story ideas for requests with no premise -----------------------------------------------------

def vague_extraction(*_):
    return Extraction(characters=[], setting=None, premise=None, listener=None, category=None)


def five_options(*_):
    from storyteller.models import StoryOption, StoryOptions
    return StoryOptions(options=[StoryOption(characters=f"c{i}", setting=f"s{i}",
                                             situation=f"x{i}") for i in range(5)])


def options_fake():
    return FakeLLM({"gate": [gate_ok], "extract": [vague_extraction], "options": [five_options],
                    "generate": [generate] * MANY, "judge": [judge_from(lambda t: set())] * MANY})


async def test_vague_request_gets_a_logged_random_option_for_the_writer(monkeypatch):
    monkeypatch.setattr(config, "OPTIONS_SEED", 7)
    llm = options_fake()
    result = await pipeline.run("tell me a story", llm)
    assert stages(llm) == ["gate", "extract", "options", "generate", "judge"]
    t = read_trace(result)
    assert len(t["options"]["list"]) == 5 and t["options"]["seed"] == 7
    assert "steer" not in t["options"]
    i = t["options"]["picked_index"]
    assert t["spec"]["idea"]["characters"] == f"c{i}"
    assert f"Premise: x{i}" in llm.calls[3][1]  # the writer's system prompt
    # same seed + same request -> same pick
    again = read_trace(await pipeline.run("tell me a story", options_fake()))
    assert again["options"]["picked_index"] == i


async def test_judge_does_not_see_the_picked_option():
    llm = options_fake()
    await pipeline.run("tell me a story", llm)
    _, system, user = next(c for c in llm.calls if c[0] == "judge")
    for i in range(5):
        assert f"c{i}" not in system + user and f"x{i}" not in system + user


async def test_no_options_call_when_the_request_has_a_premise():
    llm = fake(judge_from(lambda t: set()))
    await pipeline.run("Alice and her cat Bob fly to the moon", llm)
    assert "options" not in stages(llm)


async def test_named_characters_without_a_premise_still_get_ideas():
    # "Alice and her cat Bob": characters but no premise -> ideas, keeping Alice and Bob.
    def characters_only(*_):
        return Extraction(characters=[Character(name="Alice", role=None)], setting=None,
                          premise=None, listener=None, category=None)
    llm = FakeLLM({"gate": [gate_ok], "extract": [characters_only], "options": [five_options],
                   "generate": [generate] * MANY, "judge": [judge_from(lambda t: set())] * MANY})
    await pipeline.run("Alice", llm)
    assert stages(llm) == ["gate", "extract", "options", "generate", "judge"]
    writer = next(c for c in llm.calls if c[0] == "generate")[1]
    assert "Characters: Alice" in writer and not any(f"c{i}" in writer for i in range(5))


async def test_no_category_means_no_category_prompt_even_for_an_empty_request():
    llm = options_fake()
    await pipeline.run("tell me a story", llm)
    writer = next(c for c in llm.calls if c[0] == "generate")[1]
    assert not any(f"<{c}>" in writer for c in ("cozy", "silly", "adventure", "comfort"))
