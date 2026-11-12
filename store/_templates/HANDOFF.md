---
stage: NN_name
status: done | blocked
model: sonnet | opus | haiku | orchestrator
completed: YYYY-MM-DD
live_api_cost_usd: 0.00
reviewer_verdict: approved | changes_requested | n/a
---

# NN_name: handoff

<!-- Keep under ~80 lines. Later stages read THIS instead of the code or the chat. -->

## Built
- `path/to/file.py`: one line on what it owns

## Interfaces as built
<!-- Exact signatures later stages depend on. List ONLY differences from the plan's
     "Shared Interfaces" / task Interfaces block. Write "none" if it matches exactly. -->

## Decisions
<!-- Every `# DECISION:` added in this stage: file:line, what was chosen, the alternative. -->

## Verification
- Command: `…` → result (e.g. `12 passed`)

## Open issues / for the human reviewer
<!-- Things that look fragile or that a person should eyeball in Wave 6. -->

## Files touched (uncommitted)
- …
