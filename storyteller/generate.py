"""Story generation: specs, system prompt assembly, first draft and revision."""
from . import config, prompts
from .extract import breadth_categories
from .models import Extraction, Premise, StorySpec


def depth_spec(e: Extraction) -> StorySpec:
    return StorySpec(
        category=e.category or config.FALLBACK_CATEGORY, characters=e.characters,
        setting=e.setting, premise=e.premise, mood=e.mood, worry=e.worry,
        named_characters=bool(e.characters), named_setting=e.setting is not None)


def breadth_specs(e: Extraction, premises: list[Premise]) -> list[StorySpec]:
    cats = breadth_categories(e)
    return [StorySpec(
        category=cats[i] or config.FALLBACK_CATEGORY, characters=p.characters,
        setting=p.setting, premise=p.premise, mood=e.mood, worry=e.worry,
        # Only what the USER named counts for the hard faithfulness check, not what the
        # brainstorm invented for this premise.
        named_characters=bool(e.characters), named_setting=e.setting is not None)
        for i, p in enumerate(premises)]


def build_system_prompt(spec: StorySpec) -> str:
    """Base prompt + category bundle + one line per variable that is actually present."""
    parts = [
        prompts.load("base").substitute(target_words=config.TARGET_WORDS),
        prompts.load(spec.category).substitute(),
    ]
    lines = []
    if spec.characters:
        lines.append("Characters: " + ", ".join(spec.characters))
    for label, value in (("Setting", spec.setting), ("Premise", spec.premise),
                         ("Mood", spec.mood), ("Worry", spec.worry)):
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
