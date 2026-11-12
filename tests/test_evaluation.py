import pytest

from storyteller import compare, config, feedback, judge, prompts
from storyteller.fake import FakeLLM
from storyteller.models import (Comparison, DraftVersion, Evaluation, JudgeResult,
                                StorySpec, Verdict)
from string import Template

DIMS = config.HARD + [d for d in config.SOFT if d != "length"]
GOOD_STORY = " ".join(["word"] * 600)


@pytest.fixture(autouse=True)
def stub_prompts(monkeypatch):
    stubs = {"judge": Template("J $rubric_context | $category_checks"),
             "compare": Template("which?"),
             "cozy": Template("## Structure\nx\n## Judge checks\n- cosy check\n")}
    monkeypatch.setattr(prompts, "load", lambda name: stubs.get(name, Template("stub")))


def spec(**kw):
    base = dict(category="cozy", characters=["Mia"], setting="a barn", premise="p",
                mood="calm", worry=None, named_characters=True)
    return StorySpec(**{**base, **kw})


def judge_result(fail=()):
    return JudgeResult(**{d: Verdict(evidence="e", passed=d not in fail, fix=f"fix {d}")
                          for d in DIMS})


def ev(hard=(), soft=(), words=600):
    return Evaluation(judge=judge_result(set(hard) | set(soft)), word_count=words,
                      length_ok=True, hard_failures=list(hard), soft_failures=list(soft))


def version(rnd, hard=()):
    return DraftVersion(round=rnd, text=f"story{rnd}", evaluation=ev(hard=hard),
                        feedback_sent=None)


async def test_skips_ignored_even_if_judge_fails_them():
    s = spec(named_characters=False, setting=None, premise=None, mood=None)
    llm = FakeLLM({"judge": [judge_result(fail={"faithfulness_named",
                                                "faithfulness_premise_mood"})]})
    e = await judge.evaluate(llm, s, GOOD_STORY)
    assert e.hard_failures == [] and e.soft_failures == []


async def test_judge_failures_reported_and_prompt_has_context():
    llm = FakeLLM({"judge": [judge_result(fail={"safety", "engagement"})]})
    e = await judge.evaluate(llm, spec(), GOOD_STORY)
    assert e.hard_failures == ["safety"] and e.soft_failures == ["engagement"]
    system = llm.calls[0][1]
    assert "Mia" in system and "cosy check" in system


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


async def test_compare_both_orders_agree():
    llm = FakeLLM({"compare": [Comparison(reason="r", winner="A"),
                               Comparison(reason="r", winner="B")]})
    assert await compare.compare_both_orders(llm, "X", "Y") == "x"


async def test_compare_both_orders_disagree_is_tie():
    llm = FakeLLM({"compare": [Comparison(reason="r", winner="A")] * 2})
    assert await compare.compare_both_orders(llm, "X", "Y") == "tie"


async def test_keep_better_prefers_more_hard_passes_without_compare():
    llm = FakeLLM({})
    prev, new = version(1, hard=["safety"]), version(2)
    kept, rec = await compare.keep_better(llm, prev, new)
    assert kept is new and llm.calls == [] and rec["kept_round"] == 2
    kept, _ = await compare.keep_better(llm, new, prev)
    assert kept is new and llm.calls == []


async def test_keep_better_tie_keeps_prev():
    llm = FakeLLM({"compare": [Comparison(reason="r", winner="A")] * 2})
    prev, new = version(1), version(2)
    kept, rec = await compare.keep_better(llm, prev, new)
    assert kept is prev and rec["result"] == "prev"


async def test_keep_better_new_wins_both_orders():
    # prev=x, new=y: order1 B (y), order2 A (y)
    llm = FakeLLM({"compare": [Comparison(reason="r", winner="B"),
                               Comparison(reason="r", winner="A")]})
    prev, new = version(1), version(2)
    kept, rec = await compare.keep_better(llm, prev, new)
    assert kept is new and rec == {"rule": "pairwise:y", "result": "new", "kept_round": 2}


# ---- regressions from the wave 5 review --------------------------------------------------

def test_invented_setting_does_not_trigger_named_faithfulness():
    # Breadth mode: the brainstorm invents a setting; the user named nothing.
    invented = spec(named_characters=False, setting="a moonlit forest", named_setting=False)
    assert "faithfulness_named" in judge.skipped_dimensions(invented)
    named = spec(named_characters=False, setting="a moonlit forest", named_setting=True)
    assert "faithfulness_named" not in judge.skipped_dimensions(named)


async def test_keep_better_never_trades_safe_for_unsafe():
    llm = FakeLLM({})
    safe_but_flawed = version(1, hard=["wind_down", "consistency"])
    unsafe = version(2, hard=["safety"])
    kept, rec = await compare.keep_better(llm, safe_but_flawed, unsafe)
    assert kept is safe_but_flawed and rec["rule"] == "hard_checks" and llm.calls == []
