---
stage: 12_feedback_overrides
status: done
model: sonnet
completed: 2026-11-13
live_api_cost_usd: 0.00
reviewer_verdict: n/a
---

# 12_feedback_overrides: handoff

## Built
- `storyteller/overrides.py`: `WAIVABLE_DEFINITIONS` (asserted == `config.WAIVABLE` at import), `waivable_text()`, `apply_overrides(ev, overrides)`.
- `storyteller/extract.py`: `extract(llm, text)` substitutes `waivable_dimensions`, calls `normalize(result, text)`; `normalize(e, text="")` drops overrides whose quote (case/whitespace-insensitive, non-empty) is not in `text`.
- `tests/test_overrides.py`: 12 tests per plan Task 1.

## Interfaces as built
none (extract's second param renamed `request` -> `text`, positional use unaffected).

## Decisions
- `overrides.py` apply_overrides: coarse form, whole dimension waived at the guard; judge prompt static.
- `extract.py` normalize: code-side quote check against the conversation text.
- `apply_overrides` returns the input unchanged when nothing is waived; `"safety"` is subtracted from the waived set even for `model_construct`-ed overrides.

## Verification
- `.venv/bin/python -m pytest -q tests/test_overrides.py tests/test_stages.py` -> 30 passed.

## Open issues / for the human reviewer
- `normalize(e)` with no text drops ALL overrides (per plan). Callers must pass the conversation text.
- `prompts/extract.md` needs `$waivable_dimensions` (Task 2); harmless until then.

## Files touched (uncommitted)
- `storyteller/overrides.py`, `storyteller/extract.py`, `tests/test_overrides.py`
