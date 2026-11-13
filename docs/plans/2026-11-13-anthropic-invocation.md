# Anthropic Direct Invocation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a second LLM backend that calls the Anthropic Messages API directly. You pick the backend with one env var, OpenRouter stays the default, and nothing outside the wrapper needs to know which backend is in use.

**Architecture:** `storyteller/llm.py` gets a provider-neutral base class that owns the retry loop, budget guard and usage callback. `OpenRouterClient` keeps its exact behaviour on top of that base. A new `AnthropicClient` (`storyteller/llm_anthropic.py`) is the second subclass. A factory, `build_client()` in `storyteller/clients.py`, is the only place that names a concrete client. The pipeline calls the factory, so later backend changes never touch it again.

**Tech Stack:** Python 3.14, `anthropic` SDK (async client), `openai` SDK (unchanged), pydantic 2, pytest + pytest-asyncio.

**Spec:** This plan. The requirements come from a review of the `skeleton` branch's wrapper, summarized in "Gaps this plan closes" below. Base branch: `skeleton` (a084a1a).

## Gaps this plan closes (the spec)

| # | Gap in `skeleton` | Closed by |
|---|---|---|
| G1 | `pipeline.py` hardcodes `OpenRouterClient(...)` in `run()` and `baseline()` | Task 3: factory + pipeline swap |
| G2 | `structured()` sends OpenAI-style `response_format` + OpenRouter's `provider.require_parameters` | Task 2: `output_config.format` json_schema |
| G3 | Cost comes from OpenRouter's `usage.cost` extension | Task 2: cost computed from `input_tokens`/`output_tokens` × configured price |
| G4 | System prompt, `max_tokens`, model ID, key name differ | Task 2 + config |
| G5 | Retry loop catches `openai.*` exceptions directly | Task 1: base loop is SDK-agnostic; subclasses translate their own errors |
| G6 | `LLMError`/`BudgetExceeded` should be shared, not redefined | Task 1: stay in `llm.py`, imported by the new client |
| G7 | `tests/test_llm.py` is coupled to OpenRouter internals | Task 2: own test file; Task 3: shared contract tests run against both clients |

## Global Constraints

- **Work in a git worktree** on new branch `anthropic_invocation` cut from `skeleton`. The main checkout is on `user_feedback_feature` and has uncommitted work, so never `git checkout` there.
- **Default provider stays `openrouter`.** If `LLM_PROVIDER` is unset, behaviour is byte-for-byte what `skeleton` does today.
- **`tests/test_llm.py` must pass unmodified.** That is the backwards-compatibility proof for OpenRouter.
- **Tests never touch the network.** Fake the SDK call by patching `client._client.<...>.create`, as `test_llm.py` already does.
- **Anthropic model:** `claude-haiku-5-5` (native ID of the model OpenRouter serves as `anthropic/claude-haiku-5.5`). **Price:** $0.10 in / $0.50 out per 1M tokens.
- **Thinking off on Anthropic** (`thinking={"type": "disabled"}`), mirroring OpenRouter's `reasoning: {enabled: False}`. Haiku 5.5 accepts this at its default effort. Do not send `temperature` or `output_config.effort`.
- **New env keys:** `ANTHROPIC_API_KEY` (the user supplies it, in `.env`) and `LLM_PROVIDER` (`openrouter` | `anthropic`).
- **Repo rules (CLAUDE.md):**
  - No live API calls without the user's OK.
  - Never open, print or echo `.env`.
  - No commits of generated code before the user has reviewed it. `store/` notes may be committed.
- **Touch outside the wrapper is limited to:**
  - `pipeline.py`: 1 import + 2 call sites.
  - `tests/test_pipeline.py`: 2 monkeypatch targets.
  - `requirements.txt`, `.env.example`, and docs.

  Find these edits by **grepping for `OpenRouterClient`**, never by line number, since other branches are changing these files.

## Review Focus

1. **Anthropic rejects one of our pydantic schemas.** The schemas use `anyOf` with null, `enum`, `$defs`, and the judge's schema is built at runtime. A 400 must surface as a fast `LLMError` naming the stage and `HTTP 400`, not 3 retries. Tests: Task 3 `test_4xx_not_retried`. The live smoke (Task 5) exercises every structured stage.
2. **A response whose first content block isn't text** (a thinking block, or empty content). The client must return the first `text` block's text, and `""` if there is none. Tests: Task 2 `test_picks_first_text_block`, `test_no_text_block_returns_empty`.
3. **`stop_reason == "refusal"`.** Haiku 5.5 has no server-side fallback. The client must raise `LLMError` immediately with no retry, so it isn't billed three times. Test: Task 2 `test_refusal_is_fatal_not_retried`.
4. **`LLM_PROVIDER` typo or odd casing** (`"Anthropic "`, `"anthorpic"`). Odd casing and spacing get normalized. An unknown value raises `ValueError` listing the allowed values, from inside `run()`'s `try`, so a trace is still written. Tests: Task 3 `test_provider_is_normalized`, `test_unknown_provider_raises`, plus the existing `test_missing_key_still_writes_trace`.
5. **Double retries.** The Anthropic SDK retries 2× by default *inside* our 3-attempt loop, which would allow up to 9 billed-path calls. Construct `AsyncAnthropic(max_retries=0)`. Test: Task 2 `test_sdk_retries_disabled`.

---

### Task 0: Branch, worktree, dependency, stage notes

**Files:**
- Create: worktree `../hippocratic_ai_assessment-anthropic` on branch `anthropic_invocation`
- Create: `store/20_anthropic_invocation/CONTEXT.md` (from `store/_templates/CONTEXT.md`; plan section = this file)
- Modify: `requirements.txt` (add `anthropic>=2,<3`), `.env.example`, `CLAUDE.md` (Branches list + stage table row)

- [ ] **Step 1: Create the worktree from `skeleton`**

```bash
cd /Users/sumanthramesh/Documents/dev/hippocratic_takehome/hippocratic_ai_assessment
git worktree add ../hippocratic_ai_assessment-anthropic -b anthropic_invocation skeleton
cp docs/plans/2026-11-13-anthropic-invocation.md ../hippocratic_ai_assessment-anthropic/docs/plans/
```

All later commands run from the worktree. Use the main checkout's venv: `PY=../hippocratic_ai_assessment/.venv/bin/python`.

- [ ] **Step 2: Confirm the baseline is green before any change**

Run: `$PY -m pytest -q`
Expected: all pass. Record the count in `CONTEXT.md`.

- [ ] **Step 3: Add the dependency and install it**

Add `anthropic>=2,<3` to `requirements.txt`, then run `$PY -m pip install "anthropic>=2,<3"`.
Expected: `$PY -c "import anthropic; print(anthropic.__version__)"` prints 2.x.

- [ ] **Step 4: Extend `.env.example`**

```
OPENROUTER_API_KEY=
# Which backend to call: openrouter (default) or anthropic
LLM_PROVIDER=openrouter
ANTHROPIC_API_KEY=
```

- [ ] **Step 5: Add the stage row and branch line to `CLAUDE.md`, then write `CONTEXT.md`**

Branch line: `` `anthropic_invocation` (from `skeleton` at a084a1a): direct Anthropic API backend behind `LLM_PROVIDER`. Plan: `docs/plans/2026-11-13-anthropic-invocation.md` ``. Stage row: `store/20_anthropic_invocation/` | Anthropic backend | (orchestrator) | —. Append a line to `store/LOG.md`. These are notes, so they may be committed now.

---

### Task 1: Provider-neutral base class (OpenRouter behaviour unchanged)

**Files:**
- Modify: `storyteller/llm.py`
- Test: `tests/test_llm.py` (**unmodified**, it is the regression guard)

**Interfaces:**
- Produces, all in `storyteller/llm.py`:
  - `LLMClient`, `LLMError`, `BudgetExceeded`, `_strict_schema`: unchanged names and behaviour.
  - `class RetryableError(Exception)`: raised by a subclass's `_call` for transient failures (connection, timeout, 429, 5xx).
  - `class BaseLLMClient`:
    - `__init__(self, on_usage: Callable | None = None)` sets `self.on_usage` and `self.total_cost = 0.0`.
    - `async text(system, user, *, stage) -> str`
    - `async structured(system, user, schema: type[T], *, stage) -> T`
    - `async _with_retries(system, user, schema: type[BaseModel] | None, stage) -> str | T`
    - `_check_budget(self) -> None` raises `BudgetExceeded` if `total_cost >= MAX_RUN_COST_USD`.
    - `_record_usage(self, stage, prompt_tokens: int, completion_tokens: int, cost: float, seconds: float) -> None` adds cost, calls `on_usage`, and raises `BudgetExceeded` if `total_cost > MAX_RUN_COST_USD`.
    - `async _call(self, system: str, user: str, schema: type[BaseModel] | None, stage: str) -> str` is abstract. It makes one HTTP call, calls `_check_budget()` first and `_record_usage(...)` after, and returns the raw text. It raises `RetryableError` for transient failures and `LLMError` for fatal ones.
  - `class OpenRouterClient(BaseLLMClient)`: same constructor signature, `RuntimeError` message and request kwargs as today. Its `_call` builds `response_format` from `schema` (when not None) and translates `openai.APIStatusError` 4xx≠429 → `LLMError(f"{stage}: HTTP {code}: {e}")`, and other `openai.APIError` → `RetryableError`.

- [ ] **Step 1: Run the regression guard before refactoring**

Run: `$PY -m pytest tests/test_llm.py -q`. Expected: PASS.

- [ ] **Step 2: Refactor `llm.py` to the interfaces above**

`_with_retries` keeps today's loop. It catches `RetryableError` and `pydantic.ValidationError` and retries with `asyncio.sleep(2 ** attempt)`. It lets `LLMError` and `BudgetExceeded` propagate. After `config.RETRIES` attempts it raises `LLMError(f"{stage}: failed after {config.RETRIES} attempts: {last}")`. Validation stays inside the loop. `llm.py` must not import `anthropic`.

- [ ] **Step 3: Run the regression guard and the full suite**

Run: `$PY -m pytest -q`. Expected: same pass count as Task 0 Step 2, and `tests/test_llm.py` untouched (`git diff --stat tests/test_llm.py` is empty).

---

### Task 2: `AnthropicClient`

**Files:**
- Modify: `storyteller/config.py`
- Create: `storyteller/llm_anthropic.py`
- Test: `tests/test_llm_anthropic.py`

**Interfaces:**
- Consumes: `BaseLLMClient`, `RetryableError`, `LLMError`, `_strict_schema` from Task 1.
- Produces:
  - `config.PROVIDER: str = os.getenv("LLM_PROVIDER", "openrouter").strip().lower()`
  - `config.ANTHROPIC_MODEL = "claude-haiku-5-5"`
  - `config.ANTHROPIC_THINKING = {"type": "disabled"}`
  - `config.ANTHROPIC_PRICE_IN_PER_TOKEN = 0.10 / 1_000_000` and `config.ANTHROPIC_PRICE_OUT_PER_TOKEN = 0.50 / 1_000_000`, with a comment saying these are the *only* cost source on this path, so they must change with the model.
  - `MODEL`, `BASE_URL` and `PRICE_*` stay untouched. Keep the existing "fixed, not env-overridable" DECISION comment for the models: `LLM_PROVIDER` only switches between two fixed endpoints.
  - `AnthropicClient(BaseLLMClient)` in `storyteller/llm_anthropic.py`, with `__init__(self, api_key: str | None = None, on_usage: Callable | None = None)`:
    - It reads `ANTHROPIC_API_KEY` and raises `RuntimeError("ANTHROPIC_API_KEY not set")` if empty.
    - It builds `self._client = anthropic.AsyncAnthropic(api_key=key, max_retries=0)`.

`_call` sends `self._client.messages.create(**kwargs)` with these kwargs:
- `model=config.ANTHROPIC_MODEL`, `max_tokens=config.MAX_TOKENS`, `thinking=config.ANTHROPIC_THINKING`, and `messages=[{"role": "user", "content": user}]`.
- `system=system` **only if `system` is non-empty**.
- `output_config={"format": {"type": "json_schema", "schema": _strict_schema(schema.model_json_schema())}}` **only if `schema` is not None**.

It maps the response like this:
- `stop_reason == "refusal"` → `LLMError(f"{stage}: model refused ({stop_details.category if present})")`
- `usage is None` → `LLMError`
- cost = `input_tokens*IN + output_tokens*OUT`, then `_record_usage(stage, input_tokens, output_tokens, cost, seconds)`
- It returns the first block with `type == "text"`, else `""`.

Errors map like this: `anthropic.APIStatusError` with a status <500 other than 429 → `LLMError(f"{stage}: HTTP {code}: {e}")`. Other `anthropic.APIError` → `RetryableError`.

Fake for these tests: patch `client._client.messages.create` with an async recorder returning `SimpleNamespace(content=[SimpleNamespace(type="text", text=...)], stop_reason="end_turn", stop_details=None, usage=SimpleNamespace(input_tokens=10, output_tokens=5))`.

- [ ] **Step 1: Write the failing tests in `tests/test_llm_anthropic.py`**

```python
async def test_request_shape_structured():
    # kw = recorded kwargs of one structured("s", "u", GateResult, stage="gate") call
    assert kw["model"] == "claude-haiku-5-5"
    assert kw["max_tokens"] == config.MAX_TOKENS
    assert kw["thinking"] == {"type": "disabled"}
    assert kw["system"] == "s"
    assert kw["messages"] == [{"role": "user", "content": "u"}]
    assert kw["output_config"]["format"]["type"] == "json_schema"
    assert kw["output_config"]["format"]["schema"]["additionalProperties"] is False
    assert "temperature" not in kw and "extra_body" not in kw and "response_format" not in kw

async def test_text_call_has_no_output_config():          # "output_config" not in kw
async def test_empty_system_is_omitted():                 # text("", "u") -> "system" not in kw
async def test_picks_first_text_block():                  # content=[thinking block, text "story"] -> "story"
async def test_no_text_block_returns_empty():             # content=[] -> text() == ""
async def test_refusal_is_fatal_not_retried():            # stop_reason="refusal" -> LLMError, len(calls) == 1
async def test_cost_from_tokens_and_callback():
    # usage input_tokens=1000, output_tokens=2000
    assert seen[0][:4] == ("gate", 1000, 2000, 1000 * 0.10e-6 + 2000 * 0.50e-6)
async def test_no_usage_raises():                          # usage=None -> LLMError
def test_missing_key_raises(monkeypatch):                  # RuntimeError, match "ANTHROPIC_API_KEY not set"
def test_sdk_retries_disabled():                           # AnthropicClient(api_key="k")._client.max_retries == 0
```

Use `pytest.approx` for the cost.

- [ ] **Step 2: Run them to see them fail**

Run: `$PY -m pytest tests/test_llm_anthropic.py -q`. Expected: FAIL (`ModuleNotFoundError: storyteller.llm_anthropic`).

- [ ] **Step 3: Implement `config` additions and `AnthropicClient` per the Interfaces block**

- [ ] **Step 4: Run them to see them pass, plus the full suite**

Run: `$PY -m pytest -q`. Expected: all pass.

---

### Task 3: Factory, pipeline swap, contract tests

**Files:**
- Create: `storyteller/clients.py`
- Modify: `storyteller/pipeline.py`. Grep for `OpenRouterClient` and expect 3 hits: the import, `run()` and `baseline()`.
- Modify: `tests/test_pipeline.py`. Grep for `"OpenRouterClient"` and expect 2 monkeypatch targets; change them to `"build_client"`.
- Test: `tests/test_clients.py`, `tests/test_llm_contract.py`

**Interfaces:**
- Consumes: `OpenRouterClient` (Task 1), `AnthropicClient` (Task 2), `config.PROVIDER`.
- Produces:
  - `PROVIDERS = ("openrouter", "anthropic")` in `storyteller/clients.py`.
  - `build_client(on_usage: Callable | None = None, provider: str | None = None) -> LLMClient` in `storyteller/clients.py`:
    - It normalizes `(provider or config.PROVIDER).strip().lower()`.
    - An unknown value raises `ValueError("LLM_PROVIDER must be one of: openrouter, anthropic (got '...')")`.
    - It imports `llm_anthropic` **inside** the anthropic branch, so OpenRouter users never import the `anthropic` package.
  - In `pipeline.py`:
    - `from .clients import build_client` replaces the `OpenRouterClient` import. `BudgetExceeded` and `LLMClient` still come from `.llm`.
    - `run()` calls `build_client(on_usage=trace.on_usage)`, still inside the `try`.
    - `baseline()` uses `llm or build_client()`.

- [ ] **Step 1: Write the failing tests**

`tests/test_clients.py`:
```python
def test_default_is_openrouter(monkeypatch):     # PROVIDER "openrouter", OPENROUTER_API_KEY set -> isinstance OpenRouterClient
def test_anthropic_selected(monkeypatch):        # provider="anthropic", key set -> isinstance AnthropicClient; .on_usage is the passed fn
def test_provider_is_normalized(monkeypatch):    # provider=" Anthropic " -> AnthropicClient
def test_unknown_provider_raises():              # provider="anthorpic" -> ValueError, match "openrouter, anthropic"
def test_only_factory_names_concrete_clients():
    # scan storyteller/**/*.py except llm.py, llm_anthropic.py, clients.py:
    # no file contains "OpenRouterClient(" or "AnthropicClient("
```

`tests/test_llm_contract.py`: a fixture is parametrized over `["openrouter", "anthropic"]`. It returns `(client, calls, script)`, where `script(*items)` queues replies. A `str` item is a successful reply with that text. An `int` item makes the fake raise that SDK's status error with that HTTP code: `openai.APIStatusError` or `anthropic.APIStatusError`, built with a response object from the HTTP library each SDK depends on. Each test runs against both clients:
```python
async def test_retry_then_validate(c):        # script('{"bad":1}', GOOD) -> GateResult; len(calls) == 2
async def test_gives_up_after_retries(c):     # script(*['{"bad":1}'] * config.RETRIES) -> LLMError; len(calls) == config.RETRIES
async def test_4xx_not_retried(c):            # script(400) -> LLMError match "HTTP 400"; len(calls) == 1
async def test_429_and_5xx_retried(c):        # script(429, 503, GOOD) -> GateResult; len(calls) == 3
async def test_budget_exceeded(c, monkeypatch):  # MAX_RUN_COST_USD 0.10, each call costs 0.06 -> 2nd call raises BudgetExceeded
async def test_usage_callback_shape(c):       # on_usage receives (stage, int, int, float, float)
```

For `test_budget_exceeded`, make each call cost 0.06:
- OpenRouter: set `usage.cost=0.06`.
- Anthropic: monkeypatch `ANTHROPIC_PRICE_IN_PER_TOKEN` so that 10 input tokens cost 0.06.

- [ ] **Step 2: Run them to see them fail**

Run: `$PY -m pytest tests/test_clients.py tests/test_llm_contract.py -q`. Expected: `test_clients` FAILs on import, and the guard test fails on `pipeline.py`. Contract tests may already pass. That is fine: they pin the shared behaviour.

- [ ] **Step 3: Implement `clients.py`, the pipeline swap and the `test_pipeline.py` target rename**

- [ ] **Step 4: Run the full suite**

Run: `$PY -m pytest -q`. Expected: all pass. `git diff --stat tests/test_llm.py` is empty, and `git diff tests/test_pipeline.py` shows only the two target strings changed.

---

### Task 4: Docs and handoff

**Files:**
- Modify:
  - `README.md` setup section: how to choose a provider, and which key each one needs.
  - `docs/OPEN_QUESTIONS.md`: amend the "One `OpenRouterClient` per run" and "Model access goes through OpenRouter" decisions to say "one client per run, via `build_client()`", and that the provider is chosen by `LLM_PROVIDER`.
- Create: `store/20_anthropic_invocation/HANDOFF.md` (template; `status: done` only after Task 6)

- [ ] **Step 1: Edit the two docs.** Leave `docs/SPEC.md` alone, since it records the original brief.
- [ ] **Step 2: Write `HANDOFF.md`.** List the new files and interfaces (`build_client`, `BaseLLMClient`, `AnthropicClient`), the env keys, and the five Review Focus items with their tests. Append a line to `store/LOG.md`.

---

### Task 5: Live smoke test (**needs the user's OK first**)

**Precondition:** the user has put `ANTHROPIC_API_KEY` in the worktree's `.env` themselves. Never open, print or echo it.

- [ ] **Step 1: Ask the user.** "3 live runs on `claude-haiku-5-5` via Anthropic: one full pipeline run with a specific request, one with a vague request (exercises the options stage), and one baseline. Estimated ≤ $0.04 total. Each run is hard-capped at `MAX_RUN_COST_USD` = $0.10." Wait for a clear yes.
- [ ] **Step 2: Run them.** Use `LLM_PROVIDER=anthropic $PY main.py "<request>" --verbose` for the two pipeline runs, and `LLM_PROVIDER=anthropic $PY main.py "<request>" --baseline` for the third. Expected:
  - Each pipeline run ends with a story or a gate message.
  - The trace shows calls for `gate`, `extraction`, `judge`, and `options` on the vague run, with non-zero tokens and cost.
  - There is no `LLMError`.

  If a run crashes, stop and report. Do not re-run without asking.
- [ ] **Step 3: Record the results.** Note the trace paths, per-stage cost and any schema errors in `HANDOFF.md`.

---

### Task 6: Review gate (no commits of code before this)

- [ ] **Step 1: Show the user the full diff.** Run `git diff skeleton --stat` and walk through it. This is the repo's walkthrough → Q&A → data-flow pass.
- [ ] **Step 2: Commit on `anthropic_invocation` only after the user approves.** Set `status: done` in `HANDOFF.md` and append to `store/LOG.md`.
