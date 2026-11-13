"""EXPERIMENT runner: the 10 vague requests from docs/findings/convergence_test.md, one pipeline
run each, under condition A (VAGUE_MODE=invent) or B (VAGUE_MODE=options).

    .venv/bin/python scripts/run_independent.py A
    .venv/bin/python scripts/run_independent.py B [--seed 20261113]

Traces go to runs/independent/<A|B>/, plus results.json (story text, cost, latency per run).
DOTENV_PATH points at the .env to load (the key is read, never printed)."""
import argparse
import asyncio
import json
import os
import sys
import time

from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# A worktree has no .env of its own; by default use the main checkout's, next to this one.
load_dotenv(os.getenv("DOTENV_PATH",
                      os.path.join(os.path.dirname(ROOT), "hippocratic_ai_assessment", ".env")))
sys.path.insert(0, ROOT)

from storyteller import config, pipeline  # noqa: E402

REQUESTS = [
    "tell me a bedtime story",
    "a bedtime story please",
    "can you tell me a story",
    "something nice for my son before bed",
    "a story for my 6 year old",
    "I need a bedtime story for my daughter",
    "a sleepy story for tonight",
    "any story is fine",
    "a story to help my kids fall asleep",
    "surprise me with a bedtime story",
]


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("condition", choices=["A", "B"])
    ap.add_argument("--seed", default=None, help="OPTIONS_SEED for condition B")
    args = ap.parse_args()

    config.VAGUE_MODE = "invent" if args.condition == "A" else "options"
    config.OPTIONS_SEED = args.seed
    config.RUNS_DIR = os.path.join(ROOT, "runs", "independent", args.condition)
    os.makedirs(config.RUNS_DIR, exist_ok=True)

    results = []
    for i, req in enumerate(REQUESTS):
        start = time.monotonic()
        r = await pipeline.run(req)
        secs = time.monotonic() - start
        with open(r.trace_path) as f:
            cost = json.load(f)["total_cost_usd"]
        results.append({"index": i, "request": req, "status": r.status, "story": r.story,
                        "message": r.message, "trace": os.path.basename(r.trace_path),
                        "seconds": round(secs, 1), "cost_usd": cost})
        print(f"{i} {r.status} {secs:.1f}s ${cost:.4f}", flush=True)
    with open(os.path.join(config.RUNS_DIR, "results.json"), "w") as f:
        json.dump(results, f, indent=2)
    print(f"total ${sum(x['cost_usd'] for x in results):.4f}")


if __name__ == "__main__":
    asyncio.run(main())
