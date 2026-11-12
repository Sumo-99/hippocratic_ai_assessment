---
stage: 05_pipeline
model: opus
plan_section: "Task 5: Pipeline, selection, cap/fallback, CLI (opus)"
parallel_with: []
---

# 05_pipeline: orchestrate the full story flow

One job: wire the stages into `pipeline.run(request)` (gate → extract → depth/breadth → parallel draft loops → selection → safety fallback → trace), plus `baseline()` and the `main.py` CLI, all tested offline with FakeLLM.

## Inputs
- Plan: `../../docs/plans/2026-11-11-storyteller-skeleton.md`. Read only "Global Constraints", "API Budget (hard rule)", "Review Focus", "Shared Interfaces", "Task 5".
- Spec, for the exact rules: `../../docs/SPEC.md` "Architecture" §6–9 (revision loop, keep-better, selection, behavior at the cap).
- Handoffs (their "Interfaces as built" override the plan): `../01_foundation/HANDOFF.md`, `../02_prompts/HANDOFF.md`, `../03_stages/HANDOFF.md`, `../04_evaluation/HANDOFF.md`
- Code to import from (read the signatures; don't edit them unless a bug blocks you, and record any edit in the HANDOFF): `../../storyteller/*.py`
- The original `../../main.py`. Rewrite it, but keep its top docstring question about "what you would have built next" with the answer left **empty** for the author.

Do NOT load: other stage folders' CONTEXT files, `storyteller/prompts/*.md` content (it's tested already), `runs/`.

## Process
1. TDD from the plan's Task 5 test list, building depth first, then breadth, then cap/fallback. Use FakeLLM with callable replies keyed by stage.
2. Facts from the handoffs to respect:
   - `OpenRouterClient.total_cost` is per instance, so `run()` creates **one fresh client per run** when `llm` is None, wiring `on_usage=trace.on_usage`.
   - Routing helpers live in `extract.py`. Spec builders, `write_story` and `revise_story` live in `generate.py`.
   - `keep_better` returns `(kept, record)`.
   - Catch `BudgetExceeded` in `run()`: write the trace, then return a friendly message (`status="safety_fallback_message"` is wrong for this, so add a status `"error"` to `PipelineResult` and record the change in the HANDOFF as an interface change).
3. Record cost and tokens in the trace, plus a `total_cost_usd`. `--verbose` prints that total.
4. Add `# TODO(critique-check)`, `# TODO(user-feedback)` and `# TODO(safety-fallback)` hooks. Mark judgment calls `# DECISION:`.
5. **No live API calls.** No key exists yet. Do not `git add` or `git commit`.

## Outputs
- `storyteller/pipeline.py`, `tests/test_pipeline.py`, rewritten `main.py`, and an optional `models.py` edit for the `"error"` status (uncommitted)
- `HANDOFF.md` here, including a short "data flow" paragraph (request → PipelineResult + trace keys) for the human review phase.

## Done when
`.venv/bin/python -m pytest -q` → the whole suite passes, and `.venv/bin/python main.py --help` prints usage.

## Review check
- An all-pass draft makes 0 revise and 0 compare calls.
- At most MAX_ROUNDS revisions.
- Selection ignores ties and breaks remaining ties by fewer soft failures, then by index.
- All drafts failing safety → fallback → canned message, never a story.
- The trace is always written (`finally`).
