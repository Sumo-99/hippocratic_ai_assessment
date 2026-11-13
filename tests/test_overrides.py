"""Overrides applied in code. FakeLLM only; prompt templates stubbed."""
from string import Template
from typing import get_args

import pytest
from pydantic import ValidationError

from storyteller import config, prompts
from storyteller.extract import extract, quoted
from storyteller.fake import FakeLLM
from storyteller.models import Character, Evaluation, Extraction, JudgeResult, Override, Verdict, OverridableCheck
from storyteller.overrides import apply_overrides, overridable_text

DIMS = config.HARD + [d for d in config.SOFT if d != "length"]


def judge_result(fail=()):
    return JudgeResult(**{d: Verdict(evidence="e", passed=d not in fail, fix=f"fix {d}")
                          for d in DIMS})


def ev(hard=(), soft=()):
    return Evaluation(judge=judge_result(set(hard) | set(soft)), word_count=600,
                      length_ok=True, hard_failures=list(hard), soft_failures=list(soft))


def ov(dim, quote="q"):
    return Override(quote=quote, dimension=dim, allow="x")


def ext(**kw):
    base = dict(characters=[], setting=None, premise=None, listener=None,
                category=None)
    return Extraction(**{**base, **kw})


def test_overridden_hard_failure_moves_to_overridden():
    out = apply_overrides(ev(hard=["wind_down", "consistency"]), [ov("wind_down")])
    assert out.hard_failures == ["consistency"] and out.overridden == ["wind_down"]


def test_overridden_soft_failure_moves_to_overridden():
    out = apply_overrides(ev(soft=["length", "engagement"]), [ov("length")])
    assert out.soft_failures == ["engagement"] and out.overridden == ["length"]


def test_safety_is_never_overridden_even_if_smuggled_in():
    sneaky = Override.model_construct(quote="x", dimension="safety", allow="x")
    out = apply_overrides(ev(hard=["safety"]), [sneaky])
    assert out.hard_failures == ["safety"] and out.overridden == []


def test_safety_is_not_representable():
    with pytest.raises(ValidationError):
        Override(quote="x", dimension="safety", allow="x")
    assert "safety" not in Override.model_json_schema()["$defs"]["OverridableCheck"]["enum"] \
        if "$defs" in Override.model_json_schema() else \
        "safety" not in Override.model_json_schema()["properties"]["dimension"]["enum"]


def test_overridable_enum_matches_config():
    assert set(get_args(OverridableCheck)) == set(config.OVERRIDABLE_CHECKS)
    assert "safety" not in config.OVERRIDABLE_CHECKS


def test_no_overrides_returns_the_same_evaluation():
    e = ev(hard=["wind_down"], soft=["length"])
    out = apply_overrides(e, [])
    assert out == e and out.overridden == []


def test_judge_verdict_is_untouched():
    out = apply_overrides(ev(hard=["wind_down"]), [ov("wind_down")])
    assert out.judge.wind_down.passed is False


def test_all_passed_true_when_only_overridden_failures_remain():
    out = apply_overrides(ev(hard=["wind_down"], soft=["length"]),
                          [ov("wind_down"), ov("length")])
    assert out.all_passed and out.overridden == ["wind_down", "length"]


def test_overridable_text_lists_every_overridable_dimension_and_not_safety():
    text = overridable_text()
    for d in config.OVERRIDABLE_CHECKS:
        assert f"- {d}: " in text
    assert "safety" not in text
    assert text.count("\n") == len(config.OVERRIDABLE_CHECKS) - 1


def test_quoted_ignores_case_and_whitespace():
    assert quoted("Leave it   hanging", "tell a story and leave it hanging")
    assert not quoted("leave it hanging", "an exciting adventure")
    assert not quoted("", "anything")


async def test_extract_drops_overrides_whose_quote_is_not_in_the_text(monkeypatch):
    monkeypatch.setattr(prompts, "load", lambda name: Template("X $overridable_checks"))
    reply = ext(characters=[Character(name=None, role=None)],
                overrides=[ov("wind_down", quote="leave it hanging"),
                           ov("story_arc", quote="invented words")])
    out = await extract(FakeLLM({"extract": [reply]}), "a fox story, and leave it hanging")
    assert [o.dimension for o in out.overrides] == ["wind_down"]
    assert out.characters == []  # the existing empty-character filter still runs


async def test_extract_substitutes_overridable_checks(monkeypatch):
    monkeypatch.setattr(prompts, "load", lambda name: Template("X $overridable_checks"))
    llm = FakeLLM({"extract": [ext()]})
    await extract(llm, "hi")
    system = llm.calls[0][1]
    assert "wind_down" in system and "- safety" not in system


def test_quote_must_match_whole_words():
    """quote="end" must not match inside "friend"; it still matches as a word."""
    assert not quoted("end", "a story about my friend")
    assert quoted("end", "no calm bit at the end")


# ---- keep-wishes line (17_feedback_live_smoke fix) ----------------------------------------

def _soft_ev(soft):
    from storyteller.models import JudgeResult, Verdict
    v = Verdict(evidence="e", passed=True, fix=None)
    judge = JudgeResult(**{d: v for d in JudgeResult.model_fields}).model_copy(
        update={d: Verdict(evidence="e", passed=False, fix=f"fix {d}") for d in soft})
    return Evaluation(judge=judge, word_count=600, length_ok=True, hard_failures=[],
                      soft_failures=list(soft))


def test_build_feedback_appends_keep_wishes_line():
    from storyteller.feedback import KEEP_FEEDBACK, build_feedback
    text = build_feedback(_soft_ev(["category_checks"]), keep="End on a cliffhanger.")
    lines = text.splitlines()
    assert lines[0] == "- category_checks: fix category_checks"
    assert lines[-1] == KEEP_FEEDBACK.format(feedback="End on a cliffhanger.")
    assert "End on a cliffhanger." in lines[-1] and "undo" in lines[-1]


def test_build_feedback_without_wishes_is_unchanged():
    from storyteller.feedback import build_feedback
    ev_ = _soft_ev(["category_checks"])
    assert build_feedback(ev_) == build_feedback(ev_, keep=None) == \
        "- category_checks: fix category_checks"
