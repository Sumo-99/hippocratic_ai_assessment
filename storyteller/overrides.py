"""Overrides: the user's own ask can switch off a rubric dimension for their story. Safety never."""
from . import config
from .models import Evaluation, Override

# Phrased as what kind of user ask conflicts with each dimension, for the extract prompt.
OVERRIDABLE_DEFINITIONS: dict[str, str] = {
    "wind_down": "the story ends calm, safe and sleepy, with no cliffhanger, open question or "
                 "surprise at the end (conflicts with asks like 'end on a cliffhanger', "
                 "'to be continued', 'leave it hanging')",
    "faithfulness_named": "every character, place and detail the user named appears and is "
                          "kept as given (conflicts with asks to drop or swap a named element)",
    "consistency": "names, facts and the setting stay the same all the way through (conflicts "
                   "with asks for deliberate changes, transformations or unreliable details)",
    "age_language": "words and sentences suit a young child (conflicts with asks for fancier, "
                    "longer or more grown-up language)",
    "story_arc": "a clear beginning, a small problem and a gentle resolution (conflicts with "
                 "asks for a plotless, episodic or open-ended story)",
    "engagement": "the story holds a child's attention with fresh, vivid detail (conflicts "
                  "with asks for a deliberately slow, repetitive or minimal telling)",
    "faithfulness_premise": "the story delivers the premise the user gave (conflicts with "
                            "asks to twist or move away from that premise)",
    "category_checks": "the story follows the style rules of its category, such as cozy, "
                       "silly, adventure (conflicts with asks for a different tone or style)",
    "length": f"the story is {config.WORD_RANGE[0]} to {config.WORD_RANGE[1]} words (conflicts "
              "with asks for a much shorter or longer story)",
}
assert list(OVERRIDABLE_DEFINITIONS) == config.OVERRIDABLE_CHECKS, "definitions must match config.OVERRIDABLE_CHECKS"


def overridable_text() -> str:
    return "\n".join(f"- {k}: {v}" for k, v in OVERRIDABLE_DEFINITIONS.items())


def active(overrides: list[Override]) -> list[Override]:
    """The overrides that count: every one except safety (even a model_construct-ed one)."""
    return [o for o in overrides if o.dimension != "safety"]


def apply_overrides(ev: Evaluation, overrides: list[Override]) -> Evaluation:
    """Move failures the user asked for out of the blocking lists into `overridden`."""
    # DECISION: the coarse override stays as a backstop under the precise one: the judge is now
    # told each exception (judge._rubric_context), and the guard still ignores an overridden
    # dimension's failure if the judge fails it anyway.
    # "safety" is dropped here even if a model_construct-ed override names it.
    overridden = {o.dimension for o in active(overrides)}
    if not overridden:
        return ev
    hard = [d for d in ev.hard_failures if d not in overridden]
    soft = [d for d in ev.soft_failures if d not in overridden]
    removed = [d for d in ev.hard_failures + ev.soft_failures if d in overridden]
    return ev.model_copy(update={"hard_failures": hard, "soft_failures": soft,
                                 "overridden": removed})
