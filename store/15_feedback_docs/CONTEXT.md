---
stage: 15_feedback_docs
model: haiku
plan_section: "Task 4: Docs (haiku)"
parallel_with: [16_feedback_review]
---

# 15_feedback_docs: document the feedback loop

One job: update the design docs and README for post-story feedback, based on what was actually built.

## Inputs
- Plan: `../../docs/plans/2026-11-13-user-feedback.md` → "Task 4" only.
- Handoffs (the source of truth for what was built): `../12_feedback_overrides/HANDOFF.md`, `../13_feedback_prompts/HANDOFF.md`, `../14_feedback_loop/HANDOFF.md`.
- Files to edit: `../../docs/ARCHITECTURE.md`, `../../docs/OPEN_QUESTIONS.md`, `../../README.md`.

Do NOT load: code files, other stage folders, `runs/`, `docs/findings/`.

## Process
Follow Task 4's checkboxes. Match each doc's existing style and heading structure: add to it, don't restructure it. Keep diagrams in the same syntax they already use.

## Outputs
Those three docs (uncommitted) + `HANDOFF.md`. Append one line to `../LOG.md`.

## Done when
Every decision listed in the three handoffs appears in OPEN_QUESTIONS, and the ARCHITECTURE flow shows the feedback loop.

## Review check
No doc claims behaviour the handoffs don't describe.
