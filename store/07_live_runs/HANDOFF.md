---
stage: 07_live_runs
status: done
model: haiku
completed: 2026-11-12
live_api_cost_usd: 0.0221
reviewer_verdict: approved
---

# 07_live_runs: handoff

## Built
- `runs/samples/vague.json`: trace for "tell me a story"
- `runs/samples/named_characters.json`: trace for "a story about Alice and her cat Bob"
- `runs/samples/worry.json`: trace for "my son is scared of the dark"

Each trace contains `branch`, `calls`, `drafts`, `extraction`, `final`, `gate`, `premises`, `selection`, `timings`, `usage`, `total_cost_usd`.

## Results
| request | branch | drafts | revision rounds per draft | final hard/soft failures | total seconds (budget 60) | total cost USD |
|---|---|---|---|---|---|---|
| "tell me a story" (vague) | breadth | 3 (cozy, adventure, silly) | 0 / 1 / 0 | none / none | 33.55 | 0.0090 |
| "a story about Alice and her cat Bob" (named_characters) | breadth | 3 (cozy, adventure, silly) | 0 / 0 / 0 | none / none | 21.20 | 0.0067 |
| "my son is scared of the dark" (worry) | breadth | 3 (comfort x3) | 0 / 0 / 0 | none / none | 20.89 | 0.0064 |

Total live API cost: $0.0221 (trace sum $0.022117). Budget $0.10 for this stage was not exceeded. All three runs status `story`.

First two sentences of each final story:
- vague: "The Owl Who Counted Stars" opens with "High in an old oak tree, at the edge of a quiet orchard, lived a little owl named Mabel. Evening came softly."
- named_characters: "The Cocoa Night" opens with "Alice and Bob lived in a small cottage at the edge of the woods. Every night, they had a special routine."
- worry: "Milo and the Brave Bedtime" opens with "Milo lived in a small blue house with a big yellow door. His bedroom had a window, a bookshelf, and a bed with a green blanket."

## Decisions
- No `.gitignore` change. `git check-ignore runs/samples/vague.json` printed nothing (exit 1, not ignored), so `runs/*` and `!runs/samples/` already allow the samples.

## Verification
- `.venv/bin/python main.py --verbose "tell me a story"` → ran, exit 0, cost $0.0090
- `.venv/bin/python main.py --verbose "a story about Alice and her cat Bob"` → ran, exit 0, cost $0.0067
- `.venv/bin/python main.py --verbose "my son is scared of the dark"` → ran, exit 0, cost $0.0064
- `git check-ignore runs/samples/vague.json` → no output (not ignored)
- `grep -rl "sk-or" runs/samples` → no output (clean)

## Open issues / for the human reviewer
- Each request ran once; no retries, no extra requests, no code edits. `.env` was not opened.
- The three runs used the breadth branch. The depth branch has no live sample here.
- Only one draft (adventure, tell-me-a-story run) needed a revision round. The other drafts passed on first generation.

## Files touched (uncommitted)
- New: `runs/samples/vague.json`, `runs/samples/named_characters.json`, `runs/samples/worry.json`, `store/07_live_runs/HANDOFF.md`
- New (gitignored, not committed): `runs/20261112T050430251194Z-tell-me-a-story.json`, `runs/20261112T050454506315Z-a-story-about-alice-and-her-cat-bob.json`, `runs/20261112T050518284934Z-my-son-is-scared-of-the-dark.json`

## Orchestrator review (2026-11-12)
- Approved. Verified from traces: all required keys present; usage.cost returned on every call (fallback estimate never used); 21-34s per run. Flags for human review: (1) judge looks lenient, 8 of 9 drafts passed every check on the first try, so judge strictness is the first thing to probe in evals; (2) worry request extracted 'my son' as a named character, so faithfulness_named was judged against a non-name (story used 'Milo').
