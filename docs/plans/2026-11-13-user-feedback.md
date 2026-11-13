# Post-story user feedback: implementation plan

> **For agentic workers:** each task has a stage contract in `store/1N_feedback_*/CONTEXT.md`. Read that contract, `CLAUDE.md`, and only the task section of this plan it names. Steps use checkbox (`- [ ]`) syntax.

**Goal:** after a story is delivered, the user can quit or give free-form feedback. The feedback runs one more pass of the existing revise → judge → guard loop and returns a new story, again and again until they quit.

**Architecture:** the feedback loop is an outer loop around today's machinery. Each feedback turn re-runs the **same** gate → extract → spec path on the whole conversation (the original request plus every piece of feedback so far, newest last). The extraction now also returns a `preferences` block and an `overrides` list. The spec carries both. `build_system_prompt` puts the preferences on top of the prompt stack. One code function, `apply_overrides`, runs after every judge call and makes waived non-safety failures non-blocking. A feedback turn's first draft is a revision of the delivered story, not a fresh write. After that, the internal MAX_ROUNDS loop is unchanged.

**Tech stack:** Python 3, pydantic v2, pytest (asyncio auto mode), `FakeLLM`. No new dependencies.

**Spec:** the handoff note pasted in the session (summarised in `store/11_feedback_contracts/CONTEXT.md` → "Requirements").

## Global constraints
- No live API calls. Tests use `FakeLLM` only. Run tests with `.venv/bin/python -m pytest -q`.
- Gate (`gate.py`, `gate.md`), `revise_story` / `revise.md`, and the judge (`judge.py`, `judge.md`) stay **unchanged**.
- `safety` can never be waived. It is missing from the `Waivable` enum, so a model cannot even name it.
- `config.HARD` is unchanged: `wind_down` stays hard. Waivers are applied per run, never by editing HARD/SOFT.
- When there is no feedback, everything a request-only run sends to the model is byte-identical to today's (all 98 existing tests keep passing unchanged).
- Leave code **uncommitted** for the author's review (CLAUDE.md). Store notes may be committed.

## Shared interfaces (fixed by Task 0; every later task codes against these)

```python
# storyteller/config.py
WAIVABLE = [d for d in HARD + SOFT if d != "safety"]   # order: HARD then SOFT

# storyteller/models.py
Waivable = Literal["wind_down", "faithfulness_named", "consistency", "age_language",
                   "story_arc", "engagement", "faithfulness_premise", "category_checks", "length"]

class Override(BaseModel):       # evidence first, like every other LLM-filled schema
    quote: str                   # the user's own words that conflict, copied exactly
    dimension: Waivable
    allow: str                   # the scoped exception in plain words ("end on a cliffhanger")

class Extraction(BaseModel):     # + two fields at the END (old fields keep their order)
    ...
    preferences: str | None      # plain instructions on how to tell/change the story
    overrides: list[Override]

class StorySpec(BaseModel):      # + two optional fields
    ...
    preferences: str | None = None
    overrides: list[Override] = []

class Evaluation(BaseModel):     # + one optional field
    ...
    waived: list[str] = []       # failures ignored because the user asked for them

class StorySession(BaseModel):   # the state the outer loop carries between turns
    request: str
    feedback: list[str] = []
    spec: StorySpec
    story: DraftVersion          # the delivered version that the next feedback revises

class PipelineResult(BaseModel): # + one optional field
    ...
    session: StorySession | None = None
```

Functions later tasks rely on:
- `overrides.apply_overrides(ev: Evaluation, overrides: list[Override]) -> Evaluation` (Task 1)
- `overrides.waivable_text() -> str`: one `- name: definition` line per WAIVABLE dimension, for the extract prompt (Task 1)
- `extract.extract(llm, text: str) -> Extraction`: same signature as today. `text` is the conversation text. It substitutes `$waivable_dimensions` (Task 1)
- `extract.normalize(e: Extraction, text: str = "") -> Extraction`: also drops overrides whose `quote` is not in `text` (Task 1)
- `prompts/extract.md` contains the placeholder `$waivable_dimensions` (Task 2)
- `generate.make_spec(e)` copies `preferences` and `overrides` into the spec (Task 2)
- `generate.build_system_prompt(spec)` puts a preferences block FIRST when `spec.preferences` is set (Task 2)
- `pipeline.conversation_text(request: str, feedback: list[str]) -> str` (Task 3)
- `pipeline.run(request, llm=None) -> PipelineResult` (unchanged signature, now with `.session`) (Task 3)
- `pipeline.give_feedback(session: StorySession, feedback: str, llm=None) -> PipelineResult` (Task 3)

## Review focus
1. **Feedback revision that breaks a hard check the old story passed.** A reasonable user expects their change to be applied, not silently thrown away. So the feedback revision becomes the turn's starting version (round 0) and is never compared against the old story. The internal loop then repairs it. Test: Task 3 `test_feedback_revision_is_not_discarded_by_the_guard`.
2. **A draft that fails safety after feedback.** Expect the canned message, and the session still holds the last good story so the user can try different feedback. Test: Task 3 `test_unsafe_draft_after_feedback_shows_canned_message_and_keeps_session`.
3. **Over-eager waivers** (the extraction waives `wind_down` for "an exciting adventure"). An override must quote the user's words exactly, and code drops it if the quote isn't in the conversation. Test: Task 1 `test_normalize_drops_overrides_whose_quote_is_not_in_the_text`.
4. **Feedback that takes back an earlier waiver** ("actually, a calm ending"). Re-extracting the whole conversation means the new extraction simply has no override. The guard then enforces wind_down again. Test: Task 3 `test_later_feedback_can_take_back_a_waiver`.
5. **Unsafe feedback text.** The gate sees the conversation including the new feedback and rejects it. Nothing is written, and the session is unchanged. Test: Task 3 `test_unsafe_feedback_is_rejected_by_the_gate_and_session_kept`.

---

### Task 0: Shared contracts (orchestrator)
**Files:** modify `storyteller/models.py`, `storyteller/config.py`. **Store:** `store/11_feedback_contracts/`.
- [ ] Add the types and fields exactly as in "Shared interfaces".
- [ ] Run the full suite: 98 passed (new fields have defaults, or sit at the end of LLM schemas that tests build with keywords).

  *Note:* `Extraction` gains two required fields. The existing tests that build `Extraction(...)` pass every field by keyword, so they need `preferences=None, overrides=[]` added. Task 0 updates `tests/test_stages.py::ext` and `tests/test_pipeline.py` extraction helpers only for this.

### Task 1: Overrides and extraction code (sonnet)
**Files:** create `storyteller/overrides.py`. Modify `storyteller/extract.py`. Test: create `tests/test_overrides.py`. **Store:** `store/12_feedback_overrides/`.

**Interfaces:** consumes Task 0 types. Produces `apply_overrides`, `waivable_text`, `WAIVABLE_DEFINITIONS`, `normalize(e, text)`, and `extract` substituting `waivable_dimensions`.

- [ ] Write failing tests in `tests/test_overrides.py`:
  - `test_waived_hard_failure_moves_to_waived`: ev with hard `["wind_down","consistency"]` + override on wind_down → hard `["consistency"]`, waived `["wind_down"]`.
  - `test_waived_soft_failure_moves_to_waived`: soft `["length","engagement"]`, override on length → soft `["engagement"]`, waived `["length"]`.
  - `test_safety_is_never_waived_even_if_smuggled_in`: an `Override.model_construct(quote="x", dimension="safety", allow="x")` leaves `"safety"` in hard_failures.
  - `test_safety_is_not_representable`: `Override(quote="x", dimension="safety", allow="x")` raises `ValidationError`, and `"safety" not in Override.model_json_schema()["properties"]["dimension"]["enum"]`.
  - `test_waivable_enum_matches_config`: `set(get_args(Waivable)) == set(config.WAIVABLE)` and `"safety" not in config.WAIVABLE`.
  - `test_no_overrides_returns_the_same_evaluation`: result `==` input, `waived == []`.
  - `test_judge_verdict_is_untouched`: the waived dimension's `ev.judge.wind_down.passed` is still False (we record what the judge said; only blocking changes).
  - `test_all_passed_true_when_only_waived_failures_remain`.
  - `test_waivable_text_lists_every_waivable_dimension_and_not_safety`.
  - `test_normalize_drops_overrides_whose_quote_is_not_in_the_text`: quote "leave it hanging" kept for text "...leave it hanging", dropped for text "an exciting adventure". Matching ignores case and runs of whitespace.
  - `test_normalize_without_text_keeps_old_behaviour`: existing call `normalize(e)` still works (comfort/no-worry rule, empty character drop) and drops all overrides (no text means nothing to quote).
  - `test_extract_substitutes_waivable_dimensions`: with `prompts.load` returning `Template("X $waivable_dimensions")`, the system prompt sent contains `wind_down` and not `- safety`.
- [ ] Run them and watch them fail.
- [ ] Implement `storyteller/overrides.py`:
  - `WAIVABLE_DEFINITIONS: dict[str, str]`: one plain line per WAIVABLE dimension, phrased as *what kind of user ask conflicts with it* (for example, wind_down: "the story ends calm, safe and sleepy, with no cliffhanger, open question or surprise at the end"). Define a `length` entry around `config.WORD_RANGE`. Assert at import that its keys == `config.WAIVABLE`.
  - `waivable_text()` → `"\n".join(f"- {k}: {v}" ...)` in WAIVABLE order.
  - `apply_overrides(ev, overrides)`: waived = {o.dimension for o in overrides} − {"safety"}. Return `ev.model_copy(update=...)` with hard/soft filtered and `waived` = the failures actually removed (hard then soft, in original order). `# DECISION:` coarse form: the whole dimension is waived at the guard; the judge prompt stays static. The precise form (scoping the exception inside the judge prompt) is a later upgrade.
- [ ] `extract.py`: `extract(llm, text)` substitutes `waivable_dimensions=overrides.waivable_text()` and calls `normalize(result, text)`. `normalize(e, text="")` also keeps only overrides whose whitespace-collapsed, lower-cased `quote` is a non-empty substring of the same-normalised `text`. `# DECISION:` explain the code-side quote check (an over-eager waiver is the main risk).
- [ ] Run `.venv/bin/python -m pytest -q tests/test_overrides.py tests/test_stages.py`: all pass.

### Task 2: Prompts and the prompt stack (opus)
**Files:** modify `storyteller/prompts/extract.md`, `storyteller/generate.py`. Tests: `tests/test_prompts.py`, `tests/test_stages.py`. **Store:** `store/13_feedback_prompts/`.

**Interfaces:** consumes Task 0 types. Produces the `$waivable_dimensions` placeholder, `make_spec` copying the new fields, and the preferences block.

- [ ] Write failing tests:
  - `test_prompts.py::test_extract_explains_follow_up_feedback`: extract.md mentions `preferences`, `overrides`, `quote`, `$waivable_dimensions`, and says later feedback wins over earlier text.
  - `test_prompts.py::test_extract_never_lists_safety_as_waivable`: `"safety"` not within the overrides section, *or* the prompt says safety can never be waived. Pick one and assert it.
  - `test_prompts.py::test_all_templates_substitute`: already substitutes with dummy kwargs. Make sure `waivable_dimensions` is supplied.
  - `test_stages.py::test_make_spec_carries_preferences_and_overrides`.
  - `test_stages.py::test_preferences_block_sits_on_top_of_the_prompt`: `build_system_prompt(spec(preferences="Make the dragon funnier."))` starts with the preferences header and contains the text **before** `BASE`. It also contains a line saying these wishes win over everything below **except the Safety rules**.
  - `test_stages.py::test_no_preferences_means_prompt_unchanged`: the existing exact-string tests still pass (no block, no extra blank lines).
  - `test_stages.py::test_revise_keeps_preferences_on_top`: `revise_story` system prompt starts with the preferences block.
- [ ] Run and watch them fail.
- [ ] `extract.md`: add a section **"Follow-up feedback"**. The text may be one request, or an original request followed by numbered changes asked for after hearing the story. Fill every field for the story as it should be now: later changes win over earlier ones and over the original request, and a correction updates the field it corrects ("her name's actually Mia" → that character's name becomes Mia). Then add two field descriptions:
  - `preferences`: the user's own instructions on how the story should be told or changed (style, tone, ending, length, things to add or remove), in plain imperative sentences, all still-standing ones, newest last. Null when the request only names what the story is about. Don't repeat what already went into characters/setting/premise/worry/listener/category.
  - `overrides`: only when an instruction directly conflicts with one of the story rules below. Copy the user's exact words into `quote`, name the rule in `dimension`, and say the narrow exception in `allow`. Empty list when nothing conflicts. A wish that merely *could* bend a rule is not a conflict. Give several phrasings that map to `wind_down` (cliffhanger, "to be continued", "leave it hanging") and one non-conflict ("an exciting adventure" → no override). Then add `$waivable_dimensions`. State that the safety rule can never be overridden and is not in the list.
  - Keep the "no concrete story examples" rule satisfied (`test_no_concrete_story_examples_leak_into_prompts`).
- [ ] `generate.py`: `make_spec` copies `preferences`, `overrides`. `build_system_prompt` prepends, when `spec.preferences`:
  ```
  ## The listener's wishes (these come first)
  Where these wishes conflict with anything below, follow these wishes, except the Safety rules, which always apply.
  {preferences}
  ```
  as the first part, joined with `\n\n` like the rest. Keep it in Python (not a new .md) so tests can pin the exact text. `# DECISION:` explain why Safety is excluded.
- [ ] Run `.venv/bin/python -m pytest -q tests/test_prompts.py tests/test_stages.py`: all pass.

### Task 3: Outer feedback loop, CLI, end-to-end tests (opus)
**Files:** modify `storyteller/pipeline.py`, `main.py`. Create `tests/test_feedback_flow.py`, `tests/test_cli.py`. **Store:** `store/14_feedback_loop/`.

**Interfaces:** consumes `apply_overrides` (Task 1) and `make_spec` / `build_system_prompt` (Task 2). Produces `conversation_text`, `give_feedback`, and `run(...).session`.

- [ ] Write failing tests in `tests/test_feedback_flow.py`. Reuse the tag-word `FakeLLM` style of `tests/test_pipeline.py`. The fake extraction is a callable that reads the conversation text and returns the matching Extraction (a dragon story → `premise="a dragon"`; once "funnier" appears → `preferences="Make the dragon funnier."`; "cliffhanger" → an override on wind_down with that quote; "Mia" → the girl's name becomes Mia). Tests:
  - `test_initial_run_returns_a_session_with_the_delivered_story`
  - `test_make_the_dragon_funnier_end_to_end`: run, then `give_feedback(session, "make the dragon funnier")`. Stage order is `gate, extract, revise, judge`. The revise call's user message has the delivered story and the feedback. Its system prompt starts with the preferences block. The gate and extract user messages contain both the original request and the feedback. The result story is the new tag, and `session.feedback == ["make the dragon funnier"]`.
  - `test_feedback_never_calls_generate_or_options` (vague original included: the old `idea` carries over to the new spec).
  - `test_cliffhanger_waives_wind_down_and_delivers`: judge fails wind_down on every version. Status is story, no revise round receives a wind_down bullet, the trace's last version has `waived == ["wind_down"]`, and `config.HARD` still contains wind_down.
  - `test_waiver_does_not_hide_other_hard_failures`: cliffhanger waiver, judge fails wind_down + consistency → revision feedback lists consistency only, and the loop runs while consistency fails.
  - `test_full_rubric_runs_on_every_feedback_revision`: every judge call in a feedback turn is asked all applicable dimensions (check `llm.schemas` judge field set).
  - `test_safety_failure_is_never_waived`: extraction returns a smuggled `model_construct` safety override, and the judge fails safety → canned message.
  - `test_unsafe_draft_after_feedback_shows_canned_message_and_keeps_session`
  - `test_unsafe_feedback_is_rejected_by_the_gate_and_session_kept`: stages are `["gate"]` only.
  - `test_feedback_revision_is_not_discarded_by_the_guard`: old story passes everything. The feedback revision fails consistency, and the next fixes it → the delivered story is the latest tag, never the old one.
  - `test_feedback_turn_respects_max_rounds_and_returns_best_available`: a non-safety hard failure that never clears → MAX_ROUNDS revisions after the feedback revision, status story.
  - `test_revisions_start_from_the_kept_draft`: inside a feedback turn, each revise input is the guard's kept version.
  - `test_name_correction_updates_spec_and_judge_context`: "her name's actually Mia" → `session.spec.characters` has Mia, and the judge system prompt context includes Mia.
  - `test_multiple_feedback_turns_accumulate`: two turns. The second extract and gate see both feedbacks in order, and the preferences reflect both.
  - `test_later_feedback_can_take_back_a_waiver`: turn 1 cliffhanger (waived), turn 2 "actually give it a calm, sleepy ending" → extraction has no override, and wind_down failing is now hard again (revision feedback lists it).
  - `test_upfront_ask_uses_the_same_path`: `run("a dragon story that ends on a cliffhanger")` → wind_down waived on the first run too.
  - `test_each_feedback_turn_writes_its_own_trace`: the trace has `feedback` and `turn` keys plus waived lists.
  - `test_budget_exceeded_during_feedback_keeps_session`.
  - `test_conversation_text_is_the_bare_request_without_feedback`, plus `..._numbers_feedback_newest_last`.
- [ ] `tests/test_cli.py`: monkeypatch `builtins.input` and `pipeline.run` / `pipeline.give_feedback`.
  - `test_cli_quits_on_empty_or_quit_words` (each of `""`, `"q"`, `"quit"`, `"exit"`, `"done"`, any case/whitespace).
  - `test_cli_feeds_feedback_until_quit`: two feedbacks then quit → give_feedback called twice with the threaded session, and both stories printed.
  - `test_cli_no_feedback_prompt_without_a_story` (rejected run → no prompt).
  - `test_cli_keeps_offering_feedback_after_a_rejected_feedback`.
- [ ] Run and watch them fail.
- [ ] Implement in `pipeline.py`:
  - `conversation_text(request, feedback)`: returns `request` unchanged when feedback is empty. Otherwise:
    ```
    Original request: {request}
    Changes asked for after hearing the story (newest last):
    1. {f1}
    2. {f2}
    ```
  - `_judge(llm, spec, text, request) -> Evaluation` = `apply_overrides(await evaluate(...), spec.overrides)`. Every evaluate call in the pipeline goes through it.
  - `write_and_revise(llm, spec, trace, request, previous: DraftVersion | None = None, change: str | None = None)`: round 0 is `write_story` when `previous` is None, else `revise_story(llm, spec, previous.text, f"- The listener asked for this change: {change}")` (`feedback_sent` set to that). The rest is unchanged. `# DECISION:` round 0 of a feedback turn is the new baseline and is never guard-compared with the delivered story, because the delivered story no longer meets what the user asked for.
  - `_run(request, llm, trace, session: StorySession | None = None, feedback: str | None = None)`: one path. `text = conversation_text(request, prior + [feedback])` → gate(text) → extract(text) → make_spec. If session: copy `idea` from `session.spec` and skip options. Else: options if vague. Then write_and_revise with previous/change, and pass `text` as the judge's `request`. On status story, return `session=StorySession(request, feedback=all, spec, story=final)`. On rejected/safety_message, return the **incoming** session unchanged (None on a first run).
  - `run(request, llm=None)` and `give_feedback(session, feedback, llm=None)` share one wrapper (trace/budget/usage), so `BudgetExceeded` during feedback returns status error with the incoming session. Trace adds `feedback` (list) and `turn` (= len(feedback)).
- [ ] `main.py`: after a story, loop: `input("\nAnything to change? Tell me, or press Enter to finish: ")`. Quit on blank or `q/quit/exit/done`. Otherwise call `give_feedback`, print the story or message, keep the latest non-None session, and continue. `--verbose` details are printed per turn. Remove `TODO(user-feedback)`.
- [ ] Run the full suite: everything passes.

### Task 4: Docs (haiku)
**Files:** `docs/ARCHITECTURE.md`, `docs/OPEN_QUESTIONS.md`, `README.md` (usage section only). **Store:** `store/15_feedback_docs/`.
- [ ] ARCHITECTURE: add the outer feedback loop to the flow diagram, and a short "Feedback turn" section (conversation re-extraction, preferences on top, apply_overrides after the judge, round 0 = feedback revision).
- [ ] OPEN_QUESTIONS: decisions (coarse waiver, quote check, Safety excluded from preference precedence, feedback revision as baseline). Deferred: precise waiver inside the judge prompt; the gate seeing the whole conversation, so off-topic feedback passes relevance. Eval backlog: over-eager overrides, and whether preferences are honoured.
- [ ] README: a feedback example in the CLI usage.

### Task 5: Whole-branch review (orchestrator + opus reviewer)
**Store:** `store/16_feedback_review/`. Full suite. A fresh reviewer reads the diff against the Requirements list in `store/11_feedback_contracts/CONTEXT.md` and reports any invariant without a test.

## Parallel waves
| Wave | Tasks | Model |
|---|---|---|
| 1 | Task 0 | orchestrator |
| 2 | Task 1 ‖ Task 2 ‖ Task 3 (disjoint files; Task 3 codes against the Shared interfaces and goes green once 1 and 2 land) | sonnet ‖ opus ‖ opus |
| 3 | Task 4 ‖ Task 5 | haiku ‖ opus |

## Live-run cost (not run without the author's OK)
A smoke test of one request + two feedback turns is about 3 × (gate + extract + ≤4 × (revise + judge)) ≈ 30 Haiku calls ≈ $0.01–0.02.
