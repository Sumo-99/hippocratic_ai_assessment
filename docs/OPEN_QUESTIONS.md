# Open questions and decisions

Every `# DECISION:` marker in the code, the spec overrides, and every deferred `TODO(...)` hook. Written for the author to confirm or overturn.

## DECISION entries (in code)

1. **`storyteller/llm.py:33` strict schema.** Chosen: post-process pydantic's JSON schema ourselves (`additionalProperties: false`, all fields required, drop `default`). Alternative: openai's `to_strict_json_schema` helper, which ties us to an SDK internal.
2. **`storyteller/llm.py:79` retry policy.** Chosen: 4xx other than 429 fails immediately as `LLMError`; 429, 5xx, connection and validation errors retry with `2**attempt` second backoff. Alternative: retry everything.
3. **`storyteller/llm.py:112` missing cost.** Chosen: if OpenRouter omits `usage.cost`, estimate from token counts using the list price in `config.py`, so the budget guard cannot silently read zero. Alternative: treat as zero, or refuse to run without cost data. Unverified live whether `usage.cost` is present.
4. **`storyteller/pipeline.py:44` where `feedback_sent` lives.** Chosen: stored on the version the feedback produced (round 0 has none). Alternative: store it on the version it critiqued.
5. **`storyteller/pipeline.py:94` safety-first selection.** Chosen: drafts failing safety are dropped before counting hard failures, so an unsafe story is never shown. Alternative: plain fewest-hard-failures, where a draft failing only safety (1) could beat one failing two other hard checks (2). Spec section 8 does not say this; the reviewer should confirm.
6. **`storyteller/pipeline.py:100` tie on hard failures.** Chosen: reuse the normal win counting (both orders, then soft failures, then index). Alternative: a separate tiebreak rule.
7. **`storyteller/pipeline.py:213` budget exhaustion.** Chosen: `BudgetExceeded` becomes a friendly message with `status="error"` and the trace is kept. Alternative: let it raise. Other errors (`LLMError`, missing key) still raise to the CLI.
8. **`storyteller/extract.py:15` comfort without a worry.** Chosen: code changes the category to cozy. Alternative: trust the model, or ask the user.
9. **`storyteller/judge.py:59` failures computed in code.** Chosen: failures come from each dimension's `passed` flag, not the judge's own summary, and skipped dimensions are dropped. Alternative: trust the judge's summary list.
10. **`storyteller/compare.py:17` position bias.** Chosen: ask twice with the stories swapped and accept only an answer both orders agree on. Alternative: one call (cheaper, order-biased).
11. **`storyteller/compare.py:33` ties.** Chosen: ties keep the previous draft, so a revision must clearly win. Alternative: prefer the revision on ties.

## Decisions recorded only in handoffs (no marker in code)

12. **Gate prompt author note.** `prompts/gate.md` line 1 holds an HTML comment about edgy requests. `prompts.load()` does not strip it, so the model sees it. Alternative: strip `<!-- -->` lines in `load()`.
13. **Judge checks shown to the writer.** Category files include `## Judge checks` in the generation prompt too, so the writer sees what it will be judged on. Alternative: strip that section for generation.
14. **Brainstorm override rules.** Our category plan always overrides the model's; user-named characters and setting override; model-invented ones are kept only when the user named none.
15. **Fallback story acceptance.** The cozy fallback is returned if it passes safety even when it fails other checks (one evaluation, no revisions). Alternative: revise it, or retry.
16. **Placement.** The 01 handoff chose one `OpenRouterClient` per run so the budget is tracked per run.

## Spec overrides

- Model access goes through OpenRouter (`https://openrouter.ai/api/v1`, model `anthropic/claude-haiku-5.5`) with the `openai` SDK, not the `anthropic` SDK. The key is `OPENROUTER_API_KEY`, not `ANTHROPIC_API_KEY`.
- No `temperature` is sent; the model does not support it. Structured output uses OpenRouter's JSON schema mode with `provider.require_parameters: true`, validated with pydantic. Reasoning is turned off.

## Deferred hooks (`TODO(...)`)

- `TODO(edgy-requests)` `storyteller/gate.py:3`: borderline requests such as a dragon who eats villagers. Decide whether the gate passes them and lets the judge catch it, or rejects up front.
- `TODO(critique-check)` `storyteller/pipeline.py:35`: an open-ended "what would a parent dislike?" pass after evaluate. Deferred until evals show the rubric misses things.
- `TODO(safety-fallback)` `storyteller/pipeline.py:127`: the fallback is first pass (one cozy draft, one evaluation, no revisions). A later version might retry or soften the request.
- `TODO(user-feedback)` `main.py:58`: ask the listener what they thought and offer a revised story.

## Other open items for the reviewer

- No live call had validated that Haiku 5.5 accepts the pydantic-derived strict schemas when these docs were written.
- `latency_budget_exceeded` is recorded but nothing acts on it.
- `requirements.txt` is unpinned.

## Eval backlog (check when building the eval set, not before)

1. **The judge may be too lenient.** In the 3 sample runs (`runs/samples/`, 2026-11-12), 8 of 9 drafts passed every rubric dimension on the first try, so the revision loop ran only once. Possible causes: good drafts, a rubber-stamping judge, or a rubric that's too easy to satisfy. How to check:
   - Hand-label a few drafts and measure agreement with the judge.
   - Feed the judge deliberately flawed stories (a cliffhanger ending, a contradiction, a scary detail, a named character missing) and count how many it catches.
   - Compare pass rates per dimension.
   - Where to tune: `storyteller/prompts/judge.md`, the category `## Judge checks` sections, and `storyteller/judge.py`.
2. **Extraction of family references.** Re-run the "my son is scared of the dark" case and confirm `characters` comes back `[]`. The prompt rule was added 2026-11-12 after a live run extracted "my son" as a named character; that run has not been re-checked live.

## Wave 5 review outcomes (2026-11-12)

Fixed (each pinned by a regression test):
- `compare.py` keep_better: **safety outranks the other hard checks.** The comparison is `(fails safety?, number of hard failures)`, so a safe version is never replaced by an unsafe one. `# DECISION:` in code.
- `judge.py` / `generate.py` / `models.py`: a new `StorySpec.named_setting` field. The hard `faithfulness_named` check is skipped unless the **user** named characters or a setting; settings the brainstorm invents no longer trigger it.
- `pipeline.py`: drafts and selection comparisons run through `_all_or_cancel` (asyncio.TaskGroup). One failure cancels the sibling tasks, so nothing keeps spending after `run()` returns.
- `pipeline.py`: the client is created inside `try`, so a missing key still writes a trace.
- `config.py`: `load_dotenv()` now runs before any env var is read, so knobs in `.env` take effect. `BASE_URL` and `MODEL` are fixed and no longer env-overridable. `# DECISION:` in code.
- `llm.py`: a response with no `usage` raises `LLMError` instead of a bare AttributeError.
- `generate.py`: the system-prompt join is rewritten as a plain `if` plus `append` for readability.
- The "my son" extraction issue was already fixed in `prompts/extract.md` (see Eval backlog item 2).

Accepted / deferred:
- **The budget pre-check is per call while about 6 calls run concurrently**, so a run can overshoot `MAX_RUN_COST_USD` by a few cents. Accepted as harmless at these prices.
- **`finish_reason == "length"` is not checked.** A story cut off at `MAX_TOKENS=2000` would be accepted (unlikely: about 600 words ≈ 800 tokens), and cut-off JSON is retried with the same input. Revisit if traces ever show truncation.
