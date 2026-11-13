---
stage: 12_feedback_overrides
model: sonnet
plan_section: "Task 1: Overrides and extraction code (sonnet)"
parallel_with: [13_feedback_prompts, 14_feedback_loop]
---

# 12_feedback_overrides: waivers applied in code

One job: write `apply_overrides` (the guard's waiver step), the waivable-dimension definitions for the extract prompt, and the extraction code changes (substitute definitions, drop overrides whose quote isn't in the text).

## Inputs
- Plan: `../../docs/plans/2026-11-13-user-feedback.md` → "Global constraints", "Shared interfaces", "Review focus", "Task 1".
- Handoff: `../11_feedback_contracts/HANDOFF.md` (its Requirements list is in `../11_feedback_contracts/CONTEXT.md` → "Requirements").
- Code it may read: `../../storyteller/models.py`, `config.py`, `extract.py`, `judge.py` (signatures only), `fake.py`, `../../tests/test_stages.py` (style).

Do NOT load: other 1N stage folders, `pipeline.py`, `generate.py`, prompt .md files, `runs/`, `docs/findings/`.

## Files you own (touch nothing else; other agents are editing other files in this checkout at the same time)
- create `storyteller/overrides.py`
- modify `storyteller/extract.py`
- create `tests/test_overrides.py`

## Process
TDD through the plan's Task 1 checkboxes. Mark judgment calls `# DECISION:`. No live API calls. Do not `git add` or commit.

## Outputs
Those files (uncommitted) + `HANDOFF.md` from `../_templates/HANDOFF.md`. Append one line to `../LOG.md`.

## Done when
`.venv/bin/python -m pytest -q tests/test_overrides.py` passes. Failures elsewhere in the suite caused by other in-flight tasks are expected: list them in the handoff, don't fix them.

## Review check
`apply_overrides` can never remove `"safety"`, even given a `model_construct`-ed override.
