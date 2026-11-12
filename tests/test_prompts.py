"""Every prompt template fills in with exactly the placeholders the pipeline passes."""
import pytest

from storyteller.prompts import load

CATEGORIES = ["adventure", "silly", "comfort", "gentle_lesson", "cozy"]

KEYS = {
    "base": {"target_words": "600"},
    "gate": {},
    "extract": {},
    "judge": {"rubric_context": "Named characters: Milo", "category_checks": "- a check"},
    "revise": {},
    "baseline": {},
    **{c: {} for c in CATEGORIES},
}


@pytest.mark.parametrize("name", sorted(KEYS))
def test_all_templates_substitute(name):
    template = load(name)
    assert set(template.get_identifiers()) == set(KEYS[name])
    assert template.is_valid()
    template.substitute(**KEYS[name])


def test_baseline_is_empty():
    assert load("baseline").template.strip() == ""


@pytest.mark.parametrize("name", CATEGORIES)
def test_category_files_have_three_sections(name):
    text = load(name).template
    for heading in ("## Structure", "## Do / Don't", "## Judge checks"):
        assert heading in text


def test_comfort_never_dismisses_the_worry():
    assert "nothing to be scared of" not in load("comfort").template.lower()


def test_extract_does_not_treat_family_words_as_names():
    # Guards the rule added after the live "my son is scared of the dark" run, where
    # "my son" was extracted as a named character.
    text = load("extract").template
    assert '"my son is scared of the dark" → characters: []' in text
    assert '"my little brother Sam" → characters: ["Sam"]' in text


def test_judge_names_every_dimension():
    text = load("judge").template
    for field in ["safety", "wind_down", "faithfulness_named", "consistency", "age_language",
                  "story_arc", "engagement", "faithfulness_premise", "category_checks"]:
        assert field in text
    assert "revis" not in text.lower()


def test_base_states_target_length():
    filled = load("base").substitute(target_words="600")
    assert "500–700 words" in filled and "600" in filled
