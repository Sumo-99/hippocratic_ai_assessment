---
stage: 13_feedback_prompts
status: done
model: opus
completed: 2026-11-13
live_api_cost_usd: 0.00
reviewer_verdict: n/a
---

# 13_feedback_prompts: handoff

## Built
- `storyteller/prompts/extract.md`: the intro now says the text may be a request plus later changes. Two new field descriptions (`preferences`, `overrides` with `quote`/`dimension`/`allow`, in schema order). Two new sections: `## Follow-up feedback` (read the whole text, later changes win, a correction updates only its field, a change can take back an earlier wish and its override, standing preferences persist) and `## Overrides` (only for a certain conflict, exact-quote rule, 4 wind_down phrasings, 2 non-conflicts including `"an exciting adventure" → overrides: []`, safety statement, then `$waivable_dimensions`). The only `$` in the file is that placeholder.
- `storyteller/generate.py`: `PREFERENCES_HEADER` constant; `make_spec` copies `preferences` and `overrides`; `build_system_prompt` puts the wishes block first when `spec.preferences` is truthy. `revise_story` gets the block on top for free (it calls `build_system_prompt`).

## Interfaces as built
- **Header text differs from the plan** ("parent's", not "listener's"). Exact block, as the first `\n\n`-joined part:
  ```
  ## The parent's wishes (these come first)
  Where these wishes conflict with anything below, follow these wishes, except the Safety rules, which always apply.
  {preferences}
  ```
  The first two lines are exported as `generate.PREFERENCES_HEADER`.
- An empty string for `preferences` counts as none (no block).

## Decisions
- `generate.py:5`: "parent's wishes" not "listener's wishes". In `base.md`, "Listener" already means the child the story is for. Calling the requester's instructions the listener's would muddle that term for the writer. Alternative: the plan's wording.
- `generate.py:7`: the wishes beat base, category and variables but not Safety. A cliffhanger or a scarier tone is the parent's call. Making the story unsafe is not, and the judge rejects such a draft anyway. Alternative: no exception (rejected, since it invites a writer/judge conflict on safety).
- `tests/test_prompts.py:85`: the safety test asserts the explicit sentence "The safety rule can never be overridden" and that no `- safety` line exists. Alternative: asserting "safety" is absent from the overrides section (fragile, and the model would then have to infer it).
- extract.md (no code comment, since prompts have none): an instruction that gets an override still goes into `preferences`, so the writer follows it. Tone words in the original request still follow the old tone→premise/category rule, while tone *changes* in feedback go to `preferences`.

## Verification
- `.venv/bin/python -m pytest -q tests/test_prompts.py tests/test_stages.py` → 63 passed.
- Full suite: 21 failures, all in `tests/test_feedback_flow.py` (`pipeline.give_feedback` / `conversation_text` not yet built: Task 3 is in progress). None touch this stage's files.

## Open issues / for the human reviewer
- The extract prompt's false-positive behaviour (overrides for non-conflicts) can only be checked live with Haiku. It is worth a small eval: "exciting adventure", "make it funnier", "scarier" → expect `[]`; "cliffhanger", "to be continued" → expect wind_down.
- The `quote` rule asks for exact spelling and capitals. Whether code-side matching is case-sensitive is Task 1's call.
- The prompt assumes Task 3 formats the text as "Original request" + numbered changes, newest last, and refers to it that way loosely. If Task 3's wording differs, nothing breaks, but the words should line up.

## Files touched (uncommitted)
- `storyteller/prompts/extract.md`, `storyteller/generate.py`, `tests/test_prompts.py`, `tests/test_stages.py`
