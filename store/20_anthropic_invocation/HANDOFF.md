---
stage: 20_anthropic_invocation
status: in_progress   # set to done after the live smoke and the user's review
model: orchestrator (opus)
completed: 2026-11-13
live_api_cost_usd: 0.005
reviewer_verdict: n/a
---

# 20_anthropic_invocation: handoff

## Built
- `storyteller/llm.py`: `BaseLLMClient` (retry loop, validation, budget guard, usage callback) and `RetryableError`. `OpenRouterClient` is now a subclass that only implements `_call`; its request kwargs and error messages are unchanged.
- `storyteller/llm_anthropic.py`: `AnthropicClient(api_key=None, on_usage=None)`, the direct Anthropic backend.
- `storyteller/clients.py`: `build_client(on_usage=None, provider=None) -> LLMClient` and `PROVIDERS`. The only module that names a concrete client.
- `storyteller/config.py`: `PROVIDER` (env `LLM_PROVIDER`, default `openrouter`), `ANTHROPIC_MODEL`, `ANTHROPIC_THINKING`, `ANTHROPIC_PRICE_IN/OUT_PER_TOKEN`.
- `storyteller/pipeline.py`: `run()` and `baseline()` call `build_client()` (3 lines changed).
- `requirements.txt` (`anthropic>=2,<3`), `.env.example` (`LLM_PROVIDER`, `ANTHROPIC_API_KEY`), README backend paragraph, OPEN_QUESTIONS decisions.

## Interfaces as built
- Stage is `store/20_*` (the plan text said 19; 19 was taken). Base is `skeleton` at 8ce1517 (the plan said a084a1a; the wrapper files were identical).
- `BaseLLMClient._with_retries(system, user, schema, stage)` takes the schema class (not a provider-specific `response_format`); each subclass builds its own request from it.
- Otherwise as in the plan.

## Decisions
- `llm_anthropic.py`: `AsyncAnthropic(max_retries=0)`, so the SDK doesn't retry inside our loop. Alternative: leave SDK retries on (up to 9 attempts per call).
- `llm_anthropic.py`: a refusal records usage first (it can be billed), then raises `LLMError` with no retry. Alternative: retry it, paying up to 3 times for a likely repeat.
- `llm_anthropic.py`: 4xx other than 429 is fatal, same as OpenRouter; this includes a schema the API rejects.
- `clients.py`: `llm_anthropic` is imported lazily, so OpenRouter users never import the `anthropic` package.
- `config.py`: `LLM_PROVIDER` is env-switchable. It only picks between two fixed endpoints, so it doesn't break the "model and endpoint are fixed" decision.

## Verification
- `$PY -m pytest -q` → 237 passed (baseline was 210; +10 Anthropic, +12 contract, +5 factory).
- `git diff --stat skeleton -- tests/test_llm.py` → empty (the OpenRouter regression guard is untouched).
- `LLM_PROVIDER=nope`: `run()` raises a `ValueError` that names the allowed values, and still writes a trace.

- **Live smoke (2026-11-13, user-approved, real Anthropic key, `LLM_PROVIDER=anthropic`):** every structured schema was accepted.
  - "A story about a shy dragon who loves baking": PASS, 0 revisions, $0.0018. Calls: gate, extract, generate, judge. Trace `runs/20261113T170849070818Z-…json`.
  - "tell me a story": PASS, 0 revisions, $0.0022. Calls: gate, extract, options, generate, judge. Trace `runs/20261113T170915291958Z-…json`.
  - `--baseline "a cat story"`: exit 0, about 400 words, no system prompt. Run twice because the first output was cut off by `head`, so there were 4 live runs, not 3.
  - Total about $0.005.

## Open issues / for the human reviewer
- Not exercised live: the `revise` stage, because both stories passed in round 0. It is a plain text call on the same code path as `generate`, which did run live.
- No cache-token accounting: we never enable prompt caching, so `input_tokens` + `output_tokens` is the full bill.

## Files touched (uncommitted)
- storyteller/llm.py, storyteller/llm_anthropic.py, storyteller/clients.py, storyteller/config.py, storyteller/pipeline.py
- tests/test_llm_anthropic.py, tests/test_llm_contract.py, tests/test_clients.py, tests/test_pipeline.py (2 strings)
- requirements.txt, .env.example, README.md, docs/OPEN_QUESTIONS.md
