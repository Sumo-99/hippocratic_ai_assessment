---
stage: 04_evaluation
status: done
model: sonnet
completed: 2026-11-11
live_api_cost_usd: 0.00
reviewer_verdict: approved
---

# 04_evaluation: handoff

## Built
- `storyteller/judge.py`: `word_count`, `length_ok`, `skipped_dimensions`, `evaluate` (judge call + failure lists computed in code).
- `storyteller/feedback.py`: `build_feedback` (hard failures only if any, else soft; length bullet states count and range).
- `storyteller/compare.py`: `compare_once`, `compare_both_orders`, `keep_better`.
- `tests/test_evaluation.py`: 11 tests, prompts monkeypatched with stub Templates.

## Interfaces as built
None: signatures match the plan. `keep_better` trace dict is `{rule, result, kept_round}` with `rule` = `"hard_checks"` or `"pairwise:x|y|tie"`, `result` = `"new"`/`"prev"`.

## Prompt contract (for stage 02/05)
- `judge` is substituted with `rubric_context` and `category_checks`; the user message is `STORY:\n<story>`.
- `category_checks` is the body of the `## Judge checks` section of `prompts/<category>.md` (whole file if the heading is missing).
- `compare` is substituted with no keys; user message is `STORY A:\n...\n\nSTORY B:\n...`.
- The rubric_context tells the judge which dimensions are skipped (evidence "N/A", passed true), but code ignores them regardless.

## Decisions
- `judge.py` `evaluate`: failures recomputed from each `passed` flag, skips dropped in code.
- `compare.py` `compare_both_orders`: two swapped-order calls, only agreement counts.
- `compare.py` `keep_better`: ties keep prev. Fewer hard failures wins without a call (equals more hard checks passed, since skipped ones are never failures).

## Verification
- `.venv/bin/python -m pytest tests/test_evaluation.py -v` → `11 passed`

## Open issues / for the human reviewer
- `evaluate` category_checks parsing depends on stage 02 using the exact heading `## Judge checks`.
- Soft-failure order: judge dimensions in `config.SOFT` order, then `length` last.

## Files touched (uncommitted)
- New: `storyteller/{judge,feedback,compare}.py`, `tests/test_evaluation.py`, `store/04_evaluation/HANDOFF.md`

## Orchestrator review (2026-11-11)
- Approved. Verified `_rubric_context` names skipped dimensions explicitly ('evidence N/A, passed true'), matching judge.md; `## Judge checks` heading matches all 5 category files.
