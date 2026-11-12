# Bedtime Storyteller Skeleton: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the one-call `main.py` with an async pipeline: gate → extract → branch (depth/breadth) → per-draft generate/judge/revise loop → selection → safety fallback. Every LLM call goes to Claude Haiku 5.5 through OpenRouter, and each run writes a JSON trace.

**Architecture:** The `storyteller/` package is built from small modules, each owning one stage. The modules depend only on an `LLMClient` protocol. A real OpenRouter client and a `FakeLLM` (for tests) both implement that protocol. Pydantic models in `storyteller/models.py` are the contract between modules. Prompts live as `string.Template` files in `storyteller/prompts/`. `pipeline.run(request)` is the only public entry, so the CLI and a future eval script call the same function.

**Tech Stack:** Python 3.11+, `openai` SDK (`AsyncOpenAI`, OpenRouter base URL), `pydantic` v2, `python-dotenv`, `pytest` + `pytest-asyncio`.

**Spec:** `docs/SPEC.md` (the original brief plus the OpenRouter overrides at the top). Read it with this plan.

## Global Constraints

- Branch: all work on `skeleton`. `main` already holds the original `README.md` + `main.py` (commit `8fdc136`) and must not change.
- Model for EVERY call: `anthropic/claude-haiku-5.5` through `https://openrouter.ai/api/v1`, set once in `config.MODEL`.
- Key: env var `OPENROUTER_API_KEY`. Ship `.env.example`, and keep `.env` and `runs/` in `.gitignore`. Never commit a key.
- Never pass `temperature` (the model rejects it). Diversity comes from the brainstorm prompt only.
- Structured output: `response_format={"type":"json_schema","json_schema":{"name":..., "strict": True, "schema": ...}}` plus `extra_body={"provider": {"require_parameters": True}}`, then `Model.model_validate_json`. Check current syntax with Context7 (`openai` python SDK) and OpenRouter's structured-outputs docs before writing `llm.py`.
- Dependencies: `openai`, `pydantic`, `python-dotenv`. Dev only: `pytest`, `pytest-asyncio`. No frameworks.
- Readable code that the author can explain line by line. Comment lightly. Mark judgment calls with `# DECISION:` and copy each into `docs/OPEN_QUESTIONS.md`.
- Tests never touch the network. They use `FakeLLM` only.
- Story length: aim for 500–700 words (`TARGET_WORDS = 600`, said as "about 500–700 words" in the base prompt). The code check accepts 400–900 (`WORD_RANGE = (400, 900)`).
- **No implementation commits until the Human Review Phase (Wave 6) is done.** Subagents and the orchestrator leave all task work uncommitted in the working tree. Per-task reviewers inspect it with `git status` / `git diff` scoped to the task's files. After the user finishes the review phase, the orchestrator commits in the small logical pieces listed under each task's "Commit" step (staging by file with `git add <paths>`). This also avoids parallel subagents racing on the git index.

## API Budget (hard rule)

The user has **$10 of OpenRouter credit total**, and it must cover this skeleton **and** the later eval set. Be extremely conservative.

- **Price** (OpenRouter, checked 2026-11-11): $0.10 per 1M input tokens and $0.50 per 1M output tokens (prompts under 100k tokens). Estimated worst case for one full run (breadth: 3 drafts × 3 revision rounds, every comparison) ≈ 130k in + 35k out ≈ **$0.03**. A typical run is under $0.01. This holds only if hidden reasoning tokens are off. Set `extra_body["reasoning"] = {"enabled": False}`, and check the exact field in Task 1 Step 1 against OpenRouter docs.
- **Who may spend:** only Task 7 (exactly 3 runs) and the final smoke check makes live calls. No subagent makes a live call unless the orchestrator has said so in that task's brief. Every other task uses `FakeLLM`.
- **Guards built into the code (Task 1):**
  - Request usage accounting (`extra_body["usage"] = {"include": True}`) and record `cost` per call in the trace.
  - `config.MAX_RUN_COST_USD = 0.10`: the client raises `BudgetExceeded` once a single run's summed cost passes it.
  - `config.MAX_TOKENS = 2000` per call.
  - `RETRIES = 3`, and no retry on 4xx other than 429.
- **Before any live call** the orchestrator states how many runs it intends and the estimated cost, and waits for the user's OK.
- **Ledger:** after live runs, report the summed `cost` from the traces. Suggest the user also set a credit limit on the key in the OpenRouter dashboard (e.g. $3 for development).

## Context Store and Per-Stage Protocol

`store/` is the build's working memory, in ICM style: one folder per stage, plain markdown, and status read from which files exist. Routing and the stage table live in `store/CLAUDE.md`. It exists so that (a) each subagent loads only ~2k–8k tokens instead of the whole plan and chat, and (b) the user can follow progress by opening folders. There's no human gate between tasks; the store is how the user keeps track.

Every stage runs this protocol:

1. **Before dispatch (orchestrator):** create `store/NN_name/CONTEXT.md` from `store/_templates/CONTEXT.md`. It names the plan section to read, the input `HANDOFF.md` files, the exact files to write, and the "done when" command. It links to the plan rather than copying it (one home per fact). Append `dispatched` to `store/LOG.md`.
2. **Subagent brief = pointers, not content:** "Read `store/CLAUDE.md`, then `store/NN_name/CONTEXT.md`, and only what it lists." Include nothing secret.
3. **On finish (subagent):** write `store/NN_name/HANDOFF.md` from the template, under ~80 lines: what was built, **interfaces as built** (only differences from the plan), every `# DECISION:`, the verification result, open issues for the human reviewer, files touched, and live API cost.
4. **Review (per-task reviewer):** reads the CONTEXT, the HANDOFF and the diff of the listed files. Sets `reviewer_verdict` in the HANDOFF frontmatter. The orchestrator appends `reviewed` to LOG.
5. **Downstream stages read handoffs, not code or chat.** Where a HANDOFF's "interfaces as built" differs from the plan, the HANDOFF wins.
6. **Wave 6 uses the store:** the walkthrough and the data-flow note start from the handoffs' "Open issues / for the human reviewer" and "Decisions" sections. `docs/OPEN_QUESTIONS.md` is compiled from those plus a grep for `# DECISION:`.

`store/` contains notes, not implementation code, so the orchestrator may commit it as it changes (`chore(store): …`). This doesn't loosen the rule that implementation code waits for Wave 6.

**`.gitignore` is maintained, not written once.** A baseline already exists (secrets, Python caches, venvs, `runs/*` except `runs/samples/`, OS files). Any task that introduces a new generated or local-only artifact adds its pattern in the same task and lists it in its HANDOFF. Before every commit the orchestrator runs `git status --ignored --short` and checks that nothing secret or generated is staged and nothing intended (e.g. `runs/samples/`) is ignored.

## Subagent Execution Map

| Wave | Task | Model | Why that model | Parallel with |
|---|---|---|---|---|
| 1 | T1 Foundation: config, models, llm, fake, trace | **sonnet** | Well-specified contract code | — (everything depends on it) |
| 2 | T2 Prompt templates | **opus** | Prompt quality decides story quality; open-ended craft | T3, T4 |
| 2 | T3 Stage modules: gate, extract, brainstorm, generate | **sonnet** | Thin wrappers with fixed interfaces | T2, T4 |
| 2 | T4 Evaluation: judge, length, feedback, compare, keep-better | **sonnet** | Pure logic, fully specified by tests | T2, T3 |
| 3 | T5 Pipeline + selection + cap/fallback + CLI + baseline | **opus** | Most moving parts; async orchestration + edge rules | — |
| 4 | T6 Docs: ARCHITECTURE (Mermaid), README run section, OPEN_QUESTIONS | **sonnet** | Defined deliverable | T7 |
| 4 | T7 Live sample runs (3 requests) + trace summaries | **haiku** | Cheap, repetitive run-and-report | T6 |
| 5 | Automated whole-tree review | **opus** | Final automated gate | — |
| 6 | Human Review Phase (walkthrough → Q&A → data-flow note) | (me, with user) | User owns every line | — |
| 6 | Commit in logical pieces | (me) | Only after user OK | — |
| 7 | Push `skeleton`, draft PR | (me) | Outward-facing, needs user OK | — |

Each task's "Commit" step is the commit message to use **later**, in Wave 6. No implementation code is committed during Waves 1–5. Every row also follows the per-stage protocol above: its `store/` folder name is in `store/CLAUDE.md`, and it isn't done until its `HANDOFF.md` exists.

Wave-2 tasks write disjoint files. T3 and T4 load prompts by name only, so they can run before T2 finishes (tests use `FakeLLM` and stub prompt text). Per-task reviewers are **haiku** for T7 and **sonnet** for the rest.

## File Structure

```
.env.example              OPENROUTER_API_KEY=
.gitignore                exists; maintained per the protocol above
store/                    exists; build context store (CLAUDE.md, LOG.md, _templates/, NN_stage/{CONTEXT,HANDOFF}.md)
requirements.txt
main.py                   CLI (rewritten; keeps the "what I'd build next" docstring slot EMPTY)
storyteller/
  __init__.py
  config.py               constants
  models.py               all pydantic types (the inter-module contract)
  llm.py                  LLMClient protocol, OpenRouterClient, retries, usage capture
  fake.py                 FakeLLM for tests
  trace.py                Trace recorder + stage timer + JSON writer
  prompts/__init__.py     load(name) -> Template
  prompts/*.md            templates (T2)
  gate.py extract.py brainstorm.py generate.py     (T3)
  judge.py compare.py feedback.py                  (T4)
  pipeline.py             (T5)
tests/
  conftest.py test_llm.py test_stages.py test_evaluation.py test_pipeline.py
docs/ SPEC.md ARCHITECTURE.md OPEN_QUESTIONS.md plans/
runs/                     (gitignored, except T7's 3 committed sample traces under runs/samples/)
```

## Review Focus

1. **Model returns JSON that fails pydantic validation, or OpenRouter returns 429/5xx.** Expect a retry (3 attempts, backoff 1s/2s/4s), then a clear exception. A half-parsed object must never come back. Tested in T1.
2. **Brainstorm returns fewer or more than 3 premises, or the wrong categories.** Expect a code check: exactly 3, categories forced to the required set (overwritten in code, with `# DECISION:`). Tested in T3.
3. **Judge marks a "skip" dimension (no named characters, or null premise) as failed.** Code must ignore skipped dimensions no matter what the judge says. Tested in T4.
4. **Every draft fails safety, including the fallback.** Expect the canned message, never a story, with the trace recording why. Tested in T5.
5. **Pairwise comparison disagrees between orders, in keep-better and in selection.** Keep-better keeps the previous draft; selection gives neither side a win. Tested in T4/T5.

---

## Shared Interfaces (defined in T1, referenced by all)

`storyteller/models.py` (field order matters: evidence/reason fields come first so the model writes its reasoning before the verdict):

```python
Category = Literal["adventure", "silly", "comfort", "gentle_lesson", "cozy"]

class GateResult(BaseModel):    reason: str; safe: bool; relevant: bool
class Extraction(BaseModel):
    characters: list[str]; setting: str | None; premise: str | None
    mood: str | None; worry: str | None; category: Category | None
class Premise(BaseModel):       premise: str; category: Category; characters: list[str]; setting: str
class Brainstorm(BaseModel):    premises: list[Premise]
class StorySpec(BaseModel):     # variables for ONE draft
    category: Category; characters: list[str]; setting: str | None
    premise: str | None; mood: str | None; worry: str | None
    named_characters: bool      # True only if the USER named them (drives faithfulness skip)
class Verdict(BaseModel):       evidence: str; passed: bool; fix: str | None
class JudgeResult(BaseModel):   # fixed fields, so strict schema guarantees every dimension
    safety: Verdict; wind_down: Verdict; faithfulness_named: Verdict; consistency: Verdict
    age_language: Verdict; story_arc: Verdict; engagement: Verdict
    faithfulness_premise_mood: Verdict; category_checks: Verdict
class Evaluation(BaseModel):
    judge: JudgeResult; word_count: int; length_ok: bool
    hard_failures: list[str]; soft_failures: list[str]   # dimension names, skips removed
    @property all_passed -> bool
class Comparison(BaseModel):    reason: str; winner: Literal["A", "B"]
class DraftVersion(BaseModel):  round: int; text: str; evaluation: Evaluation; feedback_sent: str | None
class Draft(BaseModel):         index: int; spec: StorySpec; versions: list[DraftVersion]; kept: DraftVersion
class PipelineResult(BaseModel):
    status: Literal["story", "rejected", "safety_fallback_message"]
    story: str | None; message: str | None; trace_path: str | None
```

`HARD = ["safety", "wind_down", "faithfulness_named", "consistency"]`, `SOFT = ["age_language", "story_arc", "engagement", "faithfulness_premise_mood", "category_checks", "length"]` live in `config.py`.

`storyteller/llm.py`:

```python
class LLMClient(Protocol):
    async def text(self, system: str, user: str, *, stage: str) -> str: ...
    async def structured(self, system: str, user: str, schema: type[T], *, stage: str) -> T: ...
```

`stage` is a label such as `"judge"` or `"revise"`. The client sends `(stage, prompt_tokens, completion_tokens, seconds)` to an optional `on_usage` callback, which `Trace` supplies.

`storyteller/config.py`: `MODEL`, `BASE_URL`, `MAX_ROUNDS = 3`, `TARGET_WORDS = 600`, `WORD_RANGE = (400, 900)`, `MAX_TOKENS = 2000`, `MAX_RUN_COST_USD = 0.10`, `LATENCY_BUDGET_S = 60`, `RETRIES = 3`, `UNKNOWN_CATEGORY_SET = ["cozy", "adventure", "silly"]`, `FALLBACK_CATEGORY = "cozy"`, `RUNS_DIR = "runs"`. Values may be overridden by env vars of the same name (optional).

---

### Task 1: Foundation (sonnet)

**Files:** Create `requirements.txt`, `.env.example`, `storyteller/{__init__,config,models,llm,fake,trace}.py`, `storyteller/prompts/__init__.py`, `tests/conftest.py`, `tests/test_llm.py`.

**Interfaces:** Produces everything under *Shared Interfaces*, plus:
- `OpenRouterClient(api_key: str | None = None, on_usage: Callable | None = None)`. It reads `OPENROUTER_API_KEY` via dotenv and raises `RuntimeError("OPENROUTER_API_KEY not set")` if it is missing.
- `FakeLLM(script: dict[str, list[Any]])` replies per `stage` from a FIFO queue. A queued item is either a `str`/model instance, or a callable `(system, user) -> reply`. It records `calls: list[tuple[stage, system, user]]`.
- `Trace(request: str)` has `.set(key, value)`, `.append(key, value)`, `.stage(name)` (a context manager that records wall-clock seconds into `timings[name]`, accumulating), `.on_usage(...)`, and `.write() -> str` (writes `runs/<UTC timestamp>-<slug>.json` and returns the path).
- `prompts.load(name: str) -> string.Template` reads `storyteller/prompts/<name>.md`.

- [ ] **Step 1:** Use Context7 to check `AsyncOpenAI(base_url=..., api_key=...)`, `chat.completions.create(response_format=..., extra_body=...)`, and `resp.usage`. Write down any differences from the Global Constraints in OPEN_QUESTIONS.
- [ ] **Step 2: Failing tests** in `tests/test_llm.py`:
  - `test_structured_retries_then_validates`: patch the client's raw call to return `'{"bad":1}'` first, then a valid GateResult JSON. Expect a `GateResult` back and 2 raw calls.
  - `test_structured_gives_up_after_retries`: raw call always invalid. Expect `LLMError` after `config.RETRIES` attempts.
  - `test_never_sends_temperature`: inspect the captured kwargs. Expect `"temperature" not in kwargs`, `kwargs["model"] == "anthropic/claude-haiku-5.5"`, and reasoning disabled plus usage included in `extra_body`.
  - `test_budget_exceeded_raises`: fake raw responses report `cost=0.06` each. The second call raises `BudgetExceeded` when `MAX_RUN_COST_USD = 0.10`.
  - `test_fake_llm_fifo_and_records_calls`.
  - `test_trace_stage_accumulates_and_writes_json` (use `tmp_path`, monkeypatch `RUNS_DIR`).
  - Patch `asyncio.sleep` so backoff doesn't slow tests.
- [ ] **Step 3:** Run `pytest tests/test_llm.py -v`. Expect FAIL (import errors).
- [ ] **Step 4:** Implement. Retries wrap the raw call **and** validation. Back off `2**attempt` seconds on `openai.APIError`/`RateLimitError`/`ValidationError`. The schema name is `schema.__name__`, and the schema comes from `schema.model_json_schema()`. If strict mode rejects pydantic's schema (e.g. `additionalProperties`), add a small `_strict_schema()` helper that sets `additionalProperties: false` and lists all properties as required. Mark that helper `# DECISION:`.
- [ ] **Step 5:** Run `pytest tests/test_llm.py -v`. Expect PASS.
- [ ] **Step 6 (orchestrator):** commit `feat: foundation (config, models, OpenRouter client, fake LLM, trace)`.

### Task 2: Prompt templates (opus)

**Files:** Create `storyteller/prompts/{base,adventure,silly,comfort,gentle_lesson,cozy,judge,gate,extract,brainstorm,revise,compare,baseline}.md`. Add `tests/test_prompts.py`.

**Interfaces:** Each template's `$placeholders` must match exactly, because T3, T4 and T5 call `.substitute()` with these keys:

| File | Placeholders | Content (from spec §1–6) |
|---|---|---|
| `base` | `$target_words` | Audience 5–10, short sentences, read-aloud, no violence, no real danger, no imitable unsafe acts, final third winds down, no cliffhanger. Output the story text only, with an optional title line. |
| `<category>` ×5 | none | Three headed sections: `## Structure` (ordered beats), `## Do / Don't`, `## Judge checks` (bullets). Content per spec §4. |
| `gate` | none (request goes in user msg) | Judges the REQUEST, not a story. Reshape-able requests count as safe. Include the TODO note on edgy requests (like "dragon eats villagers") as a comment line for the author, not for the model. |
| `extract` | none | Rules from spec §2 verbatim: never invent a premise; comfort only with a worry; moral dilemma → gentle_lesson; null if unclear. |
| `brainstorm` | `$characters`, `$setting`, `$categories` | 3 distinct premises seen together. Named characters/setting appear in every one. One premise per listed category, in order. |
| `judge` | `$rubric_context`, `$category_checks` | Per dimension: evidence → passed → fix (location-specific). How to mark skipped dimensions: evidence "N/A", passed true. Mood "honored in a bedtime-appropriate way". Never mention revisions. |
| `revise` | none (system = generation prompt + revise suffix) | Change only what the feedback asks; keep everything else; output the full story. |
| `compare` | none | "Which would a parent rather read to their child at bedtime?" Answer with reason first, then winner A/B. |
| `baseline` | none | Empty file. `baseline()` sends only the request (original behaviour). |

- [ ] **Step 1: Failing test** `test_all_templates_substitute`: for each file, `load(name).substitute(**KEYS[name])` succeeds with dummy values, and `$` placeholders outside the table are absent (`Template.get_identifiers()` equals the expected set, Python ≥3.11).
- [ ] **Step 2:** Run `pytest tests/test_prompts.py`. Expect FAIL.
- [ ] **Step 3:** Write the templates. Keep each category file under ~40 lines. Prompts should be explicit and concrete, with no clever tricks.
- [ ] **Step 4:** Run the test again. Expect PASS.
- [ ] **Step 5 (orchestrator):** commit `feat: prompt templates (base, categories, judge, gate, extraction, brainstorm, revision, comparison)`.

### Task 3: Stage modules (sonnet)

**Files:** Create `storyteller/{gate,extract,brainstorm,generate}.py`, `tests/test_stages.py`.

**Interfaces (Consumes T1; prompt names from T2):**
- `async def check_request(llm, request: str) -> GateResult`
- `def gate_message(g: GateResult) -> str | None`: returns a friendly message with the reason plus "try another request" when `not (safe and relevant)`, otherwise `None`.
- `async def extract(llm, request: str) -> Extraction`, followed by `normalize(e: Extraction) -> Extraction`. Normalization is code, not LLM: `comfort` with `worry is None` becomes `cozy` (`# DECISION:`). Category stays `None` here; the fallback happens in `plan_drafts`.
- `def plan_drafts(e: Extraction) -> Literal["depth", "breadth"]` returns `"depth"` iff `e.premise`.
- `def breadth_categories(e: Extraction) -> list[Category]` returns `[e.category]*3` if a category is known, otherwise `UNKNOWN_CATEGORY_SET`.
- `async def brainstorm(llm, e: Extraction) -> list[Premise]`: validates exactly 3 (`LLMError` otherwise), overwrites each `premise.category` with `breadth_categories(e)[i]`, and when characters/setting were named, overwrites `premise.characters`/`setting` with them.
- `def depth_spec(e) -> StorySpec` and `def breadth_specs(e, premises) -> list[StorySpec]`. `named_characters = bool(e.characters)`. Category falls back to `FALLBACK_CATEGORY`.
- `def build_system_prompt(spec: StorySpec) -> str`: base + category bundle + one `Characters: …` / `Setting: …` / `Premise: …` / `Mood: …` / `Worry: …` line per non-empty field.
- `async def write_story(llm, spec) -> str` (stage `"generate"`). `async def revise_story(llm, spec, previous: str, feedback: str) -> str` (stage `"revise"`; system = `build_system_prompt(spec)` + revise template; user = previous story + feedback).

- [ ] **Step 1: Failing tests:**
  - `test_gate_message_none_when_ok` / `test_gate_message_includes_reason`
  - `test_plan_depth_when_premise` / `test_plan_breadth_when_no_premise`
  - `test_breadth_categories_known` → `["silly"]*3`; `test_breadth_categories_unknown` → `["cozy","adventure","silly"]`
  - `test_comfort_without_worry_normalized_to_cozy`
  - `test_brainstorm_forces_named_chars_and_categories` (FakeLLM returns premises with wrong categories)
  - `test_brainstorm_rejects_wrong_count`
  - `test_system_prompt_omits_absent_variables`: no `Mood:` line when mood is None; `Characters: Alice, Bob` when present
  - `test_depth_spec_falls_back_to_cozy`
- [ ] **Step 2:** Run `pytest tests/test_stages.py`. Expect FAIL.
- [ ] **Step 3:** Implement. Add a module docstring to `gate.py` stating that it judges requests, not stories, plus the `# TODO(edgy-requests):` line.
- [ ] **Step 4:** Run `pytest tests/test_stages.py`. Expect PASS.
- [ ] **Step 5 (orchestrator):** commit `feat: gate, extraction, routing, brainstorm and storyteller stages`.

### Task 4: Evaluation and comparison (sonnet)

**Files:** Create `storyteller/{judge,feedback,compare}.py`, `tests/test_evaluation.py`.

**Interfaces:**
- `def word_count(text) -> int`; `def length_ok(text) -> bool` (inclusive `WORD_RANGE`).
- `def skipped_dimensions(spec) -> set[str]`: adds `faithfulness_named` if `not spec.named_characters and spec.setting is None`, and `faithfulness_premise_mood` if `spec.premise is None and spec.mood is None`.
- `async def evaluate(llm, spec, story) -> Evaluation` (stage `"judge"`). Each call is fresh and gets the full rubric, with no mention of revisions. Builds hard/soft failure lists from `JudgeResult` minus skips. Adds `"length"` to soft failures when the length check fails.
- `def build_feedback(ev: Evaluation) -> str`: if `hard_failures` exist, list only those, otherwise list the soft ones. One bullet per dimension with its `fix` (fall back to `evidence` if `fix` is None). The length bullet states the actual count and the target range.
- `async def compare_once(llm, a: str, b: str) -> Literal["A","B"]` (stage `"compare"`).
- `async def compare_both_orders(llm, x: str, y: str) -> Literal["x","y","tie"]`: runs both orders concurrently with `asyncio.gather`. Order 1 is A=x, B=y; order 2 is A=y, B=x. Agreement gives that side; disagreement gives `"tie"`.
- `async def keep_better(llm, prev: DraftVersion, new: DraftVersion) -> tuple[DraftVersion, dict]`: more hard checks passed wins; on equal hard counts, `compare_both_orders`, where `"y"` (new) wins and `"x"` or `"tie"` keeps prev. The returned dict is the trace record `{rule, result, kept_round}`.

- [ ] **Step 1: Failing tests:**
  - `test_skips_ignored_even_if_judge_fails_them` (Review Focus 3)
  - `test_length_failure_is_soft`
  - `test_feedback_hard_only_when_any_hard_fails`: a soft failure is present but absent from the feedback text
  - `test_feedback_soft_when_no_hard`
  - `test_compare_both_orders_agree`: queue `["A","B"]` → `"x"` (x chosen in both orders). `test_compare_both_orders_disagree_is_tie`: queue `["A","A"]` → `"tie"` (position bias)
  - `test_keep_better_prefers_more_hard_passes_without_compare` (assert no `"compare"` calls)
  - `test_keep_better_tie_keeps_prev` / `test_keep_better_new_wins_both_orders`
- [ ] **Step 2:** Run `pytest tests/test_evaluation.py`. Expect FAIL.
- [ ] **Step 3:** Implement. The judge user message gives the story plus a `$rubric_context` built in code that lists characters/setting/premise/mood and the skipped dimensions.
- [ ] **Step 4:** Run `pytest tests/test_evaluation.py`. Expect PASS.
- [ ] **Step 5 (orchestrator):** commit `feat: rubric judge, feedback priority, pairwise comparison and keep-better rule`.

### Task 5: Pipeline, selection, cap/fallback, CLI (opus)

**Files:** Create `storyteller/pipeline.py`, `tests/test_pipeline.py`. Rewrite `main.py`.

**Interfaces (Consumes T1–T4):**
- `async def run_draft(llm, spec, index, trace) -> Draft`: generate, then evaluate. Then loop up to `MAX_ROUNDS` times: stop early if `kept.evaluation.all_passed`; otherwise build feedback, revise from `kept`, evaluate, `keep_better`. Every version and comparison goes to the trace.
- `async def select(llm, drafts: list[Draft]) -> Draft`. With 1 draft, return it. `survivors` are the drafts with no hard failures. If there are none, return `best_available(drafts)`: fewest hard failures, ties broken with `compare_both_orders` (`# DECISION:` if 3 drafts tie, use win counting as below). Otherwise compare every survivor pair concurrently (`gather`); a tie gives no wins. Sort key: `(-wins, len(soft_failures), index)`.
- `async def run(request: str, llm: LLMClient | None = None) -> PipelineResult`: gate → (reject, return message) → extract → plan → specs → `gather(run_draft…)` → if `"safety"` is in the hard failures of every kept draft, run the fallback: one fresh cozy draft (spec = depth spec with category cozy, premise None), generate plus one evaluation, no revisions (`# TODO(safety-fallback): first pass`). If that still fails safety, return `CANNED_SAFETY_MESSAGE`. Otherwise call `select`. Always `trace.write()` in a `finally`. Also record `branch`, `timings`, and a `latency_budget_exceeded` bool.
- `async def baseline(request: str, llm=None) -> str`: one `text()` call with system `""` and user = request.
- `main.py`: `argparse` with `--baseline`, `--verbose` (prints branch, drafts, rounds per draft, final pass/fail, per-stage timings, trace path) and an optional positional `request` (prompts with `input()` when omitted). Keep the original docstring slot at the top with its question, left empty for the author.
- Hooks: `# TODO(critique-check)` after evaluate, `# TODO(user-feedback)` after printing.

- [ ] **Step 1: Failing tests** (all with FakeLLM using callable replies):
  - `test_rejected_request_returns_message_and_no_generation`
  - `test_depth_single_draft_stops_when_all_pass` (exactly 1 `"generate"`, 0 `"revise"`, 0 `"compare"`)
  - `test_revision_loop_respects_max_rounds` (judge always fails a soft check, so exactly `MAX_ROUNDS` revises)
  - `test_breadth_runs_three_drafts_and_selects_by_wins`
  - `test_selection_tiebreak_soft_failures_then_index`
  - `test_selection_filters_hard_failures`
  - `test_all_fail_safety_uses_fallback_story` / `test_fallback_fails_safety_returns_canned` (Review Focus 4: `result.story is None`)
  - `test_only_nonsafety_hard_failures_returns_best_available`
  - `test_trace_written_with_required_keys` (`gate, extraction, branch, drafts, final, timings, usage`)
- [ ] **Step 2:** Run `pytest tests/test_pipeline.py`. Expect FAIL.
- [ ] **Step 3:** Implement in the order depth → breadth → cap/fallback, re-running the tests after each.
- [ ] **Step 4:** Run `pytest -q`. Expect all PASS. Then run `python main.py --help`. Expect usage text.
- [ ] **Step 5 (orchestrator):** commit in 2–3 pieces: `feat: pipeline depth path`, `feat: breadth branch and selection`, `feat: cap behaviour, safety fallback, CLI and baseline`.

### Task 6: Docs (sonnet), in parallel with T7

**Files:** Create `docs/ARCHITECTURE.md`, `docs/OPEN_QUESTIONS.md`. Modify `README.md` by appending a `## Running this solution` section; leave the original text untouched.

- [ ] **Step 1:** ARCHITECTURE diagram 1, end to end, per spec "Structure" bullet: user, gate (reject arrow back to user), extraction, depth/breadth diamond with brainstorm, the per-draft loop as one box, selection, safety check, fallback exit, output, trace sink. Diagram 2 shows inside one draft's loop. Use `classDef llm` vs `classDef code` colors. Show the rubric as a small box, with a table beside it (dimension | hard/soft | LLM/code | skip rule).
- [ ] **Step 2:** OPEN_QUESTIONS: `grep -rn "DECISION:" storyteller main.py`, one entry per hit (file:line, decision, alternative). Include the OpenRouter override and the strict-schema helper.
- [ ] **Step 3:** README run section: venv, `pip install -r requirements.txt`, `cp .env.example .env`, `python main.py "…"`, `--baseline`, `--verbose`, `pytest`.
- [ ] **Step 4:** Check that the Mermaid parses (paste into `npx -y @mermaid-js/mermaid-cli` or the GitHub preview if available; otherwise eyeball it carefully).
- [ ] **Step 5 (orchestrator):** commit `docs: architecture diagrams, open questions, run instructions`.

### Task 7: Live sample runs (haiku), in parallel with T6

**Precondition:** the user has put `OPENROUTER_API_KEY` in `.env` themselves (it is never pasted into chat or a brief). The orchestrator has stated "3 runs, est. ≤ $0.10 total" and the user has OK'd it. If the key is missing, skip and report "no key". Never run more than the 3 requests, and never re-run a crashed request without asking.

- [ ] **Step 1:** Run `python main.py --verbose "tell me a story"`, `… "a story about Alice and her cat Bob"`, `… "my son is scared of the dark"`.
- [ ] **Step 2:** Copy the 3 traces to `runs/samples/` (un-ignore that folder with `!runs/samples/` in `.gitignore`). Check that the traces contain no key: `grep -ri "sk-or" runs/samples` should print nothing.
- [ ] **Step 3:** Report per run: branch, number of drafts, rounds, final failures, total seconds against the 60s budget, and token totals. Don't edit code. If a run crashes, report the traceback and stop.
- [ ] **Step 4 (orchestrator):** commit `chore: sample run traces`.

### Wave 5: Automated review (orchestrator + opus reviewer)

- [ ] Opus reviewer over the uncommitted working tree (`git diff` + untracked files) against `docs/SPEC.md` and this plan. Fix the findings it confirms.
- [ ] `pytest -q` passes. `grep -rn "sk-or" .` (excluding `.env` and `.git`) prints nothing, and `.env` is gitignored.

### Wave 6: Human Review Phase (user + orchestrator, interactive, BEFORE any implementation commit)

The user is responsible for every line and wants a clear picture before anything is committed. Run the three steps **one at a time**. Move on only when the user says so. Don't produce a later step's material early.

- [ ] **Step 1: Walkthrough of the core parts.** Explain the codebase in reading order:
  1. `storyteller/models.py`: the schemas. Every module talks through them, and the strict JSON output depends on their field order (evidence first).
  2. `storyteller/llm.py`: the one place money is spent. Covers the OpenRouter call, structured output, retries, and the budget guard.
  3. `storyteller/pipeline.py` `run()`: the flow, gate → extract → branch → draft loops → select → fallback.
  4. `judge.py` / `feedback.py` / `compare.py`: the quality loop (rubric, hard vs soft priority, keep-better, two-order comparison).
  5. `generate.py` + `prompts/`: how the system prompt is put together.

  Flag the **must-review** spots explicitly. These are the schemas, the hard/soft lists in `config.py`, the safety fallback, the budget guard, and every `# DECISION:`.
- [ ] **Step 2: Questions.** Answer the user's questions. Fix anything they want changed (still uncommitted), then re-run `pytest -q`.
- [ ] **Step 3: Core functions and data flow note, given when the user asks.** One note listing each core function (signature, inputs, outputs, which LLM stage it calls) and the data flow from request to `PipelineResult` and trace JSON, including which fields of which model carry each decision. Offer to save it as `docs/REVIEW_NOTES.md`.
- [ ] **Then commit** in the logical pieces named under each task, after the user OKs it.

### Wave 7: Push and PR (orchestrator)

- [ ] **Ask the user before pushing.** Then `git push -u origin skeleton` and open a draft PR (`gh pr create --draft --base main`) covering what's done, what's stubbed (deferred TODOs), the `# DECISION:` list, and the total API spend so far. Do not merge.
