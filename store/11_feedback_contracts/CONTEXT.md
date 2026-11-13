---
stage: 11_feedback_contracts
model: orchestrator
plan_section: "Task 0: Shared contracts (orchestrator)"
parallel_with: []
---

# 11_feedback_contracts: fix the feedback feature's shared types

One job: add the shared types and fields for post-story feedback, so Tasks 1–3 can build in parallel against fixed names.

Branch: `user_feedback_feature` (from `skeleton`).

## Requirements (the source handoff, condensed; every 1N_feedback_* stage is held to these)
After a story is delivered, the user can quit or give free-form feedback ("make the dragon funnier", "end on a cliffhanger", "her name's actually Mia"). Feedback triggers one more pass of the existing revise → judge → guard loop. The new story comes back, and the user can give more feedback or quit. The feedback loop is an outer loop around the existing machinery.

R1. Reuse, don't rebuild: the input gate, the storyteller-revise call and the rubric judge are unchanged.
R2. Extraction gains (a) a user-preference block (plain instructions) and (b) `overrides: [{dimension, allow}]`: the rubric dimensions the user's ask conflicts with, plus the scoped exception. The extraction call is given the waivable dimensions and their definitions, so it can detect conflicts semantically ("cliffhanger", "to be continued", "leave it hanging" → `wind_down`).
R3. The `dimension` enum excludes `safety`. Safety is unrepresentable, not just forbidden.
R4. The guard (code) consults overrides. A waived non-safety failure is non-blocking: it isn't fed to revision and doesn't block output. Everything else is judged and enforced as normal. v1 uses the coarse form (the whole dimension is ignored at the guard, and the judge prompt stays static). The precise form (scoping the exception inside the judge prompt) is noted as a later upgrade.
R5. The preference block sits on top of the prompt stack and supersedes base/characters/setting/category when they conflict.
R6. The full rubric runs on every feedback revision.
R7. Safety is checked on the feedback request (gate) and on the generated draft (judge). A safety failure on output → canned message, never shown.
R8. `wind_down` stays a hard check. It is overridable, not demoted.
R9. Revisions start from the kept draft (Option A). Internal MAX_ROUNDS behaviour is unchanged (at the cap with a non-safety hard failure → best available; failing safety → canned).
R10. The same extraction path handles the ask whether it comes up front or as post-story feedback. No special case for feedback.
R11 (author). Thorough tests of the whole flow: initial prompt → draft → feedback (for example, "make the dragon funnier") → revised story → more feedback / quit.

## Inputs
- Plan: `../../docs/plans/2026-11-13-user-feedback.md` → "Global constraints", "Shared interfaces", "Task 0".
- Code: `../../storyteller/models.py`, `../../storyteller/config.py`, and the tests that build `Extraction(...)`.

## Process
1. Add the types and fields exactly as in the plan's "Shared interfaces".
2. Add `preferences=None, overrides=[]` to the tests' `Extraction(...)` helpers (they pass every field by keyword).

## Outputs
- `storyteller/models.py`, `storyteller/config.py` (uncommitted). `HANDOFF.md`.

## Done when
`.venv/bin/python -m pytest -q` → 98 passed.

## Review check
`"safety"` is absent from `Waivable`, and `config.HARD` is unchanged.
