# Skeleton Spec

This is the original setup brief for the take-home. It is kept verbatim below,
except for the **overrides** listed first. Where an override conflicts with the
brief, the override wins.

## Overrides (from the author, after the brief was written)

> **On branch `anthropic_invocation` (the submission), overrides 1 and 2 are withdrawn.** It uses
> the brief's own choice: the `anthropic` SDK, key `ANTHROPIC_API_KEY`, model `claude-haiku-5-5`,
> structured output via `output_config.format`. Overrides 1 and 2 still describe the development
> branch `skeleton`.

1. **Model access goes through OpenRouter, not the `anthropic` SDK.** Use the
   official `openai` Python SDK (`AsyncOpenAI`) pointed at
   `https://openrouter.ai/api/v1`. The model is still Claude Haiku 5.5, with
   OpenRouter id `anthropic/claude-haiku-5.5`. The key comes from the env var
   `OPENROUTER_API_KEY`, not `ANTHROPIC_API_KEY`.
2. **Structured output** goes through OpenRouter's
   `response_format={"type": "json_schema", ...}`, which this model supports
   (verified 2026-11-11 against `GET /api/v1/models`). The output is then
   validated with pydantic. The model does **not** support `temperature`, so
   never send it.
3. `main` holds only the original `README.md` and `main.py`, unchanged. All
   work goes on branch `skeleton`.
4. **Simplified first version (2026-11-12).** `skeleton` implements a deliberately
   smaller version: one draft per request (no brainstorm), no LLM comparison (a
   code-only regression guard instead), no fallback draft, no `mood` field (tone
   goes into category or premise), and a gate returning separate `safety` and
   `relevance` checks. The full brief as first built is on branch
   `skeleton_extensive`. Details: `docs/OPEN_QUESTIONS.md`.

---

## Original brief (verbatim)

You are setting up the first working skeleton of a take-home assignment for Hippocratic AI. Work in this repo on a new branch named `skeleton`. Commit in small, logical steps with clear messages. Never commit secrets.

### The assignment (summary)
Take a simple bedtime story request and use prompting to tell a story appropriate for ages 5-10. Requirements: incorporate an LLM judge to improve story quality; provide a block diagram of the system (prompt flow, interaction between user, storyteller, judge and other components). The original skeleton is `main.py` (it uses the legacy `openai.ChatCompletion` API; replace that).

### Hard constraints

* Model: Anthropic Claude Haiku 5.5, API model id `claude-haiku-5-5`, for EVERY LLM call (storyteller, judge, extraction, gate, comparisons). This is a recruiter instruction that supersedes GPT-3.5 in the README. Use the official `anthropic` Python SDK (Messages API). Check the current SDK docs (e.g. via Context7) for exact syntax, structured/JSON output via tool use, and async usage; don't rely on memory. **[overridden: see Overrides 1–2]**
* API key from the environment variable `ANTHROPIC_API_KEY`. Add `.env.example`, add `.env` to `.gitignore`. Never hardcode or commit a key. **[overridden: `OPENROUTER_API_KEY`]**
* Python, minimal dependencies (`anthropic`, `pydantic`, optionally `python-dotenv`). Use `asyncio` so parallel drafts run concurrently. **[overridden: `openai` instead of `anthropic`]**
* The author must be able to explain every line, so favor readable, well-named, lightly commented code over cleverness. No frameworks (no LangChain etc.).

### Architecture (implement this flow)

1. Input gate (one LLM call, structured output): `{safe: bool, relevant: bool, reason: str}` on the user's REQUEST. If not safe or not relevant to a bedtime story, return a friendly message with the reason and ask for a new request. Note in code: the gate judges a request, not a story; it should not reject requests that could be reshaped into something bedtime-appropriate. Edgy-but-valid requests (e.g. "a dragon who eats villagers") are a known open case: leave a clear TODO, don't design it.
2. Pre-processing (one LLM call, structured output): extract `characters: list[{name: str|None, role: str|None}]` (role = species or relationship, e.g. "Alice's cat"; personality traits not stored yet), `setting: str|None`, `premise: str|None`, `mood: str|None`, `worry: str|None`, and `category: one of [adventure, silly, comfort, gentle_lesson, cozy] | None`. Rules: never invent a premise for a vague request (leave it null). `comfort` only if the request contains a worry. Moral-dilemma requests map to `gentle_lesson`. Null/unclear category -> `cozy` (the fallback). Routing never rejects.
3. Breadth vs depth branch (code):
   * premise present -> DEPTH: one draft, in the extracted category (or cozy).
   * premise null -> BREADTH: one "premise brainstorm" LLM call that returns 3 distinct premises while seeing all three at once. Any named characters and setting are passed into the brainstorm and must appear in every premise; if none were named, the model invents them per premise. If category is known, all 3 premises use that category. If category is unknown, use the FIXED set cozy, adventure, silly (one premise each); exclude comfort (needs a worry, would invent a fear) and gentle_lesson (unrequested lessons risk preachiness). Each premise then becomes its own draft. Do NOT rely on temperature for diversity.
4. Generation (storyteller): system prompt = shared BASE prompt + CATEGORY bundle + VARIABLE lines (one line per variable, only if present).
   * BASE: audience 5-10, simple vocabulary and short sentences, read-aloud friendly; no violence/real danger/imitable unsafe behavior; final third slows down to a calm, safe, quiet ending with no cliffhanger; target length (configurable).
   * CATEGORY bundles (first-pass, keep each in its own prompt template file): a story structure (ordered beats), do's/don'ts, and category-specific judge checks.
      * adventure: clear goal, journey with 2-3 obstacles, return home; must still wind down.
      * silly: one ridiculous wish/habit, escalating attempts (rule of three), playful language/sound words, harmless surprise, winds down; avoid humor from meanness or embarrassment.
      * comfort: character shares the child's worry, worry taken seriously (never "nothing to be scared of"), trusted figure, one gentle coping strategy a real child could use, worry shrinks, ends safe and sleepy; avoid making the feared thing real or fighting it, avoid stated morals.
      * gentle_lesson: character holds a mistaken belief or makes a small choice, sees a gentle consequence, discovers the realization themselves; avoid preachiness and stated morals.
      * cozy: low-plot, soothing routine/ritual structure, gentle realization, very calm; needs nothing from the request (fallback).
5. Evaluation per draft:
   * Length: code check (configurable word range).
   * Rubric judge: one LLM call, stateless (fresh call, full rubric each time), structured output. For EACH dimension the judge writes evidence first, then a pass/fail verdict, then (if fail) a specific fix pointing at where in the story. Never tell the judge a draft is a revision.
   * HARD dimensions: safety; bedtime wind-down; faithfulness to NAMED characters + setting (skip if none named); consistency (no contradictions in names, facts, or the story world's own rules).
   * SOFT dimensions: age-appropriate language; story arc (setup, problem/goal, attempt, resolution); engagement (stakes, agency, specific vivid details); faithfulness to premise + mood (skip if null; mood is reshaped for bedtime, so judge "honored in a bedtime-appropriate way"); category-specific checks; length (code).
   * No overall score. Pass/fail per dimension.
6. Revision loop per draft (drafts run in parallel):
   * If everything passes -> stop (no further checks or comparisons for that draft; keep its verdicts).
   * Feedback priority: if any HARD check fails, send only the hard failures; otherwise send the soft failures.
   * Revise, don't regenerate: revision call gets the previous draft + feedback + the original constraints (base prompt, category bundle, variables), and is told to change only what the feedback asks and keep everything else.
   * After each revision, keep the better of (previous, new): first prefer the one passing more HARD checks; if tied, pairwise holistic comparison ("which would a parent rather read to their child at bedtime?"), run in BOTH orders to cancel position bias; disagreement -> keep previous. Next revision starts from the kept draft.
   * Cap: `MAX_ROUNDS` = maximum number of revisions per draft (default 3, configurable). Also log wall-clock time per stage; there's a ~60s latency budget to tune against later.
7. Selection across drafts (breadth case, after all loops finish): filter out drafts still failing any hard check, then compare every pair of survivors with the SAME pairwise function used in step 6 (both orders, all calls in parallel), count wins. Tiebreak: fewer soft failures; if still tied, keep the earlier draft. With a single draft there is no selection step.
8. Behavior at the cap:
   * If SAFETY fails on every final draft: never show it. Fallback (first pass, mark TODO): one fresh cozy draft through one evaluation; if it still fails safety, return a friendly canned message.
   * If only other hard checks fail: return the best available draft (fewest hard failures, then pairwise).
9. Output: print the final story.

### Deferred (do NOT build, leave TODOs/hooks)

* Critique check (open-ended "what would a parent dislike?"): deferred until evals show the rubric misses things.
* User feedback after the story / interactivity.
* Edgy-request reshaping policy.
* Eval harness. BUT support it now:
   * a `baseline(request)` function: single call to the same model with just the request (the original main.py behavior);
   * a JSON trace per run written to `runs/` (gate result, extraction, branch taken, every draft version, every judge verdict with evidence, feedback sent, comparisons, final choice, timings, token usage if available). Keep the pipeline callable as a function so an eval script can import it.

### Structure (suggested, adjust if cleaner)

* `main.py` (CLI entry: prompts for a request, runs pipeline, prints story; `--baseline` flag; `--verbose` prints a short trace summary). Keep the original docstring slot for "what I would build next" but leave it for the author to write.
* `storyteller/` package: `llm.py` (client wrapper, structured-output helper, retries), `gate.py`, `extract.py`, `brainstorm.py`, `generate.py`, `judge.py`, `compare.py`, `pipeline.py`, `config.py`, `trace.py`, `prompts/` (base, one file per category, judge rubric, gate, extraction, brainstorm, revision, comparison).
* `tests/` with unit tests for pure logic only (routing/branching, feedback priority, keep-better rule, selection incl. win counting and tiebreak, cap behavior) using a fake LLM client. No live API calls in tests.
* `docs/ARCHITECTURE.md` with Mermaid diagrams: (1) end-to-end flow: user, gate (reject path back to user), pre-processing, breadth/depth branch with the premise brainstorm, the per-draft loop as one box, selection, safety check, safety fallback exit, output, and the run trace; (2) inside one draft's loop: prompt assembly, storyteller, evaluation (length code + rubric judge), feedback builder, revision, keep-better comparison, cap. Color LLM calls and code steps differently. Show the rubric as a small box in the main flow and expand it in a side table (hard vs soft, LLM vs code). This is a draft the author will refine.
* `requirements.txt`, `.env.example`, updated run instructions.

### Working rules

* Get an end-to-end path working first (depth case), then breadth, then the cap/fallback rules, then tests and docs.
* If something in this spec is ambiguous or seems wrong, pick the simplest reasonable option, mark it `# DECISION:` in code, and list it in `docs/OPEN_QUESTIONS.md` rather than inventing a big feature.
* If you have an API key available, run 2-3 sample requests (one vague like "tell me a story", one with characters like "Alice and her cat Bob", one with a worry like "my son is scared of the dark") and save their traces; otherwise make sure everything runs with the fake client.
* Commit on `skeleton` and push the branch; open a draft PR summarizing what's done, what's stubbed, and the `# DECISION:` list. Do not merge into main.
