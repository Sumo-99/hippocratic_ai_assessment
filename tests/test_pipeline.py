"""Pipeline tests. FakeLLM replies are callables that look at the prompt, so each stage
behaves like a tiny deterministic model. Every story starts with a tag word (P0, P1, FB, ...)
that the fake judge and fake comparer use to decide what to say."""
import json
import os
import re
from string import Template

import pytest

from storyteller import config, pipeline, prompts
from storyteller.fake import FakeLLM
from storyteller.llm import BudgetExceeded
from storyteller.models import (Brainstorm, Comparison, Extraction, GateResult, JudgeResult,
                                Premise, Verdict)

DIMS = config.HARD + [d for d in config.SOFT if d != "length"]
PAD = " ".join(["word"] * 600)  # keeps every fake story inside WORD_RANGE
MANY = 50                       # plenty of scripted replies for a callable stage


@pytest.fixture(autouse=True)
def isolate(monkeypatch, tmp_path):
    # Stub prompts: "<name>" lets a test see which category bundle a system prompt used.
    monkeypatch.setattr(prompts, "load", lambda name: Template(f"<{name}>"))
    monkeypatch.setattr(config, "RUNS_DIR", str(tmp_path / "runs"))


# ---- fake stage behaviour ----------------------------------------------------------------

def gate_ok(*_):
    return GateResult(reason="fine", safe=True, relevant=True)


def extraction(premise):
    return Extraction(characters=[], setting=None, premise=premise, mood=None, worry=None,
                      category=None)


def brainstorm_reply(*_):
    return Brainstorm(premises=[Premise(premise=f"P{i}", category="cozy", characters=["Kit"],
                                        setting="a hill") for i in range(3)])


def generate(system, _user):
    """First draft: tagged by the premise in the system prompt; no premise means fallback."""
    m = re.search(r"^Premise: (\S+)", system, re.M)
    return f"{m.group(1) if m else 'FB'} {PAD}"


def revise(_system, user):
    previous = user.split("Story:\n", 1)[1].split("\n\nFeedback:", 1)[0]
    tag = previous.split()[0]
    return f"{tag}r {PAD}"  # each revision appends an "r" to the tag


def tag_of(story):
    return story.split()[0]


def judge_from(fails_for):
    """fails_for(tag) -> set of failing dimension names."""
    def reply(_system, user):
        fail = fails_for(tag_of(user.removeprefix("STORY:\n")))
        return JudgeResult(**{d: Verdict(evidence="e", passed=d not in fail, fix=f"fix {d}")
                              for d in DIMS})
    return reply


def compare_by_rank(rank):
    """rank(tag) -> number; the lower number wins in either order."""
    def reply(_system, user):
        a = user.split("STORY A:\n", 1)[1].split("\n\nSTORY B:\n", 1)[0]
        b = user.split("\n\nSTORY B:\n", 1)[1]
        return Comparison(reason="r", winner="A" if rank(tag_of(a)) < rank(tag_of(b)) else "B")
    return reply


def always_a(*_):
    """Pure position bias: both orders disagree, so every comparison is a tie."""
    return Comparison(reason="r", winner="A")


def fake(premise, judge, compare=always_a, gate=gate_ok):
    return FakeLLM({
        "gate": [gate],
        "extract": [extraction(premise)],
        "brainstorm": [brainstorm_reply],
        "generate": [generate] * MANY,
        "revise": [revise] * MANY,
        "judge": [judge] * MANY,
        "compare": [compare] * MANY,
    })


def stages(llm):
    return [c[0] for c in llm.calls]


# ---- gate ---------------------------------------------------------------------------------

async def test_rejected_request_returns_message_and_no_generation():
    llm = fake("x", judge_from(lambda t: set()),
               gate=lambda *_: GateResult(reason="Not a story request.", safe=True,
                                          relevant=False))
    result = await pipeline.run("what is 2+2", llm)
    assert result.status == "rejected" and result.story is None
    assert "Not a story request." in result.message
    assert stages(llm) == ["gate"]


# ---- depth --------------------------------------------------------------------------------

async def test_depth_single_draft_stops_when_all_pass():
    llm = fake("D", judge_from(lambda t: set()))
    result = await pipeline.run("a story about a dragon", llm)
    s = stages(llm)
    assert result.status == "story" and tag_of(result.story) == "D"
    assert s.count("generate") == 1 and s.count("judge") == 1
    assert s.count("revise") == 0 and s.count("compare") == 0
    assert "brainstorm" not in s


async def test_revision_loop_respects_max_rounds():
    llm = fake("D", judge_from(lambda t: {"engagement"}))  # never satisfied
    result = await pipeline.run("a dragon", llm)
    s = stages(llm)
    assert s.count("revise") == config.MAX_ROUNDS
    assert s.count("judge") == config.MAX_ROUNDS + 1
    assert s.count("compare") == 2 * config.MAX_ROUNDS  # keep-better, both orders
    assert result.status == "story"


async def test_revision_loop_honours_changed_max_rounds(monkeypatch):
    monkeypatch.setattr(config, "MAX_ROUNDS", 1)
    llm = fake("D", judge_from(lambda t: {"engagement"}))
    await pipeline.run("a dragon", llm)
    assert stages(llm).count("revise") == 1


async def test_revision_stops_once_kept_version_passes():
    # The original fails a soft check; the first revision passes and wins the comparison.
    llm = fake("D", judge_from(lambda t: set() if t.endswith("r") else {"story_arc"}),
               compare=compare_by_rank(lambda t: 0 if t.endswith("r") else 1))
    result = await pipeline.run("a dragon", llm)
    assert stages(llm).count("revise") == 1
    assert tag_of(result.story) == "Dr"


async def test_revision_feedback_is_built_from_kept_version():
    llm = fake("D", judge_from(lambda t: {"engagement"}))
    await pipeline.run("a dragon", llm)
    revise_users = [c[2] for c in llm.calls if c[0] == "revise"]
    assert all("fix engagement" in u for u in revise_users)
    # Comparisons always tie, so every revision starts from the original draft.
    assert all(u.startswith("Story:\nD ") for u in revise_users)


# ---- breadth and selection ----------------------------------------------------------------

async def test_breadth_runs_three_drafts_and_selects_by_wins():
    rank = {"P2": 0, "P0": 1, "P1": 2}
    llm = fake(None, judge_from(lambda t: set()), compare=compare_by_rank(rank.get))
    result = await pipeline.run("a bedtime story", llm)
    s = stages(llm)
    assert s.count("brainstorm") == 1 and s.count("generate") == 3
    assert s.count("compare") == 6  # 3 pairs x 2 orders, no keep-better (all passed)
    assert tag_of(result.story) == "P2"


async def test_selection_tiebreak_soft_failures_then_index():
    # Every comparison ties (position bias). P0 keeps a soft failure, P1 and P2 pass clean:
    # fewer soft failures beats P0, then the earlier index picks P1 over P2.
    llm = fake(None, judge_from(lambda t: {"engagement"} if t.startswith("P0") else set()))
    result = await pipeline.run("a bedtime story", llm)
    assert tag_of(result.story) == "P1"


async def test_selection_filters_hard_failures():
    # P2 would win every comparison, but it still fails a hard check, so it is filtered out.
    rank = {"P2": 0, "P0": 1, "P1": 2}
    llm = fake(None, judge_from(lambda t: {"consistency"} if t.startswith("P2") else set()),
               compare=compare_by_rank(lambda t: rank[t.rstrip("r")]))
    result = await pipeline.run("a bedtime story", llm)
    assert tag_of(result.story) == "P0"


async def test_select_single_draft_makes_no_calls():
    llm = fake("D", judge_from(lambda t: set()))
    draft = await pipeline.run_draft(llm, _spec(), 0, pipeline.Trace("x"))
    llm.calls.clear()
    assert await pipeline.select(llm, [draft]) is draft
    assert llm.calls == []


def _spec():
    from storyteller.models import StorySpec
    return StorySpec(category="cozy", characters=[], setting=None, premise="D", mood=None,
                     worry=None, named_characters=False)


# ---- behaviour at the cap -----------------------------------------------------------------

async def test_only_nonsafety_hard_failures_returns_best_available():
    # P0 fails two hard checks; P1 and P2 fail one each and tie on comparisons;
    # P2 also has a soft failure, so P1 is the best available.
    fails = {"P0": {"wind_down", "consistency"}, "P1": {"consistency"},
             "P2": {"consistency", "engagement"}}
    llm = fake(None, judge_from(lambda t: fails[t.rstrip("r")]))
    result = await pipeline.run("a bedtime story", llm)
    assert result.status == "story" and tag_of(result.story).startswith("P1")


async def test_best_available_never_picks_a_safety_failure():
    # P0 has the fewest hard failures, but one of them is safety: it must never be shown.
    fails = {"P0": {"safety"}, "P1": {"wind_down", "consistency"},
             "P2": {"wind_down", "consistency"}}
    llm = fake(None, judge_from(lambda t: fails[t.rstrip("r")]))
    result = await pipeline.run("a bedtime story", llm)
    assert result.status == "story" and not tag_of(result.story).startswith("P0")


async def test_all_fail_safety_uses_fallback_story():
    llm = fake("D", judge_from(lambda t: set() if t == "FB" else {"safety"}))
    result = await pipeline.run("a dragon", llm)
    assert result.status == "story" and tag_of(result.story) == "FB"
    fallback_system = [c[1] for c in llm.calls if c[0] == "generate"][-1]
    assert "<cozy>" in fallback_system and "Premise:" not in fallback_system
    # The fallback gets one evaluation and no revisions of its own.
    assert stages(llm).count("revise") == config.MAX_ROUNDS
    assert stages(llm).count("judge") == config.MAX_ROUNDS + 2


async def test_fallback_fails_safety_returns_canned():
    llm = fake(None, judge_from(lambda t: {"safety"}))
    result = await pipeline.run("a bedtime story", llm)
    assert result.status == "safety_fallback_message"
    assert result.story is None
    assert result.message == pipeline.CANNED_SAFETY_MESSAGE
    trace = json.load(open(result.trace_path))
    assert trace["final"]["status"] == "safety_fallback_message"
    assert "safety" in trace["fallback"]["evaluation"]["hard_failures"]


# ---- trace, errors, baseline --------------------------------------------------------------

async def test_trace_written_with_required_keys():
    llm = fake(None, judge_from(lambda t: {"engagement"} if t == "P0" else set()))
    result = await pipeline.run("a bedtime story", llm)
    trace = json.load(open(result.trace_path))
    for key in ["gate", "extraction", "branch", "drafts", "final", "timings", "usage",
                "total_cost_usd", "latency_budget_exceeded"]:
        assert key in trace, key
    assert trace["branch"] == "breadth"
    assert [d["index"] for d in trace["drafts"]] == [0, 1, 2]
    assert len(trace["drafts"][0]["versions"]) == config.MAX_ROUNDS + 1
    assert len(trace["drafts"][0]["comparisons"]) == config.MAX_ROUNDS
    assert trace["drafts"][0]["versions"][1]["feedback_sent"].startswith("- engagement")
    assert "selection" in trace


async def test_budget_exceeded_returns_error_and_writes_trace():
    def boom(*_):
        raise BudgetExceeded("over")
    llm = fake("D", judge_from(lambda t: set()))
    llm.script["generate"] = [boom]
    result = await pipeline.run("a dragon", llm)
    assert result.status == "error" and result.story is None and result.message
    trace = json.load(open(result.trace_path))
    assert "over" in trace["error"] and trace["final"]["status"] == "error"


async def test_trace_written_even_when_run_raises():
    def crash(*_):
        raise RuntimeError("unexpected")
    llm = fake("D", judge_from(lambda t: set()), gate=crash)
    with pytest.raises(RuntimeError):
        await pipeline.run("a dragon", llm)
    assert len(os.listdir(config.RUNS_DIR)) == 1


async def test_run_without_llm_builds_one_client_wired_to_trace(monkeypatch):
    made = []

    class Client(FakeLLM):
        def __init__(self, on_usage=None):
            super().__init__({"gate": [lambda *_: GateResult(reason="no", safe=False,
                                                             relevant=True)]})
            self.on_usage = on_usage
            made.append(self)

    monkeypatch.setattr(pipeline, "OpenRouterClient", Client)
    await pipeline.run("x")
    assert len(made) == 1 and made[0].on_usage.__self__.__class__ is pipeline.Trace


async def test_baseline_is_one_plain_call():
    llm = FakeLLM({"baseline": ["once upon a time"]})
    assert await pipeline.baseline("a cat story", llm) == "once upon a time"
    assert llm.calls == [("baseline", "", "a cat story")]


async def test_verbose_details_print_from_trace(capsys):
    import main
    llm = fake(None, judge_from(lambda t: {"engagement"} if t == "P0" else set()))
    result = await pipeline.run("a bedtime story", llm)
    main.print_details(result.trace_path)
    out = capsys.readouterr().out
    assert "branch: breadth" in out and "draft 0" in out and "final: PASS" in out
    assert "total cost: $0.0000" in out and result.trace_path in out


# ---- regressions from the wave 5 review --------------------------------------------------

async def test_failed_draft_cancels_the_others():
    import asyncio
    cancelled = []

    async def boom():
        raise BudgetExceeded("over")

    never = asyncio.Event()  # conftest makes asyncio.sleep instant, so block on an Event

    async def slow():
        try:
            await never.wait()
        except asyncio.CancelledError:
            cancelled.append(True)  # plain asyncio.gather would leave this task running
            raise

    with pytest.raises(BudgetExceeded):
        await pipeline._all_or_cancel([boom(), slow()])
    assert cancelled == [True]


async def test_missing_key_still_writes_trace(monkeypatch):
    def no_key(**_):
        raise RuntimeError("OPENROUTER_API_KEY not set")
    monkeypatch.setattr(pipeline, "OpenRouterClient", no_key)
    with pytest.raises(RuntimeError):
        await pipeline.run("a dragon")
    assert len(os.listdir(config.RUNS_DIR)) == 1
