---
stage: 04_evaluation
model: sonnet
plan_section: "Task 4: Evaluation and comparison (sonnet)"
parallel_with: [02_prompts, 03_stages]
---

# 04_evaluation: judge, feedback, compare, keep-better

One job: build the rubric judge wrapper, length check, skip rules, feedback priority, two-order comparison and keep-better rule, tested offline.

## Inputs
- Plan: `../../docs/plans/2026-11-11-storyteller-skeleton.md`. Read only "Global Constraints", "Shared Interfaces", "Review Focus" items 3 and 5, "Task 4: Evaluation and comparison (sonnet)", and the `judge` / `compare` rows of the Task 2 placeholder table.
- Handoff: `../01_foundation/HANDOFF.md`. Its "Interfaces as built" overrides the plan.
- Code: `../../storyteller/{config,models,llm,fake}.py`, `../../storyteller/prompts/__init__.py`, `../../tests/conftest.py`

Do NOT load: other stage folders, `storyteller/prompts/*.md` (stage 02 is writing them), gate/extract/brainstorm/generate/pipeline.

## Process
1. TDD from the plan's Task 4 test list. **Monkeypatch `storyteller.prompts.load`** in tests with stub Templates; never depend on the real `.md` files.
2. Implement `storyteller/{judge,feedback,compare}.py` with the exact plan signatures. `HARD`/`SOFT` come from `config`. `WORD_RANGE` is `(400, 900)`.
3. `compare_both_orders` runs both orders concurrently with `asyncio.gather`. Disagreement means `"tie"`. In keep-better, a tie keeps the previous draft.
4. No live API calls. Do not `git add` or `git commit`. Don't edit shared files; describe any needed change in the HANDOFF.

## Outputs
- `storyteller/{judge,feedback,compare}.py`, `tests/test_evaluation.py` (uncommitted)
- `HANDOFF.md` here

## Done when
`.venv/bin/python -m pytest tests/test_evaluation.py -v` → all pass.

## Review check
Skipped dimensions are ignored even when the judge fails them. Feedback contains only hard failures whenever any hard check fails. Keep-better makes no comparison call when the hard pass counts differ. A `["A","A"]` comparison queue gives `"tie"`.
