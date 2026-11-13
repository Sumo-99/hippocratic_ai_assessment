"""All tunable constants in one place. The numeric knobs below can be overridden by an env var
of the same name, in the shell or in .env."""
import os

from dotenv import load_dotenv

# Load .env BEFORE reading any env var below, so knobs set in .env actually take effect.
load_dotenv()

# DECISION: endpoint and model are fixed, not env-overridable. A stray shell variable (for
# example ANTHROPIC_BASE_URL, which the anthropic SDK would otherwise honour) must never
# redirect the API key and prompts to another host, or swap the model.
BASE_URL = "https://api.anthropic.com"
MODEL = "claude-haiku-5-5"  # used for EVERY call
# No hidden (billed) thinking tokens. Haiku 5.5 accepts "disabled" at its default effort;
# Opus 5.5 and Sonnet 5.5 reject it, so change this together with MODEL.
THINKING = {"type": "disabled"}

MAX_ROUNDS = int(os.getenv("MAX_ROUNDS", 3))          # max revisions of the story
TARGET_WORDS = int(os.getenv("TARGET_WORDS", 600))    # prompt says "about 500-700 words"
WORD_RANGE = (400, 900)                               # what the code check accepts
MAX_TOKENS = int(os.getenv("MAX_TOKENS", 2000))       # per call
MAX_RUN_COST_USD = float(os.getenv("MAX_RUN_COST_USD", 0.10))  # budget guard per run
# Anthropic list price for claude-haiku-5-5, prompts up to 100K tokens (checked 2026-11-13).
# The API returns token counts but no dollar cost, so these are the ONLY cost source: change
# them with MODEL or the budget guard reads wrong.
PRICE_IN_PER_TOKEN = 0.10 / 1_000_000
PRICE_OUT_PER_TOKEN = 0.50 / 1_000_000
LATENCY_BUDGET_S = int(os.getenv("LATENCY_BUDGET_S", 60))
RETRIES = int(os.getenv("RETRIES", 3))

# Requests with no premise get a random pick from 5 model-made ideas (storyteller/options.py).
# Set OPTIONS_SEED to make the pick repeatable per request, e.g. for eval runs.
OPTIONS_SEED = int(os.environ["OPTIONS_SEED"]) if os.getenv("OPTIONS_SEED") else None
RUNS_DIR = os.getenv("RUNS_DIR", "runs")

# Judge dimensions. HARD failures block a story; SOFT ones only trigger revision.
HARD = ["safety", "wind_down", "faithfulness_named", "consistency"]
SOFT = ["age_language", "story_arc", "engagement", "faithfulness_premise",
        "category_checks", "length"]
# Dimensions a user's own ask may override for their story (storyteller/overrides.py). Safety is
# never overridable; models.OverridableCheck mirrors this list so a model cannot even name safety.
OVERRIDABLE_CHECKS = [d for d in HARD + SOFT if d != "safety"]
