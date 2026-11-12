---
stage: 07_live_runs
model: haiku
plan_section: "Task 7: Live sample runs (haiku), in parallel with T6"
parallel_with: [06_docs]
---

# 07_live_runs: three real runs, nothing more

One job: run exactly 3 live requests, save their traces as samples, and report what happened and what it cost. **This is the only stage allowed to spend real money. The user has $10 total.**

## Inputs
- `../05_pipeline/HANDOFF.md` (what the trace contains)
- `../../.gitignore`

Do NOT load: any source code, prompts, plans, or other stages. Do NOT open, print, cat or echo `.env`; the code reads the key itself.

## Process
Run these **one at a time**, in this order, from the repo root. **Each command runs exactly once.**
1. `.venv/bin/python main.py --verbose "tell me a story"`
2. `.venv/bin/python main.py --verbose "a story about Alice and her cat Bob"`
3. `.venv/bin/python main.py --verbose "my son is scared of the dark"`

Hard rules:
- **If any command fails (traceback or non-zero exit), STOP immediately.** Don't run the remaining requests and don't retry. Report the full error and the trace path if one was written.
- If a run's verbose total cost is above $0.10, stop and report it.
- Never re-run a request, never run extra requests, never run `pytest` with live calls, never edit code.

After the runs:
4. `mkdir -p runs/samples` and copy the 3 newest `runs/*.json` there, naming them `vague.json`, `named_characters.json`, `worry.json`.
5. Check `.gitignore` allows `runs/samples/`: `git check-ignore runs/samples/vague.json` should print nothing. If it is ignored, change the rule to `runs/*` plus `!runs/samples/`, and say so.
6. Secret scan: `grep -rl "sk-or" runs/samples` must print nothing.
7. Do not `git add` or `git commit`.

## Outputs
- `runs/samples/{vague,named_characters,worry}.json`
- `HANDOFF.md` here, from `../_templates/HANDOFF.md`, with a table: request | branch | drafts | revision rounds per draft | final hard/soft failures | total seconds (budget 60) | total cost USD. Set `live_api_cost_usd` to the sum. Paste each final story's first 2 sentences only.

## Done when
3 sample traces exist, the secret scan is clean, and the HANDOFF has the table.

## Review check
The cost sum is ≤ $0.10. Each trace has gate, extraction, branch, drafts, final, timings and usage.
