---
stage: 13_feedback_prompts
model: opus
plan_section: "Task 2: Prompts and the prompt stack (opus)"
parallel_with: [12_feedback_overrides, 14_feedback_loop]
---

# 13_feedback_prompts: extraction prompt and preference block

One job: teach the extraction prompt about follow-up feedback, `preferences` and `overrides`, and put the preference block on top of the writer's prompt stack.

## Inputs
- Plan: `../../docs/plans/2026-11-13-user-feedback.md` → "Global constraints", "Shared interfaces", "Review focus", "Task 2".
- Handoff: `../11_feedback_contracts/HANDOFF.md`. Requirements: `../11_feedback_contracts/CONTEXT.md` → "Requirements" (R2, R3, R5, R10 matter most here).
- Code it may read: `../../storyteller/models.py`, `generate.py`, `prompts/__init__.py`, `prompts/extract.md`, `prompts/base.md`, `prompts/judge.md` (for the dimension meanings), `../../tests/test_prompts.py`, `../../tests/test_stages.py`.

Do NOT load: other 1N stage folders, `pipeline.py`, `extract.py`, `overrides.py`, `runs/`, `docs/findings/`.

## Files you own (touch nothing else; other agents are editing other files at the same time)
- modify `storyteller/prompts/extract.md`, `storyteller/generate.py`
- modify `tests/test_prompts.py`, `tests/test_stages.py`

## Process
TDD through the plan's Task 2 checkboxes. The extract prompt must contain the literal placeholder `$waivable_dimensions` (Task 1 substitutes it), so make sure no other stray `$` appears. Keep the existing prompt tests green (especially "no concrete story examples"). Mark judgment calls `# DECISION:`. No live API calls. Do not `git add` or commit.

## Outputs
Those files (uncommitted) + `HANDOFF.md` from `../_templates/HANDOFF.md`. Append one line to `../LOG.md`.

## Done when
`.venv/bin/python -m pytest -q tests/test_prompts.py tests/test_stages.py` passes. If a test in those files fails only because Task 1's `extract.py` hasn't landed yet, say so in the handoff.

## Review check
The preference block comes first in the system prompt and says it never overrides the Safety rules. With no preferences, the prompt is byte-identical to before.
