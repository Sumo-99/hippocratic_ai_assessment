"""End-to-end tests of the outer feedback loop: request -> story -> feedback -> revised story ->
more feedback / quit. Same tag-word FakeLLM style as tests/test_pipeline.py: every story starts
with a tag (v0 = first draft, v1, v2, ... = each revise call, counted across the whole
conversation), and the fake judge decides what fails from that tag.

One FakeLLM serves the whole conversation, so `llm.calls` accumulates across turns; `since(llm, n)`
looks only at the calls a turn made."""
import json
import os
from string import Template

import pytest

from storyteller import config, pipeline, prompts
from fakes import FakeLLM
from storyteller.generate import PREFERENCES_HEADER
from storyteller.judge import DIMENSIONS
from storyteller.llm import BudgetExceeded
from storyteller.models import (Character, Check, DraftVersion, Evaluation, Extraction, GateResult,
                                JudgeResult, Override,
                                StoryOption, StoryOptions, Verdict)

DIMS = config.HARD + [d for d in config.SOFT if d != "length"]
PAD = " ".join(["word"] * 600)  # keeps every fake story inside WORD_RANGE
MANY = 50
REQUEST = "a story about a girl named Lily and a dragon"


@pytest.fixture(autouse=True)
def isolate(monkeypatch, tmp_path):
    # Like test_pipeline.py, but the judge stub keeps its context so tests can see what the
    # judge was told (e.g. the corrected name).
    def load(name):
        if name == "judge":
            return Template("<judge>\n$rubric_context\n$category_checks")
        return Template(f"<{name}>")
    monkeypatch.setattr(prompts, "load", load)
    monkeypatch.setattr(config, "RUNS_DIR", str(tmp_path / "runs"))


# ---- fake stage behaviour ----------------------------------------------------------------

def gate(_system, text):
    """Rejects anything gory; passes everything else."""
    unsafe = "gory" in text
    return GateResult(safety=Check(evidence="That's too scary for bedtime." if unsafe else "fine",
                                   passed=not unsafe),
                      relevance=Check(evidence="fine", passed=True))


def extraction(_system, text):
    """A tiny deterministic 'model' that reads the whole conversation text, newest ask winning."""
    prefs, overrides = [], []
    if "funnier" in text:
        prefs.append("Make the dragon funnier.")
    if "calm, sleepy ending" in text:  # takes back an earlier cliffhanger ask
        prefs.append("End calm and sleepy.")
    elif "cliffhanger" in text:
        prefs.append("End on a cliffhanger.")
        overrides.append(Override(quote="cliffhanger", dimension="wind_down",
                                  allow="end on a cliffhanger"))
    girl = "Mia" if "Mia" in text else "Lily"
    return Extraction(characters=[Character(name=girl, role="a girl"),
                                  Character(name=None, role="a dragon")],
                      setting=None, premise="a girl and a dragon have an adventure",
                      listener=None, category="adventure",
                      preferences=" ".join(prefs) or None, overrides=overrides)


def generate(*_):
    return f"v0 {PAD}"


def make_revise():
    count = [0]

    def revise(*_):
        count[0] += 1
        return f"v{count[0]} {PAD}"
    return revise


def tag_of(story):
    return story.split()[0]


def num(tag):
    return int(tag[1:])


class Judge:
    """Fake judge whose rule can change between turns: `fails(tag) -> set of failing dims`."""
    def __init__(self, fails=lambda t: set()):
        self.fails = fails

    def __call__(self, _system, user):
        fail = self.fails(tag_of(user.removeprefix("STORY:\n")))
        return JudgeResult(**{d: Verdict(evidence="e", passed=d not in fail, fix=f"fix {d}")
                              for d in DIMS})


def fake(judge=None, extract=extraction):
    return FakeLLM({"gate": [gate] * MANY, "extract": [extract] * MANY,
                    "generate": [generate] * MANY, "revise": [make_revise()] * MANY,
                    "judge": [judge or Judge()] * MANY})


def since(llm, n):
    return llm.calls[n:]


def stages(calls):
    return [c[0] for c in calls]


def revise_calls(calls):
    return [c for c in calls if c[0] == "revise"]


def revise_inputs(calls):
    """The tag of the story each revise call started from."""
    return [tag_of(c[2].split("Story:\n", 1)[1]) for c in revise_calls(calls)]


def read_trace(result):
    with open(result.trace_path) as f:
        return json.load(f)


async def start(llm, request=REQUEST):
    """Run the first turn and return (result, number of calls it made)."""
    result = await pipeline.run(request, llm)
    assert result.status == "story"
    return result, len(llm.calls)


# ---- conversation_text --------------------------------------------------------------------

def test_conversation_text_is_the_bare_request_without_feedback():
    assert pipeline.conversation_text(REQUEST, []) == REQUEST


def test_conversation_text_numbers_feedback_newest_last():
    assert pipeline.conversation_text("a dragon", ["make it funnier", "her name's Mia"]) == (
        "Original request: a dragon\n"
        "Changes asked for after hearing the story (newest last):\n"
        "1. make it funnier\n"
        "2. her name's Mia")


# ---- first turn ---------------------------------------------------------------------------

async def test_initial_run_returns_a_session_with_the_delivered_story():
    llm = fake()
    result, _ = await start(llm)
    s = result.session
    assert s is not None and s.request == REQUEST and s.feedback == []
    assert s.story.text == result.story and tag_of(s.story.text) == "v0"
    assert [c.name for c in s.spec.characters] == ["Lily", None]
    # A request-only run still sends the bare request to the gate, extraction and judge context.
    assert llm.calls[0][2] == REQUEST and llm.calls[1][2] == REQUEST


async def test_every_run_returns_a_session_even_when_rejected():
    """There is always a session: it starts with the request. A rejected first request has
    no story yet, so there is nothing to give feedback on."""
    llm = fake()
    result = await pipeline.run("a gory story", llm)
    assert result.status == "rejected"
    assert result.session.request == "a gory story"
    assert result.session.story is None and result.session.spec is None
    assert result.session.feedback == []


async def test_feedback_without_a_story_is_refused():
    llm = fake()
    rejected = await pipeline.run("a gory story", llm)
    with pytest.raises(ValueError, match="no story"):
        await pipeline.give_feedback(rejected.session, "make it funnier", llm)
    assert stages(llm.calls) == ["gate"]  # nothing more was called


async def test_first_turn_session_has_no_feedback_and_feedback_turn_appends():
    llm = fake()
    first, _ = await start(llm)
    assert first.session.feedback == [] and first.session.story is not None
    second = await pipeline.give_feedback(first.session, "make the dragon funnier", llm)
    assert second.session.feedback == ["make the dragon funnier"]
    assert second.session.request == first.session.request
    assert first.session.feedback == []  # the earlier session object is not mutated


# ---- the headline flow --------------------------------------------------------------------

async def test_make_the_dragon_funnier_end_to_end():
    llm = fake()
    first, n = await start(llm)
    result = await pipeline.give_feedback(first.session, "make the dragon funnier", llm)

    turn = since(llm, n)
    assert stages(turn) == ["gate", "extract", "revise", "judge"]
    convo = pipeline.conversation_text(REQUEST, ["make the dragon funnier"])
    gate_user, extract_user = turn[0][2], turn[1][2]
    assert gate_user == convo and extract_user == convo
    for user in (gate_user, extract_user):
        assert REQUEST in user and "make the dragon funnier" in user
    _, revise_system, revise_user = turn[2]
    assert revise_user == (f"Story:\n{first.story}\n\nFeedback:\n"
                           "- Feedback on this story: make the dragon funnier")
    # The preference block sits on top of the prompt stack, above the base prompt.
    assert revise_system.startswith(f"{PREFERENCES_HEADER}\nMake the dragon funnier.")
    assert revise_system.index("Make the dragon funnier.") < revise_system.index("<base>")
    # The judge is told the whole conversation, not just the original request.
    assert "make the dragon funnier" in turn[3][1]

    assert result.status == "story" and tag_of(result.story) == "v1"
    s = result.session
    assert s.request == REQUEST and s.feedback == ["make the dragon funnier"]
    assert s.story.text == result.story and s.spec.preferences == "Make the dragon funnier."


async def test_feedback_never_calls_generate_or_options(monkeypatch):
    monkeypatch.setattr(config, "OPTIONS_SEED", 3)

    def vague(_system, text):
        return Extraction(characters=[], setting=None, premise=None, listener=None,
                          category=None,
                          preferences="Make it funnier." if "funnier" in text else None)

    def five(*_):
        return StoryOptions(options=[StoryOption(characters=f"c{i}", setting=f"s{i}",
                                                 situation=f"x{i}") for i in range(5)])

    llm = FakeLLM({"gate": [gate] * MANY, "extract": [vague] * MANY, "options": [five],
                   "generate": [generate], "revise": [make_revise()] * MANY,
                   "judge": [Judge()] * MANY})
    first, n = await start(llm, "tell me a story")
    idea = first.session.spec.idea
    assert idea is not None

    result = await pipeline.give_feedback(first.session, "make it funnier", llm)
    turn = since(llm, n)
    assert "generate" not in stages(turn) and "options" not in stages(turn)
    assert stages(turn) == ["gate", "extract", "revise", "judge"]
    assert result.session.spec.idea == idea  # the old option carries over to the new spec
    assert f"Premise: {idea.situation}" in revise_calls(turn)[0][1]


# ---- overrides (overrides) ------------------------------------------------------------------

async def test_cliffhanger_overrides_wind_down_and_delivers():
    judge = Judge()
    llm = fake(judge)
    first, n = await start(llm)
    judge.fails = lambda t: {"wind_down"}  # every version from here on fails wind_down
    result = await pipeline.give_feedback(first.session, "end on a cliffhanger", llm)

    turn = since(llm, n)
    assert result.status == "story"
    assert not any("wind_down" in c[2] for c in revise_calls(turn))
    trace = read_trace(result)
    last = trace["versions"][-1]["evaluation"]
    assert last["overridden"] == ["wind_down"] and last["hard_failures"] == []
    assert trace["final"]["overridden"] == ["wind_down"]
    assert "wind_down" in config.HARD  # overridden per run, never by editing HARD
    assert [o.dimension for o in result.session.spec.overrides] == ["wind_down"]


async def test_override_does_not_hide_other_hard_failures():
    judge = Judge()
    llm = fake(judge)
    first, n = await start(llm)
    judge.fails = lambda t: {"wind_down", "consistency"}
    result = await pipeline.give_feedback(first.session, "end on a cliffhanger", llm)

    loop_revisions = revise_calls(since(llm, n))[1:]  # after the feedback revision itself
    assert len(loop_revisions) == config.MAX_ROUNDS  # consistency keeps the loop running
    for _, _, user in loop_revisions:
        bullets = user.split("Feedback:\n", 1)[1].splitlines()
        # only consistency is a fix bullet; the last line is the keep-wishes reminder
        assert bullets[0] == "- consistency: fix consistency" and len(bullets) == 2
        assert bullets[1].startswith("- Keep the earlier feedback on this story:")
        assert "wind_down" not in "\n".join(bullets)
    assert result.status == "story"
    assert read_trace(result)["final"]["hard_failures"] == ["consistency"]


async def test_full_rubric_runs_on_every_feedback_revision():
    judge = Judge()
    llm = fake(judge)
    first, _ = await start(llm)
    judge.fails = lambda t: {"wind_down", "engagement"}
    schemas_before = len(llm.schemas)
    await pipeline.give_feedback(first.session, "end on a cliffhanger", llm)

    judge_schemas = [s for stage, s in llm.schemas[schemas_before:] if stage == "judge"]
    assert len(judge_schemas) == 1 + config.MAX_ROUNDS  # engagement never clears
    for schema in judge_schemas:  # the overridden wind_down is still asked about
        assert set(schema.model_fields) == set(DIMENSIONS)


async def test_safety_failure_is_never_overridden():
    def smuggler(_system, text):
        e = extraction(_system, text)
        # A model that somehow named safety (the schema forbids it): code must still ignore it.
        bad = Override.model_construct(quote="cliffhanger", dimension="safety", allow="anything")
        return e.model_copy(update={"overrides": [*e.overrides, bad]})

    judge = Judge()
    llm = fake(judge, extract=smuggler)
    first, _ = await start(llm)
    judge.fails = lambda t: {"safety", "wind_down"}
    result = await pipeline.give_feedback(first.session, "end on a cliffhanger", llm)

    assert result.status == "safety_message" and result.story is None
    assert result.message == pipeline.CANNED_SAFETY_MESSAGE
    trace = read_trace(result)
    for v in trace["versions"]:
        assert "safety" not in v["evaluation"]["overridden"]
        assert "safety" in v["evaluation"]["hard_failures"]


async def test_later_feedback_can_take_back_a_override():
    judge = Judge(lambda t: {"wind_down"} if num(t) >= 1 else set())
    llm = fake(judge)
    first, _ = await start(llm)
    second = await pipeline.give_feedback(first.session, "end on a cliffhanger", llm)
    assert read_trace(second)["final"]["overridden"] == ["wind_down"]

    n = len(llm.calls)
    third = await pipeline.give_feedback(second.session, "actually give it a calm, sleepy ending",
                                         llm)
    trace = read_trace(third)
    assert trace["extraction"]["overrides"] == [] and third.session.spec.overrides == []
    loop_revisions = revise_calls(since(llm, n))[1:]
    assert loop_revisions and all("- wind_down: fix wind_down" in c[2] for c in loop_revisions)
    assert trace["final"]["hard_failures"] == ["wind_down"] and trace["final"]["overridden"] == []


async def test_upfront_ask_uses_the_same_path():
    llm = fake(Judge(lambda t: {"wind_down"}))
    result = await pipeline.run("a dragon story that ends on a cliffhanger", llm)
    assert result.status == "story"
    assert stages(llm.calls) == ["gate", "extract", "generate", "judge"]  # nothing to revise
    v0 = read_trace(result)["versions"][0]["evaluation"]
    assert v0["overridden"] == ["wind_down"] and v0["hard_failures"] == []


# ---- safety and the gate on a feedback turn -----------------------------------------------

async def test_unsafe_draft_after_feedback_shows_canned_message_and_keeps_session():
    judge = Judge()
    llm = fake(judge)
    first, _ = await start(llm)
    judge.fails = lambda t: {"safety"} if num(t) >= 1 else set()
    result = await pipeline.give_feedback(first.session, "make the dragon funnier", llm)

    assert result.status == "safety_message" and result.story is None
    assert result.message == pipeline.CANNED_SAFETY_MESSAGE
    assert result.session == first.session  # still the last good story, feedback not recorded
    assert tag_of(result.session.story.text) == "v0" and result.session.feedback == []

    # The user can try different feedback from the last good story.
    judge.fails = lambda t: set()
    n = len(llm.calls)
    retry = await pipeline.give_feedback(result.session, "make her braver", llm)
    assert retry.status == "story" and retry.session.feedback == ["make her braver"]
    assert revise_inputs(since(llm, n)) == ["v0"]


async def test_unsafe_feedback_is_rejected_by_the_gate_and_session_kept():
    llm = fake()
    first, n = await start(llm)
    result = await pipeline.give_feedback(first.session, "make it really gory", llm)
    assert stages(since(llm, n)) == ["gate"]
    assert result.status == "rejected" and result.story is None
    assert "too scary" in result.message
    assert result.session == first.session
    assert read_trace(result)["final"]["status"] == "rejected"


async def test_budget_exceeded_during_feedback_keeps_session():
    judge = Judge()
    llm = fake(judge)
    first, _ = await start(llm)

    def over(_t):
        raise BudgetExceeded("over")
    judge.fails = over
    result = await pipeline.give_feedback(first.session, "make the dragon funnier", llm)
    assert result.status == "error" and result.message == pipeline.BUDGET_MESSAGE
    assert result.session == first.session
    trace = read_trace(result)
    assert "over" in trace["error"] and trace["turn"] == 1


# ---- the guard and the internal loop inside a feedback turn -------------------------------

async def test_feedback_revision_is_not_discarded_by_the_guard():
    """The old story passed everything; the feedback revision fails a hard check. It is still
    the turn's starting point (never guard-compared with the old story), and the loop fixes it."""
    judge = Judge(lambda t: {"consistency"} if t == "v1" else set())
    llm = fake(judge)
    first, n = await start(llm)
    result = await pipeline.give_feedback(first.session, "make the dragon funnier", llm)

    turn = since(llm, n)
    assert revise_inputs(turn) == ["v0", "v1"]  # round 1 repairs the feedback revision
    assert result.status == "story" and tag_of(result.story) == "v2"
    trace = read_trace(result)
    # The old story is not a version of this turn, so the guard never sees it.
    assert [tag_of(v["text"]) for v in trace["versions"]] == ["v1", "v2"]
    assert [g["kept_round"] for g in trace["guard"]] == [1]


async def test_feedback_revision_that_never_clears_is_still_delivered_over_the_old_story():
    judge = Judge(lambda t: {"consistency"} if num(t) >= 1 else set())
    llm = fake(judge)
    first, _ = await start(llm)
    result = await pipeline.give_feedback(first.session, "make the dragon funnier", llm)
    assert result.status == "story" and tag_of(result.story) != "v0"


async def test_feedback_turn_respects_max_rounds_and_returns_best_available():
    judge = Judge(lambda t: {"wind_down"} if num(t) >= 1 else set())
    llm = fake(judge)
    first, n = await start(llm)
    result = await pipeline.give_feedback(first.session, "make the dragon funnier", llm)

    turn = since(llm, n)
    assert len(revise_calls(turn)) == 1 + config.MAX_ROUNDS
    assert result.status == "story"
    assert tag_of(result.story) == f"v{1 + config.MAX_ROUNDS}"  # tie goes to the newer version
    assert read_trace(result)["final"]["hard_failures"] == ["wind_down"]


async def test_revisions_start_from_the_kept_draft():
    """v1 (feedback revision): wind_down. v2: wind_down + consistency (worse, thrown away).
    v3: passes. So round 2 revises the kept v1 again."""
    fails = {"v0": set(), "v1": {"wind_down"}, "v2": {"wind_down", "consistency"}, "v3": set()}
    llm = fake(Judge(lambda t: fails[t]))
    first, n = await start(llm)
    result = await pipeline.give_feedback(first.session, "make the dragon funnier", llm)

    assert revise_inputs(since(llm, n)) == ["v0", "v1", "v1"]
    trace = read_trace(result)
    assert [g["kept_round"] for g in trace["guard"]] == [0, 2]
    assert tag_of(result.story) == "v3" and result.session.story.round == 2


# ---- corrections and several turns --------------------------------------------------------

async def test_name_correction_updates_spec_and_judge_context():
    llm = fake()
    first, n = await start(llm)
    result = await pipeline.give_feedback(first.session, "her name's actually Mia", llm)

    assert [c.name for c in result.session.spec.characters] == ["Mia", None]
    judge_system = next(c[1] for c in since(llm, n) if c[0] == "judge")
    assert "Characters named by the user: Mia (a girl)" in judge_system
    revise_system = revise_calls(since(llm, n))[0][1]
    assert "Mia (a girl)" in revise_system and "Lily (a girl)" not in revise_system


async def test_multiple_feedback_turns_accumulate():
    llm = fake()
    first, _ = await start(llm)
    second = await pipeline.give_feedback(first.session, "make the dragon funnier", llm)
    n = len(llm.calls)
    third = await pipeline.give_feedback(second.session, "end on a cliffhanger", llm)

    turn = since(llm, n)
    convo = pipeline.conversation_text(REQUEST, ["make the dragon funnier", "end on a cliffhanger"])
    assert turn[0][2] == convo and turn[1][2] == convo
    assert convo.index("funnier") < convo.index("cliffhanger")
    assert third.session.feedback == ["make the dragon funnier", "end on a cliffhanger"]
    prefs = third.session.spec.preferences
    assert "funnier" in prefs and "cliffhanger" in prefs
    # The second turn revises the story the first turn delivered.
    assert revise_inputs(turn) == [tag_of(second.story)]
    assert tag_of(third.story) == "v2"


async def test_each_feedback_turn_writes_its_own_trace():
    llm = fake(Judge(lambda t: {"wind_down"} if num(t) >= 1 else set()))
    first, _ = await start(llm)
    second = await pipeline.give_feedback(first.session, "end on a cliffhanger", llm)

    assert first.trace_path != second.trace_path
    assert len(os.listdir(config.RUNS_DIR)) == 2
    t1, t2 = read_trace(first), read_trace(second)
    assert t1["feedback"] == [] and t1["turn"] == 0
    assert t2["feedback"] == ["end on a cliffhanger"] and t2["turn"] == 1
    assert t2["request"] == REQUEST
    assert t2["versions"][0]["feedback_sent"] == (
        "- Feedback on this story: end on a cliffhanger")
    assert t2["final"]["overridden"] == ["wind_down"]
    assert all("overridden" in v["evaluation"] for v in t2["versions"])
    assert "options" not in t2  # no options on a feedback turn


# ---- review fixes (16_feedback_review) ----------------------------------------------------

async def test_no_premise_story_keeps_its_idea_and_feedback_can_add_a_premise(monkeypatch):
    """Rule 3 on a feedback turn: "Alice and her cat Bob" (no premise) got a picked idea on the
    first turn. Feedback never asks for ideas again; the idea carries over, the named fields
    still win, and a premise the feedback adds replaces the idea's situation."""
    monkeypatch.setattr(config, "OPTIONS_SEED", 3)

    def ext(_system, text):
        return Extraction(characters=[Character(name="Bob", role="Alice's cat")], setting=None,
                          premise="Bob loses his bell" if "bell" in text else None,
                          listener=None, category=None)

    def five(*_):
        return StoryOptions(options=[StoryOption(characters=f"c{i}", setting=f"s{i}",
                                                 situation=f"x{i}") for i in range(5)])

    llm = FakeLLM({"gate": [gate] * MANY, "extract": [ext] * MANY, "options": [five],
                   "generate": [generate], "revise": [make_revise()] * MANY,
                   "judge": [Judge()] * MANY})
    first, n = await start(llm, "Alice and her cat Bob")
    idea = first.session.spec.idea
    assert idea is not None

    second = await pipeline.give_feedback(first.session, "make it calmer", llm)
    assert "options" not in stages(since(llm, n)) and second.session.spec.idea == idea
    system = revise_calls(since(llm, n))[0][1]
    assert "Characters: Bob (Alice's cat)" in system and f"Characters: {idea.characters}" not in system
    assert f"Premise: {idea.situation}" in system  # no premise yet: the idea fills it

    n2 = len(llm.calls)
    third = await pipeline.give_feedback(second.session, "make it about Bob losing his bell", llm)
    system = revise_calls(since(llm, n2))[0][1]
    assert "Premise: Bob loses his bell" in system and f"Premise: {idea.situation}" not in system
    assert "options" not in stages(since(llm, n2))


async def test_feedback_can_still_change_the_category():
    def ext(_system, text):
        return extraction(_system, text).model_copy(
            update={"category": "silly" if "sillier" in text else "adventure"})
    llm = fake(extract=ext)
    first, _ = await start(llm)
    result = await pipeline.give_feedback(first.session, "make it sillier", llm)
    assert result.session.spec.category == "silly"


def _ver(rnd, hard, overridden=()):
    v = Verdict(evidence="e", passed=True, fix=None)
    ev = Evaluation(judge=JudgeResult(**{d: v for d in JudgeResult.model_fields}),
                    word_count=600, length_ok=True, hard_failures=list(hard), soft_failures=[],
                    overridden=list(overridden))
    return DraftVersion(round=rnd, text=f"v{rnd}", evaluation=ev, feedback_sent=None)


def test_guard_ignores_overridden_failures():
    """prev fails consistency; new fails faithfulness_named plus an overridden wind_down. Counting
    only blocking failures it is a 1-1 tie, so the new version wins. Counting the overridden one
    too would wrongly keep prev."""
    prev = _ver(0, ["consistency"])
    new = _ver(1, ["faithfulness_named"], overridden=["wind_down"])
    assert pipeline.keep_better(prev, new) is new


async def test_overridden_dimension_is_never_sent_to_a_loop_revision():
    """Non-vacuous version of the cliffhanger check: a loop revision really runs (for a soft
    failure) and its feedback names engagement but never the overridden wind_down."""
    judge = Judge()
    llm = fake(judge)
    first, n = await start(llm)
    judge.fails = lambda t: {"wind_down"} | ({"engagement"} if t == "v1" else set())
    result = await pipeline.give_feedback(first.session, "end on a cliffhanger", llm)
    revs = revise_calls(since(llm, n))
    assert len(revs) == 2  # the feedback revision, then one loop revision
    assert "engagement" in revs[1][2] and "wind_down" not in revs[1][2]
    assert result.status == "story" and tag_of(result.story) == "v2"


# ---- the live-smoke flip-flop (17_feedback_live_smoke): the loop must not undo the change ----

def test_guard_protects_listed_dimensions_on_a_tie():
    def ver(rnd, soft):
        return _ver(rnd, []).model_copy(update={"evaluation": _ver(rnd, []).evaluation.model_copy(
            update={"soft_failures": soft})})
    prev, new = ver(0, ["category_checks"]), ver(1, ["faithfulness_premise"])
    assert pipeline.keep_better(prev, new) is new  # default: soft failures don't count
    assert pipeline.keep_better(prev, new, protect=("faithfulness_premise",)) is prev
    both = ver(2, ["faithfulness_premise"])
    assert pipeline.keep_better(new, both, protect=("faithfulness_premise",)) is both  # tie
    # hard checks still come first: fixing a hard failure beats keeping the protected pass
    hard_prev = _ver(0, ["consistency"])
    assert pipeline.keep_better(hard_prev, new, protect=("faithfulness_premise",)) is new


def cliffhanger_flip_flop(tag):
    """The smoke run, scripted: odd revisions keep the cliffhanger (wind_down fails but is overridden)
    and pick up a soft failure whose fix says 'make it sleepy'; even ones obey that fix, end
    asleep, and so fail faithfulness_premise (the judge reads the whole conversation)."""
    n = num(tag)
    if n == 0:
        return set()
    return {"wind_down", "category_checks"} if n % 2 else {"faithfulness_premise"}


async def test_loop_never_trades_the_users_change_for_a_soft_fix():
    judge = Judge()
    llm = fake(judge)
    first, n = await start(llm)
    judge.fails = cliffhanger_flip_flop
    result = await pipeline.give_feedback(first.session, "end on a cliffhanger", llm)
    turn = since(llm, n)
    # v2 ends asleep, so the guard keeps v1 (cliffhanger). Resending the same feedback from
    # v1 could only repeat the conflict (live run), so the loop stops there: 2 revise calls.
    assert revise_inputs(turn) == ["v0", "v1"]
    assert tag_of(result.story) == "v1"
    trace = read_trace(result)
    assert "faithfulness_premise" not in trace["final"]["soft_failures"]
    assert trace["guard"][-1]["stopped"] == "revision dropped the requested change"


async def test_loop_revisions_carry_the_keep_wishes_line():
    from storyteller.feedback import KEEP_FEEDBACK
    judge = Judge()
    llm = fake(judge)
    first, n = await start(llm)
    judge.fails = cliffhanger_flip_flop
    await pipeline.give_feedback(first.session, "end on a cliffhanger", llm)
    loop = revise_calls(since(llm, n))[1:]
    assert loop and all(KEEP_FEEDBACK.format(feedback="End on a cliffhanger.") in c[2] for c in loop)
    # ...but the feedback revision itself carries only the parent's change
    assert "Keep the earlier feedback" not in revise_calls(since(llm, n))[0][2]


async def test_upfront_wishes_are_protected_too():
    """R10: an up-front cliffhanger ask goes down the same path, so it gets the same guard."""
    judge = Judge(lambda t: {"v0": {"wind_down", "category_checks"},
                             "v1": {"faithfulness_premise"}}.get(t, {"wind_down"}))
    llm = fake(judge)
    result = await pipeline.run("a dragon story that ends on a cliffhanger", llm)
    assert revise_inputs(llm.calls) == ["v0"]  # v1 lost the cliffhanger: not kept, loop stops
    assert tag_of(result.story) == "v0"


async def test_first_run_without_wishes_keeps_the_old_tie_rule():
    """No preferences, no feedback: soft failures still play no part in the guard."""
    judge = Judge(lambda t: {"v0": {"engagement"}, "v1": {"faithfulness_premise"}}.get(t, set()))
    llm = fake(judge)
    await pipeline.run(REQUEST, llm)
    assert revise_inputs(llm.calls)[:2] == ["v0", "v1"]


async def test_new_hard_failure_rejection_still_retries_on_a_feedback_turn():
    """The stop is only for a revision that dropped the requested change. A revision rejected for
    a new hard failure is retried as before (the walkthrough rule)."""
    judge = Judge()
    llm = fake(judge)
    first, n = await start(llm)
    judge.fails = lambda t: {"v1": {"engagement"}, "v2": {"consistency"}}.get(t, set())
    result = await pipeline.give_feedback(first.session, "make the dragon funnier", llm)
    assert revise_inputs(since(llm, n)) == ["v0", "v1", "v1"]  # v2 thrown away, v1 retried
    assert tag_of(result.story) == "v3"
    assert all("stopped" not in g for g in read_trace(result)["guard"])


async def test_cliffhanger_exception_reaches_the_judge_on_the_feedback_turn():
    llm = fake()
    first, n = await start(llm)
    await pipeline.give_feedback(first.session, "end on a cliffhanger", llm)
    judge_systems = [c[1] for c in since(llm, n) if c[0] == "judge"]
    assert judge_systems and all("- wind_down: end on a cliffhanger" in s for s in judge_systems)
    first_judge = next(c[1] for c in llm.calls if c[0] == "judge")
    assert "wind_down: end on a cliffhanger" not in first_judge  # not before it was asked
