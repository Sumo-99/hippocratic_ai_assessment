"""Story generation: the spec, system prompt assembly, first draft and revision."""
from . import config, prompts
from .models import Extraction, StorySpec, describe_characters

# EXPERIMENT condition A: added only when the request names no characters, setting or premise.
INVENT_INSTRUCTION = (
    "The request gives no characters, setting or premise. Invent your own: choose characters, "
    "a setting and a small situation for this story yourself. Make them specific and fresh "
    "rather than the most obvious choice.")


def names_nothing(spec: StorySpec) -> bool:
    return not (spec.characters or spec.setting or spec.premise)


def make_spec(e: Extraction) -> StorySpec:
    """The extraction becomes the story's variables.

    DECISION: the cozy fallback is only for requests that name nothing (no characters, setting
    or premise). Cozy is a low-plot bundle that needs nothing from the request; given a subject
    it turned camping or a penguin in Tokyo into a bedtime routine. If something is named but
    the category is unclear, the category stays None and the base prompt works alone."""
    category = e.category
    if category is None and not (e.characters or e.setting or e.premise):
        category = config.FALLBACK_CATEGORY
    return StorySpec(category=category, characters=e.characters,
                     setting=e.setting, premise=e.premise, worry=e.worry,
                     listener=e.listener)


def build_system_prompt(spec: StorySpec) -> str:
    """Base prompt + category bundle + one line per variable that is actually present."""
    parts = [prompts.load("base").substitute(target_words=config.TARGET_WORDS)]
    if spec.category:  # no category -> no bundle, the base prompt alone
        parts.append(prompts.load(spec.category).substitute())
    lines = []
    if spec.idea is not None:  # condition B: the picked option fills the empty variables
        lines += [f"Characters: {spec.idea.characters}", f"Setting: {spec.idea.setting}",
                  f"Premise: {spec.idea.situation}"]
    elif config.VAGUE_MODE == "invent" and names_nothing(spec):  # condition A
        lines.append(INVENT_INSTRUCTION)
    if spec.characters:
        lines.append("Characters: " + describe_characters(spec.characters))
    for label, value in (("Setting", spec.setting), ("Premise", spec.premise),
                         ("Worry", spec.worry), ("Listener", spec.listener)):
        if value:
            lines.append(f"{label}: {value}")
    if lines:
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


async def write_story(llm, spec: StorySpec) -> str:
    return await llm.text(build_system_prompt(spec), "Please write the story.", stage="generate")


async def revise_story(llm, spec: StorySpec, previous: str, feedback: str) -> str:
    system = build_system_prompt(spec) + "\n\n" + prompts.load("revise").substitute()
    user = f"Story:\n{previous}\n\nFeedback:\n{feedback}"
    return await llm.text(system, user, stage="revise")
