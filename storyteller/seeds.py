"""Story seeds for vague requests ("tell me a story"): one calm starting situation, picked in code.

Without a seed, every vague request produced the same default story (a warm drink, goodnights
to objects, stars and the moon). A random seed varies the starting point; the writer still
invents the characters and details. None of the seeds involve a warm drink or saying
goodnight to objects."""
import random

SEEDS = [
    "a child and a grandparent sorting a big jar of buttons by colour on a rainy afternoon",
    "a badger repainting the sign above its burrow door before the autumn fair",
    "a snail who carries letters, finishing the slowest, last delivery of the day",
    "two friends building a blanket fort in the living room while snow falls outside",
    "a young gardener watering seedlings in window boxes high above a busy city",
    "a sea otter teaching its little cousin to float in a calm kelp bay",
    "a baker's apprentice shaping the last loaves of bread for tomorrow morning",
    "a child riding a slow night train, watching small towns pass by the window",
    "a family of field mice bringing in their seed harvest before the rain",
    "an owl librarian putting returned books back on the right shelves",
    "a little elephant practising the softest possible sound with its trunk",
    "a child knitting a scarf, one row at a time, for a friend who lives far away",
]


def pick_seed(request: str, rng_seed: str | None = None) -> tuple[int, str]:
    """Return (index, seed). With rng_seed set (config.STORY_SEED, for eval runs) the pick is
    reproducible: the same rng_seed and request always give the same seed, while different
    requests still get independent picks. Without it, the pick is random each run."""
    # DECISION: seed the RNG with rng_seed + request, not rng_seed alone, so a fixed eval seed
    # doesn't give every vague request in a batch the same seed.
    rng = random.Random(f"{rng_seed}:{request}") if rng_seed is not None else random.Random()
    i = rng.randrange(len(SEEDS))
    return i, SEEDS[i]
