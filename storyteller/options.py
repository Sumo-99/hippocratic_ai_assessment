"""EXPERIMENT condition B: for a request that names nothing, ask the model for 5 distinct story
options, then code picks one at random. The full list and the pick go in the trace."""
import random

from . import config
from .models import StoryOption, StoryOptions

OPTIONS_PROMPT = (
    "Give 5 distinct options for a calm bedtime story for a child aged 5 to 10. Each option has "
    "characters, a setting and a small situation, one line each. Make all 5 different from "
    "each other.")


async def get_options(llm) -> list[StoryOption]:
    result = await llm.structured(OPTIONS_PROMPT, "Please give the 5 options.", StoryOptions,
                                  stage="options")
    return result.options


def pick(options: list[StoryOption], seed: int | None, request: str) -> int:
    """Index of the chosen option. With a fixed seed the pick is repeatable per request; the
    request is mixed in so that different requests don't all get the same index."""
    rng = random.Random(f"{seed}:{request}") if seed is not None else random.Random()
    return rng.randrange(len(options))
