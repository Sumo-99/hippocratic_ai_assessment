---
stage: 20_anthropic_invocation
status: in_progress   # set to done after the user's GitHub review
model: orchestrator (opus)
completed: 2026-11-13
live_api_cost_usd: 0.007
reviewer_verdict: n/a
---

# 20_anthropic_invocation: handoff

This branch is **the submission** and is **Anthropic-only**. It first had two backends (OpenRouter + Anthropic behind `LLM_PROVIDER`). At the author's request it was then simplified so the reviewer sees one backend. Development continues on `skeleton` (OpenRouter); merge `skeleton` in when ready.

## Built
- `storyteller/llm.py`: `LLMClient` protocol, `LLMError`, `BudgetExceeded`, `_strict_schema`, `AnthropicClient(api_key=None, on_usage=None)`. That's one class with the retry loop, the budget guard and the usage callback.
- `storyteller/config.py`: `BASE_URL = "https://api.anthropic.com"`, `MODEL = "claude-haiku-5-5"`, `THINKING = {"type": "disabled"}`, `PRICE_IN/OUT_PER_TOKEN` (Anthropic list price). There is no `LLM_PROVIDER`.
- `storyteller/pipeline.py`: `run()` and `baseline()` construct `AnthropicClient` directly (one per turn). `clients.py` and its factory were removed as redundant.
- `requirements.txt`: `anthropic>=2,<3`, no `openai`. `.env.example`: `ANTHROPIC_API_KEY=` only.
- Docs: README setup, ARCHITECTURE colour key, OPEN_QUESTIONS (DECISION list + "Model access"), SPEC (overrides 1-2 marked withdrawn on this branch), CLAUDE.md branch line, a "superseded" note atop the plan.

## Merging from `skeleton` later
The backend lives in `llm.py`, the model block of `config.py` and the 3 client lines of `pipeline.py`. Expect merge conflicts only there: keep this branch's side. Other feature work (prompts, stages, judge, feedback) merges cleanly.

## Decisions
- `llm.py:52`: `base_url` passed explicitly, so the SDK's `ANTHROPIC_BASE_URL` env var can't redirect the key (this closes the gap found in review). `max_retries=0` stops the SDK retrying inside our loop.
- `llm.py:73`: 4xx other than 429 → `LLMError` at once, which includes a schema the API rejects.
- `llm.py:118`: a refusal records usage first (it can be billed), then raises `LLMError` with no retry.
- Cost is computed from token counts at `config.PRICE_*`, since the API returns no dollar cost.

## Verification
- `$PY -m pytest -q` → 218 passed. `tests/test_llm.py` covers the client: request shape, empty system prompt, base URL ignoring the env var, first text block, refusal, no usage, retries, 4xx/429/5xx, cost, budget, plus the FakeLLM and Trace tests.
- Live (user-approved, real Anthropic key):
  - Earlier, on the two-backend version: 2 pipeline runs PASS (one exercising `options`) and the baseline OK, about $0.005. Every structured schema was accepted.
  - After the simplification, with no `LLM_PROVIDER` set: "A story about a sleepy owl who can't find the moon" PASS, $0.0018.

## Open issues / for the human reviewer
- Not exercised live: `revise`, because every story passed in round 0. It's a plain text call on the same path as `generate`.

## Files touched
Committed and pushed for the user's review; see `git log skeleton..anthropic_invocation`.
