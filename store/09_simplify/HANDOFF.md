---
stage: 09_simplify
status: done
model: orchestrator
completed: 2026-11-12
live_api_cost_usd: 0.00
reviewer_verdict: n/a (author reviews in the walkthrough)
---

# 09_simplify: handoff

The author decided (in a side conversation, confirmed here) to trim the build to a small first version and let evals decide what to add back. The full build is preserved on branch `skeleton_extensive` (commit d25c61b). I byte-compared its 46 code/test/doc files with the working tree before trimming, and they were identical.

## Built / changed
- `storyteller/models.py`: removed Premise, Brainstorm, Comparison and Draft, and the `named_*` flags. Status `safety_fallback_message` became `safety_message`.
- `storyteller/pipeline.py`: rewritten. The flow is gate → extract → `make_spec` → `write_and_revise` → final safety check. `keep_better(prev, new)` is now pure code.
- `storyteller/generate.py`: `make_spec` replaces `depth_spec` and `breadth_specs`.
- `storyteller/extract.py`: the routing helpers were removed.
- `storyteller/judge.py`: the skip rule now reads the spec directly.
- `storyteller/llm.py`: no system message is sent when it's empty (for `--baseline`), and the redundant `load_dotenv` was dropped.
- `storyteller/prompts/base.md`: a new "Using the request" section (use what's given, invent what's missing).
- Deleted: `storyteller/brainstorm.py`, `storyteller/compare.py`, `prompts/brainstorm.md`, `prompts/compare.md`.
- `main.py`: `--verbose` shows the category and each round's failures.
- Tests rewritten: 67 pass, FakeLLM only.
- Docs: ARCHITECTURE.md (both diagrams redrawn), OPEN_QUESTIONS.md (simplification, decisions, deferred list, eval backlog), README trace description.

## Interfaces as built
- `pipeline.run(request, llm=None) -> PipelineResult`
- `pipeline.baseline(request, llm=None) -> str`
- `pipeline.keep_better(prev: DraftVersion, new: DraftVersion) -> DraftVersion`
- `pipeline.write_and_revise(llm, spec, trace) -> DraftVersion`
- `generate.make_spec(e: Extraction) -> StorySpec`
- Trace keys: request, gate, extraction, spec, versions, guard, final, timings, calls, usage, total_cost_usd, latency_budget_exceeded (and error, when there is one).

## Decisions
- Author-confirmed: gate and extraction stay separate; revisions start from the kept version (option A); the guard puts safety first, counts only hard failures, and gives ties to the new version.

## Open issues / for the human reviewer
- The vague-request behaviour now depends on the base and cozy prompts, not a brainstorm. It hasn't been checked live.
- `runs/samples/` traces come from the extensive build.

## Files touched (uncommitted)
- See `git status`.
