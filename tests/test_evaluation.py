import pytest

from storyteller import config, feedback, judge, prompts
from storyteller.fake import FakeLLM
from storyteller.models import Character, Evaluation, JudgeResult, StorySpec, Verdict
from string import Template

DIMS = config.HARD + [d for d in config.SOFT if d != "length"]
GOOD_STORY = " ".join(["word"] * 600)


@pytest.fixture(autouse=True)
def stub_prompts(monkeypatch):
    stubs = {"judge": Template("J $rubric_context | $category_checks"),
             "cozy": Template("## Structure\nx\n## Judge checks\n- cosy check\n")}
    monkeypatch.setattr(prompts, "load", lambda name: stubs.get(name, Template("stub")))


def spec(**kw):
    base = dict(category="cozy", characters=[Character(name="Mia", role="a mouse")], setting="a barn", premise="p",
                worry=None)
    return StorySpec(**{**base, **kw})


def judge_result(fail=()):
    return JudgeResult(**{d: Verdict(evidence="e", passed=d not in fail, fix=f"fix {d}")
                          for d in DIMS})


def ev(hard=(), soft=(), words=600):
    return Evaluation(judge=judge_result(set(hard) | set(soft)), word_count=words,
                      length_ok=True, hard_failures=list(hard), soft_failures=list(soft))


async def test_skips_ignored_even_if_judge_fails_them():
    s = spec(characters=[], setting=None, premise=None)
    llm = FakeLLM({"judge": [judge_result(fail={"faithfulness_named",
                                                "faithfulness_premise"})]})
    e = await judge.evaluate(llm, s, GOOD_STORY)
    assert e.hard_failures == [] and e.soft_failures == []


async def test_judge_failures_reported_and_prompt_has_context():
    llm = FakeLLM({"judge": [judge_result(fail={"safety", "engagement"})]})
    e = await judge.evaluate(llm, spec(), GOOD_STORY)
    assert e.hard_failures == ["safety"] and e.soft_failures == ["engagement"]
    system = llm.calls[0][1]
    assert "Mia (a mouse)" in system and "cosy check" in system


async def test_length_failure_is_soft():
    llm = FakeLLM({"judge": [judge_result()]})
    e = await judge.evaluate(llm, spec(), "too short")
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
    await judge.evaluate(llm, spec(), GOOD_STORY)
    _, system, user = llm.calls[0]
    assert user == f"STORY:\n{GOOD_STORY}" and "revis" not in (system + user).lower()
