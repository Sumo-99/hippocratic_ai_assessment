"""Generate five model-made story ideas for premise-free requests and select one at random."""
import random

from . import prompts
from .models import StoryOption, StoryOptions, StorySpec, describe_characters

# What the options prompt asks for, per category ("Give 5 distinct options for <this> ...").
STORY_TYPES = {
    None: "a bedtime story",
    "cozy": "a calm, cozy bedtime story",
    "adventure": "a gentle bedtime adventure where the hero reaches one small goal",
    "silly": "a silly, funny bedtime story",
    "comfort": "a comforting bedtime story",
}


def _keep(spec: StorySpec) -> str:
    """The lines every idea must keep: what the parent named."""
    lines = [f"{label}: {value}" for label, value in (
        ("Characters", describe_characters(spec.characters)), ("Setting", spec.setting)) if value]
    if not lines:
        return ""
    return "Every option must use these, exactly as given:\n" + "\n".join(lines)


async def get_options(llm, spec: StorySpec) -> list[StoryOption]:
    system = prompts.load("options").substitute(story_type=STORY_TYPES[spec.category],
                                                keep=_keep(spec))
    result = await llm.structured(system, "Please give the 5 options.", StoryOptions,
                                  stage="options")
    return result.options


def pick(options: list[StoryOption], seed: int | None, request: str) -> int:
    """Index of the chosen option. With a fixed seed (config.OPTIONS_SEED) the pick repeats per
    request; the request is mixed in so different requests don't all draw the same index."""
    rng = random.Random(f"{seed}:{request}:option") if seed is not None else random.Random()
    return rng.randrange(len(options))
