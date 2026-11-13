"""Stage tests: FakeLLM only, and prompt templates are stubbed so they don't depend on the .md files."""
from string import Template

import pytest

from storyteller import prompts
from storyteller.extract import extract, normalize
from storyteller.fake import FakeLLM
from storyteller.gate import check_request, gate_message
from storyteller.generate import build_system_prompt, make_spec, revise_story, write_story
from storyteller.models import Character, Check, Extraction, GateResult, StorySpec

STUBS = {
    "base": "BASE $target_words", "cozy": "COZY", "silly": "SILLY", "adventure": "ADV",
    "comfort": "COMFORT", "gentle_lesson": "LESSON", "gate": "GATE", "extract": "EXTRACT",
    "revise": "REVISE",
}


@pytest.fixture(autouse=True)
def stub_prompts(monkeypatch):
    monkeypatch.setattr(prompts, "load", lambda name: Template(STUBS[name]))


def ext(**kw):
    base = dict(characters=[], setting=None, premise=None, worry=None, listener=None,
                category=None)
    return Extraction(**{**base, **kw})


def spec(**kw):
    base = dict(category="cozy", characters=[], setting=None, premise=None, worry=None)
    return StorySpec(**{**base, **kw})


# ---- gate ---------------------------------------------------------------------------------

def gate_result(safe=True, relevant=True, safety_ev="fine", relevance_ev="fine"):
    return GateResult(safety=Check(evidence=safety_ev, passed=safe),
                      relevance=Check(evidence=relevance_ev, passed=relevant))


def test_gate_message_none_when_both_checks_pass():
    assert gate_message(gate_result()) is None


def test_gate_message_uses_the_failed_checks_evidence():
    msg = gate_message(gate_result(safe=False, safety_ev="Too scary."))
    assert "Too scary." in msg and "try another request" in msg.lower()
    msg = gate_message(gate_result(relevant=False, relevance_ev="Not a story."))
    assert "Not a story." in msg


def test_gate_message_reports_safety_when_both_fail():
    msg = gate_message(gate_result(safe=False, relevant=False, safety_ev="Unsafe.",
                                   relevance_ev="Not a story."))
    assert "Unsafe." in msg and "Not a story." not in msg


async def test_gate_and_extract_are_separate_calls():
    g = gate_result()
    llm = FakeLLM({"gate": [g], "extract": [ext(category="comfort", worry="dark")]})
    assert await check_request(llm, "hi") == g
    assert (await extract(llm, "hi")).category == "comfort"
    assert [c[0] for c in llm.calls] == ["gate", "extract"]


# ---- extraction -> spec -------------------------------------------------------------------

def test_comfort_without_worry_loses_its_category():
    assert normalize(ext(category="comfort")).category is None
    assert normalize(ext(category="comfort", worry="thunder")).category == "comfort"


def test_normalize_drops_empty_characters():
    e = ext(characters=[Character(name=None, role=None), Character(name="Bob", role="a cat")])
    assert normalize(e).characters == [Character(name="Bob", role="a cat")]


def test_character_describe():
    assert Character(name="Bob", role="Alice's cat").describe() == "Bob (Alice's cat)"
    assert Character(name="Alice", role=None).describe() == "Alice"
    assert Character(name=None, role="a badger").describe() == "a badger"


def test_make_spec_falls_back_to_cozy_only_when_nothing_is_named():
    assert make_spec(ext()).category == "cozy"
    assert make_spec(ext(listener="son", worry=None)).category == "cozy"  # listener isn't content
    for named in (dict(premise="a kite"), dict(setting="a barn"),
                  dict(characters=[Character(name="Bo", role="a bear")])):
        assert make_spec(ext(**named)).category is None
    s = make_spec(ext(premise="a kite", characters=[Character(name="Bo", role="a bear")], worry="thunder"))
    assert s.premise == "a kite" and s.characters == [Character(name="Bo", role="a bear")]
    assert make_spec(ext(category="silly", premise="a kite")).category == "silly"


def test_make_spec_carries_listener():
    assert make_spec(ext(listener="daughter")).listener == "daughter"


# ---- prompt assembly ----------------------------------------------------------------------

def test_system_prompt_omits_absent_variables():
    p = build_system_prompt(spec(characters=[Character(name="Alice", role=None),
                                Character(name="Bob", role="Alice's cat")], setting="a barn"))
    assert "Characters: Alice; Bob (Alice's cat)" in p and "Setting: a barn" in p
    for absent in ("Mood:", "Worry:", "Premise:"):
        assert absent not in p
    assert p.startswith("BASE 600") and "COZY" in p


def test_system_prompt_with_no_variables_has_no_trailing_lines():
    assert build_system_prompt(spec()) == "BASE 600\n\nCOZY"


def test_system_prompt_without_category_has_no_bundle():
    p = build_system_prompt(spec(category=None, premise="a kite"))
    assert p == "BASE 600\n\nPremise: a kite"


async def test_write_and_revise():
    llm = FakeLLM({"generate": ["story"], "revise": ["better"]})
    sp = spec(worry="thunder")
    assert await write_story(llm, sp) == "story"
    assert await revise_story(llm, sp, "story", "shorter") == "better"
    stage, system, user = llm.calls[1]
    # Revision = the same constraints as the first draft + the revise rules, then the full
    # previous story and the feedback in the user message.
    assert stage == "revise" and system.startswith(build_system_prompt(sp))
    assert system.endswith("REVISE") and "Worry: thunder" in system
    assert "story" in user and "shorter" in user
