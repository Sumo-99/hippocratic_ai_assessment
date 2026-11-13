# Open questions and decisions

Every `# DECISION:` marker in the code, the spec overrides, the simplification choices, the deferred features and the eval backlog. Written for the author to confirm or overturn.

## The simplified first version (2026-11-12)

The first build implemented the full brief: three drafts for vague requests, a premise brainstorm, LLM pairwise comparison in both orders, cross-draft selection and a cozy fallback draft. That build is preserved on branch `skeleton_extensive`. The author chose to start smaller and let evals decide where complexity is worth adding back. What changed:

- **One draft per request.** No depth/breadth branch and no brainstorm. For a vague request, one small call asks for 5 story ideas and code picks one at random (added 2026-11-13, see "Story options for vague requests" below).
- **The gate and extraction stay two separate calls.** A request that fails the gate stops before extraction is paid for.
- **No LLM comparison anywhere.** Keep-better is a code-only regression guard (see `pipeline.keep_better`):
  - Only hard failures count. Soft failures play no part.
  - Safety outranks the count, so a safe version is never replaced by an unsafe one.
  - Otherwise the version with fewer hard failures wins, and a tie goes to the new version.
- **Revisions start from the kept version**, in full, under the same system prompt as the first draft plus the revise rules (author confirmed "option A").
- **No fallback draft.** If the final version fails safety, the canned message is shown instead.
- **No `mood` field.** The category carries the tone (silly = funny, cozy = calm, adventure = exciting). Any tone it doesn't cover goes into the premise in a few words, never as invented events. The rubric item became `faithfulness_premise`. `worry` stays: it is filled only when the request states a fear, and comfort requires it (checked in code by `normalize`).
- **The gate returns two checks.** `safety` and `relevance`, each `Check {evidence, passed}`, in one call. Both must pass. The rejection message uses the failed check's evidence (safety first if both fail). `Check` is separate from the judge's `Verdict` because a request has no "fix".

## Story options for vague requests (2026-11-13)

Tested as condition B in `docs/findings/independent_thinking_experiement.md` (10 vague requests, one run each): letting the writer invent its own idea converged on one template, while a random pick from 5 model-made options gave 10 distinct premises. Changes from the tested version:
- **Any vague request, not only cozy.** The options prompt asks for the spec's category ("a silly, funny bedtime story", ...); the tested prompt always said "calm".
- **A worry counts as named** (`options.is_vague`, DECISION). "my son is scared of the dark" still goes straight to the writer, so the story stays about the fear.

- **A random theme steers the options call.** The experiment's option lists repeated across requests (Pip in 9 of 10 lists, a moonlit woodland animal as option 1 in all 10). Code now draws one of 28 curated places/times (`options.STEERS`) and the prompt asks for all 5 options around it. Code controls the space, as the old seed list did; the model fills in characters and specifics, as in condition B. The steers are places and times only (DECISION), and avoid the default palette (moon, woodland, meadow, pond, lantern, garden, lighthouse, cottage); a test checks this. "deep winter" is kept, although snow was common in the experiment's lists. Not yet run live.

## DECISION entries (in code)

1. **`storyteller/llm.py:32` strict schema.** Chosen: post-process pydantic's JSON schema ourselves (`additionalProperties: false`, all fields required, drop `default`). Alternative: openai's `to_strict_json_schema` helper, which ties us to an SDK internal.
2. **`storyteller/llm.py:77` retry policy.** Chosen: 4xx other than 429 fails immediately as `LLMError`. 429, 5xx, connection and validation errors retry, waiting `2**attempt` seconds. Alternative: retry everything.
3. **`storyteller/llm.py:115` missing cost.** Chosen: if OpenRouter omits `usage.cost`, estimate it from token counts at the list price in `config.py`, so the budget guard can't silently read zero. In the 3 sample runs `usage.cost` was always present.
4. **`storyteller/config.py:10` fixed endpoint and model.** Chosen: `BASE_URL` and `MODEL` are not env-overridable, so a stray shell variable can't redirect the key or swap the model. Alternative: allow overrides with a prefix.
5. **`storyteller/extract.py:13` comfort without a worry.** Chosen: code changes the category to cozy. Alternative: trust the model, or ask the user.
6. **`storyteller/judge.py:59` failures computed in code.** Chosen: failures come from each dimension's `passed` flag, never the judge's own summary, and skipped dimensions are dropped. Alternative: trust the judge's summary.
7. **`storyteller/pipeline.py:41` guard puts safety first.** Chosen: compare `(fails safety?, number of hard failures)`. Alternative: count only, where a version failing only safety (1) would beat one failing two other hard checks (2).
8. **`storyteller/pipeline.py:144` budget exhaustion.** Chosen: `BudgetExceeded` becomes a friendly message with `status="error"`, and the trace is kept. Other errors (`LLMError`, missing key) still raise to the CLI.

## Other choices (no marker in code)

- **Judge checks are shown to the writer.** The category files include their `## Judge checks` section in the generation prompt too, so the writer sees what it will be judged on. Alternative: strip that section for generation.
- **Other hard failures at the cap still show the story.** For example, a story still failing wind_down after 3 revisions is shown; only a safety failure is withheld.
- **`--baseline` sends no system prompt**, exactly like the original `main.py`.
- **One `OpenRouterClient` per run**, so the budget guard is per run.

## Spec overrides

- Model access goes through OpenRouter (`https://openrouter.ai/api/v1`, model `anthropic/claude-haiku-5.5`) with the `openai` SDK, not the `anthropic` SDK. The key is `OPENROUTER_API_KEY`.
- No `temperature` is sent; the model doesn't support it. Structured output uses OpenRouter's JSON-schema mode with `provider.require_parameters: true`, validated with pydantic. Hidden reasoning is turned off.

## Deferred: what I'd build next (candidates, let evals decide)

Each of these is implemented on `skeleton_extensive` unless marked otherwise.

- **Breadth for vague requests:** a premise brainstorm that writes three distinct drafts (cozy, adventure, silly) and picks one.
- **LLM pairwise comparison**, asked in both orders to cancel position bias, to break ties between versions and to select across drafts.
- **A safety fallback draft:** one fresh cozy draft before giving up with the canned message (`TODO(safety-fallback)`).
- **Critique check** (not built anywhere): an open-ended "what would a parent dislike?" pass after the rubric (`TODO(critique-check)`).
- **User feedback** (not built anywhere): ask the listener what they thought and revise (`TODO(user-feedback)` in `main.py`).
- **Edgy-request policy** (not built anywhere): what the gate should do with "a dragon who eats villagers" (`TODO(edgy-requests)` in `gate.py`).
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
