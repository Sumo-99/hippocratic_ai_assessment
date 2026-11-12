---
stage: 01_foundation
status: done
model: sonnet
completed: 2026-11-11
live_api_cost_usd: 0.00
reviewer_verdict: approved
---

# 01_foundation: handoff

## Built
- `requirements.txt`, `.env.example`, `pytest.ini` (`asyncio_mode = auto`, `testpaths = tests`)
- `storyteller/config.py`: constants, env-overridable; `HARD`/`SOFT` lists.
- `storyteller/models.py`: all pydantic types, evidence/reason fields first.
- `storyteller/llm.py`: `LLMClient` protocol, `OpenRouterClient`, `LLMError`, `BudgetExceeded`, `_strict_schema`.
- `storyteller/fake.py`: `FakeLLM`. `storyteller/trace.py`: `Trace`. `storyteller/prompts/__init__.py`: `load(name)`.
- `tests/conftest.py` (autouse fixture makes `asyncio.sleep` instant), `tests/test_llm.py` (9 tests).
- `.venv` made with python3.12 (gitignored); installed openai 3.49.0, pydantic 2.14.3.

## Doc check (Context7 + OpenRouter docs, 2026-11-11)
- openai SDK: `AsyncOpenAI(base_url, api_key)`, `chat.completions.create(response_format={"type":"json_schema","json_schema":{name,strict,schema}}, extra_body=...)` all as in the plan. Exceptions: `APIStatusError` (has `.status_code`), `RateLimitError` (429), `APIConnectionError`, all under `openai.APIError`.
- OpenRouter: structured outputs + `provider.require_parameters: true` confirmed. Reasoning off = `"reasoning": {"enabled": false}` (confirmed). Usage: OpenRouter docs now say usage details (incl. `usage.cost`) are ALWAYS returned; `usage: {include: true}` is therefore redundant but kept as harmless belt and braces. `cost` is an extra field on the SDK usage object, read with `getattr(usage, "cost", 0)`.

## Interfaces as built
- `Trace.on_usage` / client `on_usage` callback signature is `(stage, prompt_tokens, completion_tokens, cost, seconds)`. The plan listed it without `cost`. Trace stores it in `calls` and writes `total_cost_usd`.
- `OpenRouterClient.total_cost` (float) accumulates per client instance: make one client per run.
- Trace JSON keys: `request`, anything set/appended, `timings`, `calls`, `total_cost_usd`.
- `FakeLLM` asserts (AssertionError) when a stage's queue is empty. Fake structured replies are returned as given (not validated).
- Added `pytest.ini` (not in the plan's file list) for `asyncio_mode = auto`.
- Otherwise: matches the plan.

## Decisions
- `llm.py` `_strict_schema`: post-process pydantic's schema (additionalProperties false, all required, drop `default`). Alternative: openai's internal helper.
- `llm.py` `_with_retries`: 4xx other than 429 raises `LLMError` immediately (no retry). 429, 5xx, connection errors and validation failures retry with `2**attempt` s backoff, up to `RETRIES` attempts, then `LLMError`.
- Budget guard: checked before each call (refuses if already at/over) and after (raises once the sum passes `MAX_RUN_COST_USD`). `BudgetExceeded` is not caught by the retry loop.

## Verification
- `.venv/bin/python -m pytest tests/test_llm.py -v` → `9 passed in 0.95s` (no network; SDK `create` is replaced by a recorder).
- Checked by hand: strict schema output for `Extraction`/`JudgeResult` has `additionalProperties: false` and full `required` on nested `$defs`.

## Open issues / for the human reviewer
- No live call has validated that haiku-5.5 accepts pydantic-derived strict schemas (nullable `anyOf`, enums). First live call in Task 7 will tell.
- `usage.cost` is assumed to be in USD at `resp.usage.cost`; unverified live. If absent, cost is 0 and the budget guard silently never trips: check the first live trace.
- Budget is tracked per client instance, so Task 5 must build one `OpenRouterClient` per run.
- `requirements.txt` is unpinned.

## Files touched (uncommitted)
- New: `requirements.txt`, `.env.example`, `pytest.ini`, `storyteller/{__init__,config,models,llm,fake,trace}.py`, `storyteller/prompts/__init__.py`, `tests/conftest.py`, `tests/test_llm.py`, `store/01_foundation/HANDOFF.md`
- `.gitignore` unchanged. `docs/OPEN_QUESTIONS.md` not created (Task 6 owns it; DECISIONs above are to be copied there).

## Orchestrator review (2026-11-11)
- Approved. Fix applied: when `usage.cost` is missing, cost is estimated from tokens (`config.PRICE_IN_PER_TOKEN` / `PRICE_OUT_PER_TOKEN`) so the budget guard can't silently read 0. Marked `# DECISION:` in llm.py.
