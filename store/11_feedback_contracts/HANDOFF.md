---
stage: 11_feedback_contracts
status: done
model: orchestrator
completed: 2026-11-13
live_api_cost_usd: 0.00
reviewer_verdict: n/a
---

# 11_feedback_contracts: handoff

## Built
- `storyteller/config.py`: `WAIVABLE = [d for d in HARD + SOFT if d != "safety"]`. HARD/SOFT are unchanged.
- `storyteller/models.py`: `Waivable` Literal, `Override(quote, dimension, allow)`, `Extraction.preferences` / `.overrides`, `StorySpec.preferences` / `.overrides`, `Evaluation.waived`, `StorySession(request, feedback, spec, story)`, `PipelineResult.session`.

## Interfaces as built
- One difference from the plan: `Extraction.preferences` defaults to `None` and `Extraction.overrides` to `[]` in Python. `llm._strict_schema` still lists both as required in the JSON schema sent to the model (checked: `required` ends with `preferences, overrides`). So existing tests that build `Extraction(...)` needed no edits, and Task 0 touched no test file.
- The strict schema's `Override.dimension` enum = the 9 WAIVABLE names, no `safety` (checked).

## Decisions
- `Override` puts `quote` first (evidence-first convention), ahead of the handoff's `{dimension, allow}`. Task 1 uses it to drop over-eager waivers in code.

## Verification
- `.venv/bin/python -m pytest -q` → 98 passed.

## Files touched (uncommitted)
- `storyteller/config.py`, `storyteller/models.py`
