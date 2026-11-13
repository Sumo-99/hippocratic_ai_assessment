import pytest

from storyteller import config, feedback, judge, prompts
from fakes import FakeLLM
from storyteller.models import Character, Evaluation, JudgeResult, StorySpec, Verdict
from string import Template

DIMS = config.HARD + [d for d in config.SOFT if d != "length"]
GOOD_STORY = " ".join(["word"] * 600)
REQUEST = "Mia the mouse finds a hat in the barn"


@pytest.fixture(autouse=True)
def stub_prompts(monkeypatch):
    stubs = {"judge": Template("J $rubric_context | $category_checks"),
             "cozy": Template("## Structure\nx\n## Judge checks\n- cosy check\n")}
    monkeypatch.setattr(prompts, "load", lambda name: stubs.get(name, Template("stub")))


def spec(**kw):
    base = dict(category="cozy", characters=[Character(name="Mia", role="a mouse")], setting="a barn", premise="p",
                listener=None)
    return StorySpec(**{**base, **kw})


def judge_result(fail=()):
    return JudgeResult(**{d: Verdict(evidence="e", passed=d not in fail, fix=f"fix {d}")
                          for d in DIMS})


def ev(hard=(), soft=(), words=600):
    return Evaluation(judge=judge_result(set(hard) | set(soft)), word_count=words,
                      length_ok=True, hard_failures=list(hard), soft_failures=list(soft))


async def test_skipped_dimensions_are_not_sent_and_recorded_as_skipped():
    s = spec(characters=[], setting=None, premise=None)
    # Even if a (fake) judge returned verdicts for them, skipped dimensions are not used.
    llm = FakeLLM({"judge": [judge_result(fail={"faithfulness_named",
                                                "faithfulness_premise"})]})
    e = await judge.evaluate(llm, s, GOOD_STORY, REQUEST)
    assert e.hard_failures == [] and e.soft_failures == []
    sent = set(llm.schemas[0][1].model_fields)
    assert not sent & {"faithfulness_named", "faithfulness_premise"}
    assert sent == set(DIMS) - {"faithfulness_named", "faithfulness_premise"}
    for d in ("faithfulness_named", "faithfulness_premise"):
        assert getattr(e.judge, d).passed is None
    assert e.judge.safety.passed is True


async def test_faithfulness_sent_when_spec_has_the_fields():
    llm = FakeLLM({"judge": [judge_result()]})
    await judge.evaluate(llm, spec(), GOOD_STORY, REQUEST)
    sent = set(llm.schemas[0][1].model_fields)
    assert {"faithfulness_named", "faithfulness_premise"} <= sent


async def test_judge_failures_reported_and_prompt_has_context():
    llm = FakeLLM({"judge": [judge_result(fail={"safety", "engagement"})]})
    e = await judge.evaluate(llm, spec(), GOOD_STORY, REQUEST)
    assert e.hard_failures == ["safety"] and e.soft_failures == ["engagement"]
    system = llm.calls[0][1]
    assert "Mia (a mouse)" in system and "cosy check" in system
    assert REQUEST in system  # the raw request reaches the judge


async def test_length_failure_is_soft():
    llm = FakeLLM({"judge": [judge_result()]})
    e = await judge.evaluate(llm, spec(), "too short", REQUEST)
    assert e.soft_failures == ["length"] and e.hard_failures == [] and not e.length_ok


def test_length_bounds_inclusive():
    assert judge.length_ok(" ".join(["w"] * 400)) and judge.length_ok(" ".join(["w"] * 900))
    assert not judge.length_ok(" ".join(["w"] * 399))


def test_feedback_hard_only_when_any_hard_fails():
    text = feedback.build_feedback(ev(hard=["safety"], soft=["engagement"]))
    assert "fix safety" in text and "engagement" not in text


def test_feedback_soft_when_no_hard():
    e = ev(soft=["engagement", "length"], words=1000)
    text = feedback.build_feedback(e)
    assert "fix engagement" in text and "1000" in text and "400" in text and "900" in text


def test_named_faithfulness_runs_when_only_a_setting_was_named():
    assert "faithfulness_named" not in judge.skipped_dimensions(spec(characters=[]))
    assert "faithfulness_named" in judge.skipped_dimensions(spec(characters=[], setting=None))


def test_category_checks_skipped_without_a_category():
    assert "category_checks" in judge.skipped_dimensions(spec(category=None))
    assert "category_checks" not in judge.skipped_dimensions(spec())


async def test_judge_is_never_told_about_revisions():
    llm = FakeLLM({"judge": [judge_result()]})
    await judge.evaluate(llm, spec(), GOOD_STORY, REQUEST)
    _, system, user = llm.calls[0]
    assert user == f"STORY:\n{GOOD_STORY}" and "revis" not in (system + user).lower()


# ---- precise override: the parent's exceptions reach the judge (17_feedback_live_smoke) -------

def test_rubric_context_without_overrides_is_unchanged():
    ctx = judge._rubric_context(spec(), REQUEST)
    assert "exception" not in ctx.lower()
    assert ctx.splitlines()[-1].startswith("Premise:")  # nothing appended after the variables


def test_rubric_context_lists_the_parents_exceptions():
    from storyteller.models import Override
    sp = spec(overrides=[Override(quote="end on a cliffhanger", dimension="wind_down",
                                  allow="end on a cliffhanger")])
    ctx = judge._rubric_context(sp, REQUEST)
    assert judge.EXCEPTIONS_HEADER in ctx
    assert "- wind_down: end on a cliffhanger" in ctx
    # the header tells every dimension not to fail or "fix" the exception, safety excepted
    assert "never" in judge.EXCEPTIONS_HEADER.lower() and "safety" in judge.EXCEPTIONS_HEADER.lower()


def test_rubric_context_never_lists_safety_even_if_smuggled():
    from storyteller.models import Override
    smuggled = Override.model_construct(quote="x", dimension="safety", allow="anything goes")
    ctx = judge._rubric_context(spec(overrides=[smuggled]), REQUEST)
    assert "anything goes" not in ctx and judge.EXCEPTIONS_HEADER not in ctx


async def test_judge_system_prompt_carries_the_exceptions():
    from storyteller.models import Override
    sp = spec(overrides=[Override(quote="leave it hanging", dimension="wind_down",
                                  allow="leave the ending open")])
    llm = FakeLLM({"judge": [judge_result()]})
    await judge.evaluate(llm, sp, GOOD_STORY, REQUEST)
    assert "- wind_down: leave the ending open" in llm.calls[0][1]
