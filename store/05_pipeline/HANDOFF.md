---
stage: 05_pipeline
status: done
model: opus
completed: 2026-11-11
live_api_cost_usd: 0.00
reviewer_verdict: approved
---

# 05_pipeline: handoff

## Built
- `storyteller/pipeline.py`: `run_draft`, `select`, `best_available`, `run`, `baseline`, `CANNED_SAFETY_MESSAGE`, `BUDGET_MESSAGE`.
- `tests/test_pipeline.py`: 20 tests (the plan's list plus max-rounds override, early stop, feedback-from-kept, single-draft select, never-pick-safety-failure, budget error, trace-on-crash, client wiring, baseline, verbose output).
- `main.py`: rewritten. argparse `request?`, `--baseline`, `--verbose`. Original docstring question kept at the top, answer left empty.
- `storyteller/models.py`: `PipelineResult.status` gains `"error"`.

## Interfaces as built
- **Interface change:** `PipelineResult.status` is now `Literal["story", "rejected", "safety_fallback_message", "error"]`. `"error"` = `BudgetExceeded` was caught; `message` = `BUDGET_MESSAGE`.
- `select(llm, drafts, trace=None)`: extra optional `trace` so the selection record (`rule`, `survivors`, `pairs`, `wins`, `chosen`) goes into the trace.
- `best_available(llm, drafts, record)`: helper; `record` is the selection dict it fills.
- `run()` catches only `BudgetExceeded`. `LLMError`, and the `RuntimeError` from a missing key, still raise (trace is still written).
- `baseline()` writes no trace.
- `--verbose` reads the trace file, so it shows exactly what was recorded.

## Data flow (for the human review)
`run(request)` makes a `Trace`, plus one `OpenRouterClient(on_usage=trace.on_usage)` when `llm` is None. Then: gate (`gate`) → rejected? return a message. → extract (`extraction`) → `plan_drafts` (`branch`) → depth: `[depth_spec]`; breadth: brainstorm (`premises`) → `breadth_specs`. → `gather(run_draft …)`: each draft appends `{index, spec, versions[], comparisons[], kept_round}` to `drafts` (sorted by index afterwards). Every draft's kept version failing safety → cozy fallback (`fallback`) → story, or canned message. Otherwise `select` (`selection`). `final` = `{status, source, draft_index, round, all_passed, hard_failures, soft_failures}`. A `finally` always adds `timings` (per stage, `draft_N`, `drafts`, `selection`, `fallback`, `total`), `latency_budget_exceeded`, `usage` (calls/tokens per stage), then `Trace.write()` adds `calls` and `total_cost_usd`. It returns `PipelineResult(status, story, message, trace_path)`.

## Decisions
- `pipeline.py:44` `feedback_sent` is stored on the version the feedback produced (round 0 = None). The alternative was to store it on the version it critiqued.
- `pipeline.py:94` `best_available` drops safety-failing drafts before counting hard failures, because spec §8 says never show an unsafe story. Without this, a draft failing only safety (1) would beat one failing wind_down+consistency (2).
- `pipeline.py:100` A tie on hard failures (2 or 3 drafts) reuses the same win counting (both orders, then soft failures, then index).
- `pipeline.py:213` `BudgetExceeded` → friendly `status="error"`. Other exceptions propagate.
- The fallback story is returned if it passes safety, even when it fails other hard/soft checks (spec: one evaluation, no revisions). No `# DECISION:` marker. It sits under `TODO(safety-fallback)`.
- Hooks: `TODO(critique-check)` pipeline.py:35, `TODO(safety-fallback)` pipeline.py:127, `TODO(user-feedback)` main.py:58.

## Verification
- `.venv/bin/python -m pytest -q` → `78 passed`
- `.venv/bin/python main.py --help` → prints usage.
- No live calls. Tests write traces to `tmp_path`; no `runs/` was created.

## Open issues / for the human reviewer
- Spec §8 says "best available" picks by fewest hard failures, then pairwise. I added the safety filter on top (see Decisions). Check you agree.
- Worst-case calls with MAX_ROUNDS=3 in breadth: 3×(1 gen + 4 judge + 3 revise + 6 compare) + 6 selection compares + gate/extract/brainstorm ≈ 51 calls. The per-run budget guard (`MAX_RUN_COST_USD`) protects this.
- `latency_budget_exceeded` is only recorded. Nothing acts on it.
- `main.py` does not catch `LLMError` or a missing key. The user sees a traceback with a clear message.

## Files touched (uncommitted)
- New: `storyteller/pipeline.py`, `tests/test_pipeline.py`, `store/05_pipeline/HANDOFF.md`
- Modified: `main.py` (rewritten), `storyteller/models.py` (one line: `"error"` status)

## Orchestrator review (2026-11-11)
- Approved after reading pipeline.py end to end: early stop on all-pass, feedback from kept version, keep-better per round, safety-all-fail → fallback before selection, survivors-only win counting, best_available never returns a safety failure, trace written in finally. Flag for human review: the safety-first DECISION in best_available and that LLMError still raises to the CLI (trace kept).
