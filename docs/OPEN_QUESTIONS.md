# Open questions and decisions

Every `# DECISION:` marker in the code, the spec overrides, the simplification choices, the deferred features and the eval backlog. Written for the author to confirm or overturn.

## The simplified first version (2026-11-12)

The first build implemented the full brief: three drafts for vague requests, a premise brainstorm, LLM pairwise comparison in both orders, cross-draft selection and a cozy fallback draft. That build is preserved on branch `skeleton_extensive`. The author chose to start smaller and let evals decide where complexity is worth adding back. What changed:

- **One draft per request.** No depth/breadth branch and no brainstorm. For a request with no premise, one small call asks for 5 story ideas and code picks one at random (added 2026-11-13, see "Story ideas for requests with no premise" below).
- **The gate and extraction stay two separate calls.** A request that fails the gate stops before extraction is paid for.
- **No LLM comparison anywhere.** Keep-better is a code-only regression guard (see `pipeline.keep_better`):
  - Only hard failures count. Soft failures play no part.
  - Safety outranks the count, so a safe version is never replaced by an unsafe one.
  - Otherwise the version with fewer hard failures wins, and a tie goes to the new version.
- **Revisions start from the kept version**, in full, under the same system prompt as the first draft plus the revise rules (author confirmed "option A").
- **No fallback draft.** If the final version fails safety, the canned message is shown instead.
- **No `mood` field.** The category carries the tone (silly = funny, cozy = calm, adventure = exciting). Any tone it doesn't cover goes into the premise in a few words, never as invented events. The rubric item became `faithfulness_premise`.
- **The gate returns two checks.** `safety` and `relevance`, each `Check {evidence, passed}`, in one call. Both must pass. The rejection message uses the failed check's evidence (safety first if both fail). `Check` is separate from the judge's `Verdict` because a request has no "fix".

## Story ideas for requests with no premise (2026-11-13)

Tested as condition B in `docs/findings/independent_thinking_experiement.md` (10 vague requests, one run each): letting the writer invent its own idea converged on one template, while a random pick from 5 model-made options gave 10 distinct premises. Changes from the tested version:
- **Any category, not only cozy.** The options prompt asks for the request's category ("a silly, funny bedtime story", ...), or "a bedtime story" when there is none; the tested prompt always said "calm".
- **Triggered by a missing premise, not by "nothing named".** "Alice and her cat Bob" has characters but no plot; without ideas the writer would invent one and likely converge as vague requests did. The 5 ideas keep the named characters and setting, and the pick fills only the empty fields. Not yet run live for named-but-no-premise requests.
- Known weak spot: the experiment's option lists repeated across requests (Pip in 9 of 10 lists, a moonlit woodland animal as option 1 in all 10). Named characters make this matter less; fully empty requests still see it.

## Minification (2026-11-13)

Simplified so each rule lives in one place and the system can be stated in three rules (see `ARCHITECTURE.md`):
- **`worry` removed.** A child's fear is the premise ("scared of the dark") with category comfort. `normalize`'s "comfort needs a worry" rule is gone; the extract prompt already says "no worry, no comfort".
- **`gentle_lesson` removed.** Categories are adventure, silly, comfort, cozy. Moral-choice requests ("a story about sharing") now get the premise and no category.
- **No cozy fallback.** `FALLBACK_CATEGORY` and `make_spec` are gone: no category means the base prompt alone, even for "tell me a story" (the 5 ideas give it a plot). Untested live; the base prompt's bedtime shape and the judge's `wind_down` check keep endings calm.
- **One check per condition.** "Is there a premise?" is checked only in `pipeline._run`; "is there a category?" only where a category prompt is loaded (writer prompt, judge skip). `StorySpec` is the extraction plus the picked idea.

## User feedback (2026-11-13)

After a story is delivered, the user can ask for changes, and each change is a turn on the same story (flow in `ARCHITECTURE.md`, "Feedback turn"). Decisions:
- **Coarse override.** An override clears a whole rubric dimension, not one check inside it. The judge prompt stays static and does not learn about overrides (`overrides.apply_overrides`). Alternative: a precise override inside the judge prompt (deferred).
- **Quote check in code.** An override counts only if its `quote` appears in the conversation text, compared case- and whitespace-insensitively, whole words only (`extract.quoted`). The prompt asks for exact spelling, so the code is looser than the prompt. Alternative: case-sensitive matching (open, see the eval backlog).
- **Safety is outside the feedback's precedence and is never overridden.** The feedback block beats base, category and variables, but not the Safety rules (`generate.py:7`). Alternative: no exception, rejected because it invites a writer/judge conflict on safety.
- **Framed as "feedback on this story"**, not anyone's wishes (`generate.PREFERENCES_HEADER`): the person asking may be a parent or a child. (Earlier wording, "the parent's wishes", was dropped in review.)
- **A change that gets an override also goes into `preferences`**, so the writer still follows it. Tone changes from feedback go to `preferences`; tone words in the original request keep the old tone-to-premise/category rule.
- **The feedback revision starts from the delivered story** (`pipeline.write_and_revise`). Its round 0 is never guard-compared with the delivered story. Alternative: let the guard keep the old story, rejected because it would silently drop the user's change.
- **Rule 3 runs on the first turn only.** A feedback turn keeps `idea` and never asks for ideas again (`pipeline._run`), even if the conversation still has no premise. The idea fills only empty fields, so feedback that adds a premise replaces the idea's situation. Alternative: re-pick, which would throw the story away.
- **Budget exhaustion keeps the session** (`pipeline._turn`): `BudgetExceeded` on a feedback turn returns the incoming session.
- **Always a session** (author, review step 2). The conversation starts as a session with the request; whether a turn is a feedback turn is `feedback is not None`, not whether a session exists. Trade: `StorySession.spec`/`story` are optional until the first story, so `give_feedback` checks for a story. Terminology: "override" is the one word for a rubric check feedback switches off (`OverridableCheck`, `config.OVERRIDABLE_CHECKS`, `Evaluation.overridden`); "waive" was dropped.
- **Failed changes are not recorded.** On a rejected, safety-blocked or errored turn, the session is the incoming one.
- **Quitting is explicit** (author request). The prompt says "type exit (or press Esc) to quit". Enter on an empty line asks again and never calls the pipeline. Esc quits without Enter: on a terminal `ui.read_feedback` reads keys one at a time (cbreak mode); a lone Esc quits, arrow-key sequences are ignored, Backspace works. Elsewhere (pipes, tests, Windows) it falls back to `input()`, where typing exit still quits.
- **Output** (author request): all presentation lives in one root file, `ui.py`; `main.py` is only the flow, and nothing in `storyteller/` imports `ui`. A banner and a request prompt open the session; each story unrolls inside an ASCII scroll (`ui.format_story` + `ui.unfold`, 76 columns, centred title, Markdown `**`/`#` stripped) under a caption ("Your story", "Revised · <feedback>"); a 5-line night-sky scene (`ui.sky_frame`, `ui.with_spinner`) plays while a story is written or revised; messages are set apart with ✦; quitting says goodnight. Colour and animation run only on a terminal; `NO_COLOR` / `NO_ANIMATION` turn them off.
- **No category carryover** (ported 2026-11-13 onto the three-rule skeleton). The old build kept the category when feedback left it unclear, but that only protected the cozy fallback, which is gone. Re-extracting the whole conversation is the one source of truth; feedback can change the category ("make it funnier" → silly).
- **Override quotes match whole words** (`extract.quoted`): `end` does not match inside `friend`.
- **The CLI treats a plain "no" as quit** (`main.is_quit`: no, nope, no thanks, nothing, that's all, stop), so a happy user never pays for a rewrite. An `LLMError` on a feedback turn prints a retry line and keeps the last good story. Ctrl-C ends quietly.
- **The loop protects the parent's change** (live finding, `store/17_feedback_live_smoke`). The coarse override covered only `wind_down`, but `category_checks` and `story_arc` also expect a calm ending, and their fixes ("make the ending sleepy") undid an overridden cliffhanger. Two code-only fixes, both active whenever the spec has `preferences` or it is a feedback turn (so up-front asks get them too):
  - The guard breaks ties on hard checks with `faithfulness_premise` (`pipeline.PROTECT_FEEDBACK`), so a revision that drops the change can't replace one that kept it. Hard checks still come first.
  - Every loop revision's feedback ends with `feedback.KEEP_FEEDBACK` ("Keep the earlier feedback on this story: …; if a change above would undo any of it, keep the feedback").
  - Live re-run: the guard delivered the cliffhanger. The keep-wishes line did *not* hold when the judge's fix named the cliffhanger outright ("remove the … cliffhanger"), so all 3 loop rounds were wasted on the same conflicting fix. The precise override (exceptions in the judge's context) is the real fix. A code-side stop on repeated identical feedback would at least cap the waste.
  - **Precise override now built** (author-approved after the re-run). `judge._rubric_context` appends `judge.EXCEPTIONS_HEADER` plus one `- dimension: allow` line per active override (never safety, via `overrides.active`). No dimension may fail or "fix" the exception. `judge.md` is unchanged, and a request without overrides gets a byte-identical judge prompt. The coarse guard override stays as a backstop.
  - **Stop on a dropped change.** When the guard rejects a revision only because it lost the parent's change (tied on hard checks, worse on `faithfulness_premise`), the loop stops (`guard[-1].stopped`), because the next round would resend identical feedback. A rejection for a new hard failure still retries (`test_the_walkthrough_example`).
  - Live check: the cliffhanger turn passed in round 0 (4 calls, $0.0025, against 10 calls, $0.0085 before). The judge still failed `wind_down` itself despite the exception, and the coarse override absorbed it, so both layers stay.
  - Limitation: `faithfulness_premise` is skipped when the spec has no premise ("tell me a story" + "end on a cliffhanger"). There, only the keep-wishes line protects the change. Unskipping it when preferences exist would mean changing `judge.skipped_dimensions` (the judge is frozen for v1).
- **Deferred:** a per-conversation cost cap (today `MAX_RUN_COST_USD` caps each turn, because each turn gets a fresh client); the gate (unchanged) judges the whole conversation text, so unsafe feedback is caught, but off-topic feedback ("what's 2+2?") can still pass relevance because the original request around it is a story request.

## DECISION entries (in code)

1. **`storyteller/llm.py:33` strict schema.** Chosen: post-process pydantic's JSON schema ourselves (`additionalProperties: false`, all fields required, drop `default`). Alternative: an SDK helper, which ties us to an SDK internal.
2. **`storyteller/llm.py:73` retry policy.** Chosen: 4xx other than 429 fails immediately as `LLMError` (this includes a schema the API rejects). 429, 5xx, connection and validation errors retry, waiting `2**attempt` seconds. Alternative: retry everything.
3. **`storyteller/llm.py:52` client construction.** Chosen: `base_url` passed explicitly, so the SDK's `ANTHROPIC_BASE_URL` env var can't redirect the key; `max_retries=0`, so the SDK doesn't retry inside our own loop. Cost is computed from token counts at the list price in `config.py`, since the API returns no dollar cost.
4. **`storyteller/config.py:10` fixed endpoint and model.** Chosen: `BASE_URL` and `MODEL` are not env-overridable, so a stray shell variable can't redirect the key or swap the model. Alternative: allow overrides with a prefix.
4a. **`storyteller/llm.py:118` refusals.** Chosen: `stop_reason == "refusal"` raises `LLMError` at once, after recording usage. Alternative: retry, paying up to 3 times for a likely repeat.
5. *(removed 2026-11-13: the comfort-without-worry rule went with the `worry` field.)*
6. **`storyteller/judge.py:59` failures computed in code.** Chosen: failures come from each dimension's `passed` flag, never the judge's own summary, and skipped dimensions are dropped. Alternative: trust the judge's summary.
7. **`storyteller/pipeline.py:41` guard puts safety first.** Chosen: compare `(fails safety?, number of hard failures)`. Alternative: count only, where a version failing only safety (1) would beat one failing two other hard checks (2).
8. **`storyteller/pipeline.py:144` budget exhaustion.** Chosen: `BudgetExceeded` becomes a friendly message with `status="error"`, and the trace is kept. Other errors (`LLMError`, missing key) still raise to the CLI.

## Other choices (no marker in code)

- **Judge checks are shown to the writer.** The category files include their `## Judge checks` section in the generation prompt too, so the writer sees what it will be judged on. Alternative: strip that section for generation.
- **Other hard failures at the cap still show the story.** For example, a story still failing wind_down after 3 revisions is shown; only a safety failure is withheld.
- **`--baseline` sends no system prompt**, exactly like the original `main.py`.
- **One client per run**: `pipeline.py` makes a fresh `AnthropicClient` (`storyteller/llm.py`) each turn, so the budget guard is per run. A backend change touches `llm.py` and those two lines of `pipeline.py`.

## Model access

- The brief is followed as written: the `anthropic` SDK, the Anthropic API (`https://api.anthropic.com`), model `claude-haiku-5-5`, key `ANTHROPIC_API_KEY`. (The development branch `skeleton` went through OpenRouter instead; this branch is the Anthropic-only submission.)
- No `temperature` is sent; current models reject it. Structured output uses the API's JSON-schema mode (`output_config.format`), validated with pydantic. Thinking is disabled.

## Deferred: what I'd build next (candidates, let evals decide)

Each of these is implemented on `skeleton_extensive` unless marked otherwise.

- **Breadth for vague requests:** a premise brainstorm that writes three distinct drafts (cozy, adventure, silly) and picks one.
- **LLM pairwise comparison**, asked in both orders to cancel position bias, to break ties between versions and to select across drafts.
- **A safety fallback draft:** one fresh cozy draft before giving up with the canned message (would go in `pipeline._run`, step 5).
- **Critique check** (not built anywhere): an open-ended "what would a parent dislike?" pass after the rubric (would go in `pipeline.write_and_revise`, after the round-0 judge).
- **Edgy-request policy** (not built anywhere): what the gate should do with "a dragon who eats villagers" (would go in `gate.py` / `prompts/gate.md`).
- **An eval harness** (not built anywhere): run a request set through `pipeline.run` and `pipeline.baseline`, judge both, and compare.

## Accepted limits

- **`finish_reason == "length"` is not checked.** A story cut off at `MAX_TOKENS=2000` would be accepted (unlikely: about 600 words ≈ 800 tokens).
- **`latency_budget_exceeded` is recorded but nothing acts on it.**
- **`requirements.txt` is unpinned.**

## Eval backlog (check when building the eval set, not before)

1. **The judge may be too lenient.** In the 3 sample runs (`runs/samples/`, 2026-11-12, made with the extensive build), 8 of 9 drafts passed every rubric dimension on the first try. Possible causes: good drafts, a rubber-stamping judge, or a rubric that's too easy to satisfy. How to check:
   - Hand-label a few drafts and measure agreement with the judge.
   - Feed the judge deliberately flawed stories (a cliffhanger ending, a contradiction, a scary detail, a missing named character) and count how many it catches.
   - Compare pass rates per dimension.
   - Where to tune: `storyteller/prompts/judge.md`, the category `## Judge checks` sections, and `storyteller/judge.py`.
2. **Extraction of family references: fixed and confirmed live (2026-11-12).** "my son is scared of the dark" now extracts `characters: []`, `worry: "scared of the dark"`, `category: comfort`.
3. **Sample traces re-run with the simplified version (2026-11-12).** `runs/samples/` now holds the three requests run through this version: $0.006 in total, 12–22 s each, 4–6 calls each. The extensive build's samples are on `skeleton_extensive`.
4. **Vague requests now get a random pick from 5 model-made options.** Check variety over repeat runs of the same request, whether the theme steer stops the option lists repeating across requests (names such as Pip come from the options call, which has no name guidance), and that non-cozy vague requests ("a silly story") get ideas of that category.
5. **Tone without a mood field.** Check that requests like "a slightly spooky owl story" or "an exciting space story" keep their tone through the premise and category.
6. **The writer undershoots the length target.** First drafts were 435, 375 and 476 words against a 600-word target (400–900 accepted). One draft failed the length check and was fixed by a revision. Consider raising the target in `base.md`, or watch whether this costs revision rounds.
7. **Over-eager overrides (feedback, not run live).** The extract prompt's false-positive behaviour is untested with Haiku. Expect `overrides: []` for "an exciting adventure", "make it funnier" and "scarier", and a `wind_down` override for "a cliffhanger" and "to be continued".
8. **Whether preferences are honoured.** After a change such as "make it funnier" or "a cliffhanger", check the revised story shows it, and that a wish that would break safety never does.
9. **Judge request display on feedback turns.** The judge's `request` is the multi-line conversation text, printed with `!r` in `judge._rubric_context`, so newlines show as `\n`. `judge.py` is frozen by the plan, so check in a live run whether this confuses the judge.
