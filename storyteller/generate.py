"""Story generation: the spec, system prompt assembly, first draft and revision."""
from . import config, prompts
from .models import Extraction, StorySpec, describe_characters


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
    if spec.characters:
        lines.append("Characters: " + describe_characters(spec.characters))
    for label, value in (("Setting", spec.setting), ("Premise", spec.premise),
                         ("Worry", spec.worry)):
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
