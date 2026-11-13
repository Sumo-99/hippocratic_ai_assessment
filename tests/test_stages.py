"""Stage tests: FakeLLM only, and prompt templates are stubbed so they don't depend on the .md files."""
from string import Template

import pytest

from storyteller import prompts
from storyteller.extract import extract
from fakes import FakeLLM
from storyteller.gate import check_request, gate_message
from storyteller.generate import build_system_prompt, revise_story, write_story
from storyteller.models import Character, Check, Extraction, GateResult, StorySpec

STUBS = {
    "base": "BASE $target_words", "cozy": "COZY", "silly": "SILLY", "adventure": "ADV",
    "comfort": "COMFORT", "gate": "GATE", "extract": "EXTRACT",
    "revise": "REVISE",
}


@pytest.fixture(autouse=True)
def stub_prompts(monkeypatch):
    monkeypatch.setattr(prompts, "load", lambda name: Template(STUBS[name]))


def ext(**kw):
    base = dict(characters=[], setting=None, premise=None, listener=None, category=None)
    return Extraction(**{**base, **kw})


def spec(**kw):
    base = dict(category="cozy", characters=[], setting=None, premise=None, listener=None)
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
    llm = FakeLLM({"gate": [g], "extract": [ext(category="comfort", premise="scared of the dark")]})
    assert await check_request(llm, "hi") == g
    assert (await extract(llm, "hi")).category == "comfort"
    assert [c[0] for c in llm.calls] == ["gate", "extract"]


# ---- extraction ---------------------------------------------------------------------------

async def test_extract_drops_empty_characters():
    e = ext(characters=[Character(name=None, role=None), Character(name="Bob", role="a cat")])
    llm = FakeLLM({"extract": [e]})
    assert (await extract(llm, "hi")).characters == [Character(name="Bob", role="a cat")]


def test_character_describe():
    assert Character(name="Bob", role="Alice's cat").describe() == "Bob (Alice's cat)"
    assert Character(name="Alice", role=None).describe() == "Alice"
    assert Character(name=None, role="a badger").describe() == "a badger"


def test_spec_inherits_preferences_and_overrides_from_the_extraction():
    """pipeline builds StorySpec(**extraction.model_dump()): the feedback (preferences) and overrides
    reach the writer and judge with no copying step."""
    from storyteller.models import Override
    o = Override(quote="end on a cliffhanger", dimension="wind_down", allow="end on a cliffhanger")
    e = ext(premise="a kite", preferences="End on a cliffhanger.", overrides=[o])
    s = StorySpec(**e.model_dump())
    assert s.preferences == "End on a cliffhanger." and s.overrides == [o]
    plain = StorySpec(**ext(premise="a kite").model_dump())
    assert plain.preferences is None and plain.overrides == []


# ---- prompt assembly ----------------------------------------------------------------------

def test_system_prompt_omits_absent_variables():
    p = build_system_prompt(spec(characters=[Character(name="Alice", role=None),
                                Character(name="Bob", role="Alice's cat")], setting="a barn"))
    assert "Characters: Alice; Bob (Alice's cat)" in p and "Setting: a barn" in p
    for absent in ("Worry:", "Premise:"):
        assert absent not in p
    assert p.startswith("BASE 600") and "COZY" in p


def test_system_prompt_with_no_variables_has_no_trailing_lines():
    assert build_system_prompt(spec()) == "BASE 600\n\nCOZY"


def test_system_prompt_includes_listener():
    assert build_system_prompt(spec(listener="daughter")).endswith("Listener: daughter")


def test_system_prompt_without_category_has_no_bundle():
    p = build_system_prompt(spec(category=None, premise="a kite"))
    assert p == "BASE 600\n\nPremise: a kite"


PREFS_BLOCK = ("## Feedback on this story (this comes first)\n"
               "Where this feedback conflicts with anything below, follow the feedback, "
               "except the Safety rules, which always apply.\n"
               "Make the dragon funnier.")


def test_preferences_block_sits_on_top_of_the_prompt():
    p = build_system_prompt(spec(preferences="Make the dragon funnier.", premise="a kite"))
    assert p == PREFS_BLOCK + "\n\nBASE 600\n\nCOZY\n\nPremise: a kite"
    assert p.index("Make the dragon funnier.") < p.index("BASE")
    assert "except the Safety rules, which always apply" in p


def test_no_preferences_means_prompt_unchanged():
    # Byte-identical to a request-only run: no header, no extra blank lines.
    assert build_system_prompt(spec()) == "BASE 600\n\nCOZY"
    assert build_system_prompt(spec(preferences="")) == "BASE 600\n\nCOZY"
    assert "wishes" not in build_system_prompt(spec(premise="a kite", listener="son"))


async def test_revise_keeps_preferences_on_top():
    llm = FakeLLM({"revise": ["better"]})
    await revise_story(llm, spec(preferences="Make the dragon funnier."), "story", "funnier")
    system = llm.calls[0][1]
    assert system.startswith(PREFS_BLOCK + "\n\nBASE 600") and system.endswith("REVISE")


async def test_write_and_revise():
    llm = FakeLLM({"generate": ["story"], "revise": ["better"]})
    sp = spec(premise="thunder")
    assert await write_story(llm, sp) == "story"
    assert await revise_story(llm, sp, "story", "shorter") == "better"
    stage, system, user = llm.calls[1]
    # Revision = the same constraints as the first draft + the revise rules, then the full
    # previous story and the feedback in the user message.
    assert stage == "revise" and system.startswith(build_system_prompt(sp))
    assert system.endswith("REVISE") and "Premise: thunder" in system
    assert "story" in user and "shorter" in user


# ---- story ideas for requests with no premise -----------------------------------------------

def idea():
    from storyteller.models import StoryOption
    return StoryOption(characters="a badger and a heron", setting="a reed bed",
                       situation="mending a nest")


def test_picked_idea_fills_only_what_the_request_left_empty():
    p = build_system_prompt(spec(idea=idea(), listener="son"))
    assert p == ("BASE 600\n\nCOZY\n\nCharacters: a badger and a heron\nSetting: a reed bed\n"
                 "Premise: mending a nest\nListener: son")
    # Named characters win over the idea's; the idea still supplies setting and premise.
    p = build_system_prompt(spec(idea=idea(), characters=[Character(name="Alice", role=None)]))
    assert "Characters: Alice\n" in p and "badger" not in p
    assert "Setting: a reed bed" in p and "Premise: mending a nest" in p


async def test_options_prompt_asks_for_the_category_and_keeps_named_things(monkeypatch):
    from storyteller.models import StoryOption, StoryOptions
    from storyteller.options import get_options
    monkeypatch.setattr(prompts, "load", lambda name: Template("OPTIONS $story_type|$keep"))
    opts = StoryOptions(options=[StoryOption(characters="c", setting="s", situation="x")] * 5)
    llm = FakeLLM({"options": [opts, opts]})
    await get_options(llm, spec(category="silly"))
    await get_options(llm, spec(category=None, setting="a barn",
                                characters=[Character(name="Bob", role="Alice's cat")]))
    assert llm.calls[0][1] == "OPTIONS a silly, funny bedtime story|"
    assert llm.calls[1][1] == ("OPTIONS a bedtime story|Every option must use these, exactly as "
                               "given:\nCharacters: Bob (Alice's cat)\nSetting: a barn")


def test_options_path_has_no_hand_written_themes_or_premises():
    # The model proposes all 5 options; nothing human-written steers them.
    import re
    from pathlib import Path
    from string import Template as T
    import storyteller.options as options
    text = (Path(options.__file__).parent / "prompts" / "options.md").read_text()
    template = T(re.sub(r"<!--.*?-->", "", text, flags=re.S))
    assert set(template.get_identifiers()) == {"story_type", "keep"}
    assert "theme" not in template.template.lower()
