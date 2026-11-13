"""All tunable constants in one place. The numeric knobs below can be overridden by an env var
of the same name, in the shell or in .env."""
import os

from dotenv import load_dotenv

# Load .env BEFORE reading any env var below, so knobs set in .env actually take effect.
load_dotenv()

# DECISION: endpoint and model are fixed, not env-overridable. A stray shell variable such as
# BASE_URL must never redirect the API key and prompts to another host, or swap the model.
BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "anthropic/claude-haiku-5.5"  # used for EVERY call

MAX_ROUNDS = int(os.getenv("MAX_ROUNDS", 3))          # max revisions of the story
TARGET_WORDS = int(os.getenv("TARGET_WORDS", 600))    # prompt says "about 500-700 words"
WORD_RANGE = (400, 900)                               # what the code check accepts
MAX_TOKENS = int(os.getenv("MAX_TOKENS", 2000))       # per call
MAX_RUN_COST_USD = float(os.getenv("MAX_RUN_COST_USD", 0.10))  # budget guard per run
# OpenRouter list price for anthropic/claude-haiku-5.5 (checked 2026-11-11), used only as a
# fallback cost estimate when a response has no usage.cost.
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
