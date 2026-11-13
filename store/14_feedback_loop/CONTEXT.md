---
stage: 14_feedback_loop
model: opus
plan_section: "Task 3: Outer feedback loop, CLI, end-to-end tests (opus)"
parallel_with: [12_feedback_overrides, 13_feedback_prompts]
---

# 14_feedback_loop: the outer feedback loop

One job: wrap the pipeline in a feedback loop (`run` returns a session, `give_feedback(session, text)` runs one more turn through the same path), wire it into the CLI, and test the whole flow end to end with FakeLLM.

## Inputs
- Plan: `../../docs/plans/2026-11-13-user-feedback.md` → "Global constraints", "Shared interfaces", "Review focus", "Task 3".
- Handoff: `../11_feedback_contracts/HANDOFF.md`. Requirements: `../11_feedback_contracts/CONTEXT.md` → "Requirements" (all of R1–R11 meet here).
- Code it may read: `../../storyteller/*.py`, `../../main.py`, `../../tests/test_pipeline.py` (copy its FakeLLM tag-word style).

Do NOT load: other 1N stage folders, prompt .md files, `runs/`, `docs/findings/`.

## Files you own (touch nothing else; other agents are editing other files at the same time)
- modify `storyteller/pipeline.py`, `main.py`
- create `tests/test_feedback_flow.py`, `tests/test_cli.py`
- `tests/test_pipeline.py` only if an existing test must change because of a deliberate interface change (record why).

## Parallel-work note
Tasks 1 (`overrides.apply_overrides`, `extract.normalize(e, text)`) and 2 (`make_spec` copying `preferences`/`overrides`, the preference block in `build_system_prompt`) are being built at the same time. Code against the plan's Shared interfaces. If `storyteller/overrides.py` doesn't exist yet when you start, don't create it. Your tests may go red on imports until it lands. Write your code, then re-run. If after finishing they still can't pass because a sibling file is missing, stop and report which interface you were waiting on.

## Process
TDD through the plan's Task 3 checkboxes. Keep every existing test in `tests/test_pipeline.py` passing: a request-only run must send the model exactly what it sends today. Mark judgment calls `# DECISION:`. No live API calls. Do not `git add` or commit.

## Outputs
Those files (uncommitted) + `HANDOFF.md` from `../_templates/HANDOFF.md` (include the new trace keys). Append one line to `../LOG.md`.

## Done when
`.venv/bin/python -m pytest -q` → all pass (once Tasks 1 and 2 have landed).

## Review check
A feedback turn calls `gate, extract, revise, judge` (never `generate` or `options`). The guard never discards the feedback revision in favour of the old story. Safety failure → canned message, with the session still holding the last good story.
