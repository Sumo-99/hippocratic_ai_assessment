"""Stage tests: FakeLLM only, and prompt templates are stubbed so they don't depend on the .md files."""
from string import Template

import pytest

from storyteller import prompts
from storyteller.brainstorm import brainstorm
from storyteller.extract import breadth_categories, extract, normalize, plan_drafts
from storyteller.fake import FakeLLM
from storyteller.gate import check_request, gate_message
from storyteller.generate import (breadth_specs, build_system_prompt, depth_spec,
                                  revise_story, write_story)
from storyteller.llm import LLMError
from storyteller.models import Brainstorm, Extraction, GateResult, Premise, StorySpec

STUBS = {
    "base": "BASE $target_words", "cozy": "COZY", "silly": "SILLY", "adventure": "ADV",
    "comfort": "COMFORT", "gentle_lesson": "LESSON", "gate": "GATE", "extract": "EXTRACT",
    "brainstorm": "BRAIN $characters | $setting | $categories", "revise": "REVISE",
}


@pytest.fixture(autouse=True)
def stub_prompts(monkeypatch):
    monkeypatch.setattr(prompts, "load", lambda name: Template(STUBS[name]))


def ext(**kw):
    base = dict(characters=[], setting=None, premise=None, mood=None, worry=None, category=None)
    return Extraction(**{**base, **kw})


def spec(**kw):
    base = dict(category="cozy", characters=[], setting=None, premise=None, mood=None,
                worry=None, named_characters=False)
    return StorySpec(**{**base, **kw})


def test_gate_message_none_when_ok():
    assert gate_message(GateResult(reason="fine", safe=True, relevant=True)) is None


def test_gate_message_includes_reason():
    msg = gate_message(GateResult(reason="Too scary.", safe=False, relevant=True))
    assert "Too scary." in msg and "try another request" in msg.lower()


async def test_check_request_and_extract_use_stages():
    g = GateResult(reason="ok", safe=True, relevant=True)
    llm = FakeLLM({"gate": [g], "extract": [ext(category="comfort", worry="dark")]})
    assert await check_request(llm, "hi") == g
    assert (await extract(llm, "hi")).category == "comfort"
    assert [c[0] for c in llm.calls] == ["gate", "extract"]


def test_plan_depth_when_premise():
    assert plan_drafts(ext(premise="a lost kite")) == "depth"


def test_plan_breadth_when_no_premise():
    assert plan_drafts(ext(characters=["Bo"])) == "breadth"


def test_breadth_categories_known():
    assert breadth_categories(ext(category="silly")) == ["silly"] * 3


def test_breadth_categories_unknown():
    assert breadth_categories(ext()) == ["cozy", "adventure", "silly"]


def test_comfort_without_worry_normalized_to_cozy():
    assert normalize(ext(category="comfort")).category == "cozy"
    assert normalize(ext(category="comfort", worry="thunder")).category == "comfort"


def _premises(n=3):
    return [Premise(premise=f"p{i}", category="adventure", characters=["X"], setting="Y")
            for i in range(n)]


async def test_brainstorm_forces_named_chars_and_categories():
    llm = FakeLLM({"brainstorm": [Brainstorm(premises=_premises())]})
    out = await brainstorm(llm, ext(characters=["Alice", "Bob"], setting="a barn", category="silly"))
    assert [p.category for p in out] == ["silly"] * 3
    assert all(p.characters == ["Alice", "Bob"] and p.setting == "a barn" for p in out)
    assert "Alice, Bob | a barn | silly, silly, silly" in llm.calls[0][1]


async def test_brainstorm_keeps_model_chars_when_unnamed_and_uses_fallback_set():
    llm = FakeLLM({"brainstorm": [Brainstorm(premises=_premises())]})
    out = await brainstorm(llm, ext())
    assert [p.category for p in out] == ["cozy", "adventure", "silly"]
    assert out[0].characters == ["X"] and out[0].setting == "Y"


async def test_brainstorm_rejects_wrong_count():
    llm = FakeLLM({"brainstorm": [Brainstorm(premises=_premises(2))]})
    with pytest.raises(LLMError):
        await brainstorm(llm, ext())


def test_system_prompt_omits_absent_variables():
    p = build_system_prompt(spec(characters=["Alice", "Bob"], setting="a barn"))
    assert "Characters: Alice, Bob" in p and "Setting: a barn" in p
    for absent in ("Mood:", "Worry:", "Premise:"):
        assert absent not in p
    assert p.startswith("BASE 600") and "COZY" in p


def test_system_prompt_with_no_variables_has_no_trailing_lines():
    assert build_system_prompt(spec()) == "BASE 600\n\nCOZY"


def test_depth_spec_falls_back_to_cozy():
    s = depth_spec(ext(premise="a kite", characters=["Bo"]))
    assert s.category == "cozy" and s.named_characters and s.premise == "a kite"


def test_breadth_specs_named_flag_only_for_user_names():
    s = breadth_specs(ext(), _premises())
    assert [x.category for x in s] == ["cozy", "adventure", "silly"]
    assert not any(x.named_characters for x in s)
    assert all(x.named_characters for x in breadth_specs(ext(characters=["Bo"]), _premises()))


async def test_write_and_revise():
    llm = FakeLLM({"generate": ["story"], "revise": ["better"]})
    sp = spec(mood="calm")
    assert await write_story(llm, sp) == "story"
    assert await revise_story(llm, sp, "story", "shorter") == "better"
    stage, system, user = llm.calls[1]
    assert stage == "revise" and system.endswith("REVISE") and "Mood: calm" in system
    assert "story" in user and "shorter" in user


def test_named_setting_tracks_only_what_the_user_named():
    vague = Extraction(characters=[], setting=None, premise=None, mood=None, worry=None,
                       category=None)
    premises = [Premise(premise=f"p{i}", category="cozy", characters=["Owl"], setting="a tree")
                for i in range(3)]
    assert all(not s.named_setting for s in breadth_specs(vague, premises))
    with_setting = vague.model_copy(update={"setting": "a lighthouse", "premise": "p"})
    assert depth_spec(with_setting).named_setting is True
