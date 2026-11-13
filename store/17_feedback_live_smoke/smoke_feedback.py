"""Live smoke test of the feedback loop: 1 request + 2 feedback turns (author-approved, ~$0.02).
Run from the repo root: .venv/bin/python <this file>"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.getcwd())
from storyteller import pipeline  # noqa: E402

REQUEST = "A story about a girl named Lily and her friend, a clumsy dragon"
FEEDBACK = ["make the dragon funnier", "end on a cliffhanger"]
OUT = os.path.join(os.path.dirname(__file__), "smoke_stories.md")


def summarize(label, result):
    with open(result.trace_path) as f:
        t = json.load(f)
    ex = t.get("extraction", {})
    print(f"\n=== {label}: status={result.status} cost=${t['total_cost_usd']:.4f} "
          f"time={t['timings']['total']:.1f}s calls={t['usage']['calls']}")
    print(f"gate: safety={t['gate']['safety']['passed']} relevance={t['gate']['relevance']['passed']}")
    print(f"extraction: category={ex.get('category')} chars={[c['name'] or c['role'] for c in ex.get('characters', [])]}")
    print(f"  preferences={ex.get('preferences')!r}")
    print(f"  overrides={ex.get('overrides')}")
    for v in t.get("versions", []):
        e = v["evaluation"]
        print(f"  round {v['round']}: hard={e['hard_failures']} soft={e['soft_failures']} "
              f"waived={e.get('waived', [])} words={e['word_count']}")
    print(f"final: {t['final']}")
    return t["total_cost_usd"]


async def main():
    total = 0.0
    stories = []
    result = await pipeline.run(REQUEST)
    total += summarize("turn 0", result)
    stories.append(("turn 0", REQUEST, result.story or result.message))
    session = result.session
    for i, fb in enumerate(FEEDBACK, 1):
        if session is None:
            print("no session; stopping")
            break
        result = await pipeline.give_feedback(session, fb)
        total += summarize(f"turn {i} ({fb!r})", result)
        stories.append((f"turn {i}", fb, result.story or result.message))
        session = result.session or session
    with open(OUT, "w") as f:
        for label, ask, text in stories:
            f.write(f"# {label}: {ask}\n\n{text}\n\n")
    print(f"\nTOTAL COST: ${total:.4f}\nstories: {OUT}")


asyncio.run(main())
