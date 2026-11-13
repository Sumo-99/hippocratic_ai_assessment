---
stage: 16_feedback_review
model: opus
plan_section: "Task 5: Whole-branch review (orchestrator + opus reviewer)"
parallel_with: [15_feedback_docs]
---

# 16_feedback_review: whole-branch check against R1–R11

One job: read-only review of the feedback feature's uncommitted diff on `user_feedback_feature` against the requirements, and report gaps.

## Inputs
- Requirements: `../11_feedback_contracts/CONTEXT.md` → "Requirements".
- Handoffs: `../11_feedback_contracts/` through `../14_feedback_loop/HANDOFF.md`.
- The diff: `git diff` plus the new files (`storyteller/overrides.py`, `tests/test_overrides.py`, `tests/test_feedback_flow.py`, `tests/test_cli.py`).

Do NOT load: `runs/`, `docs/findings/`, older stage folders.

## Process
1. Run `.venv/bin/python -m pytest -q`.
2. For each of R1–R11: point to the code and the test that pins it, or report it as a gap.
3. Look for correctness bugs in the new code paths (session threading, waived lists, trace keys, CLI loop).

## Outputs
`HANDOFF.md` with a findings table (severity, file:line, fix). No code edits: the orchestrator applies the fixes.

## Done when
Every requirement has a verdict.
