"""Story options for vague requests: when the request names no characters, setting, premise or
worry, one extra call asks for 5 distinct story ideas of the request's category, and code picks
one at random. The writer gets the pick as Characters / Setting / Premise lines.

Tested as condition B in docs/findings/independent_thinking_experiement.md: with the writer
inventing its own idea, vague requests converged on one template; with a random pick from
model-made options, 10 requests gave 10 distinct premises. But the 5-option lists themselves
repeated across requests (Pip in 9 of 10 lists, a moonlit woodland animal as option 1 in all
10), so each call also gets one theme drawn at random from STEERS: code controls the space,
the model fills in the specifics."""
import random

from . import prompts
from .models import StoryOption, StoryOptions, StorySpec

# What the options prompt asks for, per category ("Give 5 distinct options for <this> ...").
STORY_TYPES = {
    "cozy": "a calm, cozy bedtime story",
    "adventure": "a gentle bedtime adventure where the hero reaches one small goal",
    "silly": "a silly, funny bedtime story",
    "gentle_lesson": "a bedtime story with a gentle lesson",
    "comfort": "a comforting bedtime story",
}


# One is drawn at random per vague request and given to the options call as its theme.
# DECISION: places and times only, no characters, so the model still invents who the story is
# about. Kept away from what the model already defaults to (moon, woodland, meadow, pond,
# lantern, garden, lighthouse, cottage), which is the palette these are meant to push off.
STEERS = (
    "a city rooftop", "the seaside", "a kitchen", "deep winter", "a workshop",
    "a train journey", "a bakery before dawn", "market day", "a rainy afternoon indoors",
    "a desert at dusk", "a houseboat on a canal", "a mountain hut", "a library",
    "a bus ride home", "a greenhouse", "a farm in spring", "a music room", "a post office",
    "a small island", "an orchard at harvest", "a museum after closing time",
    "a bicycle repair shop", "a school after everyone has gone home", "a fishing harbour",
    "a pottery studio", "a bridge over a busy river", "a hot-air balloon", "laundry day",
)


def is_vague(spec: StorySpec) -> bool:
    """Nothing to build a story from: no characters, setting, premise or worry.

    DECISION: a worry counts as something named. "my son is scared of the dark" is a comfort
    story about that fear; a random idea could ignore it, so the writer invents around it."""
    return not (spec.characters or spec.setting or spec.premise or spec.worry)


async def get_options(llm, category: str | None, steer: str) -> list[StoryOption]:
    story_type = STORY_TYPES.get(category or "cozy", STORY_TYPES["cozy"])
    system = prompts.load("options").substitute(story_type=story_type, steer=steer)
    result = await llm.structured(system, "Please give the 5 options.", StoryOptions,
                                  stage="options")
    return result.options


def _rng(seed: int | None, request: str, what: str) -> random.Random:
    """With a fixed seed (config.OPTIONS_SEED) each draw repeats per request; the request is
    mixed in so different requests don't all draw the same, and `what` keeps the steer draw
    and the option pick independent of each other."""
    return random.Random(f"{seed}:{request}:{what}") if seed is not None else random.Random()


def pick_steer(seed: int | None, request: str) -> str:
    return _rng(seed, request, "steer").choice(STEERS)


def pick(options: list[StoryOption], seed: int | None, request: str) -> int:
    """Index of the chosen option."""
    return _rng(seed, request, "option").randrange(len(options))
