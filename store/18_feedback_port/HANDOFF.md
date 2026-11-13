---
stage: 18_feedback_port
status: done
model: orchestrator
completed: 2026-11-13
live_api_cost_usd: 0.00
reviewer_verdict: n/a (author reviews in the walkthrough)
---

# 18_feedback_port: handoff

`user_feedback_feature` was moved from `a3ebb70` to `skeleton` (`a084a1a`). It had no commits of its own, so nothing was lost. The old work was re-applied with `git stash apply` (3-way merge); the stash entry is kept as a backup.

## Conflicts and how they were resolved (6 files)
- `models.py`: upstream's 4 categories + `Waivable`. `Extraction` gains `preferences`/`overrides`. `StorySpec(Extraction)` now **inherits** them, so its separate declarations were dropped.
- `extract.py`: `normalize` is gone upstream. The quote check is now `extract.quoted(quote, text)`, applied inline in `extract()` beside the empty-character filter. `extract()` also drops safety overrides (`overrides.active`), because the new `StorySpec(**e.model_dump())` re-validates and would *crash* on a forged safety override (found by `test_safety_failure_is_never_waived`).
- `generate.py`: `make_spec` is gone. `PREFERENCES_HEADER` block is prepended to upstream's new `build_system_prompt` (named fields win over the idea).
- `pipeline.py`: rule 3 is first-turn only: `if session is not None: carry idea; elif spec.premise is None: ideas`. **Dropped:** the category carryover (review M1). It only protected the cozy fallback, which no longer exists.
- `prompts/extract.md`: upstream's category list; `worry` dropped from the preferences "don't repeat" line.
- `tests/test_stages.py`: the make_spec tests went with make_spec; one test now pins that the spec inherits preferences/overrides.

## Tests ported
- `worry=` removed from fixtures (test_cli, test_feedback_flow, test_overrides).
- `normalize(...)` tests → `quoted(...)` + `extract()` end-to-end (quote filter and character filter).
- Cozy-carryover test → `test_no_premise_story_keeps_its_idea_and_feedback_can_add_a_premise` ("Alice and her cat Bob": idea carries over, no ideas call on feedback, named characters win over the idea, a feedback-added premise replaces the idea's situation).
- Judge-context test: the last base line is now `Premise:` (Worry line gone upstream).
- Mutations: no safety filter in extract → 1 fails; ideas on every turn → 2 fail.

## Verification
- `.venv/bin/python -m pytest -q` → 177 passed.

## Open issues / for the human reviewer
- Not re-run live on the new base. Upstream's own changes (no cozy fallback, loosened safety, ideas for named-but-no-premise requests) are also untested live, so one smoke run covers both (~$0.015).
- `faithfulness_premise` is skipped when there is no premise, and rule 3 targets exactly those requests. For them, guard protection rests on the precise waiver + keep-wishes line only (see OPEN_QUESTIONS).

## Files touched (uncommitted)
- storyteller: config, extract, feedback, generate, judge, models, pipeline, overrides (new), prompts/extract.md; main.py
- tests: test_evaluation, test_prompts, test_stages, test_cli (new), test_feedback_flow (new), test_overrides (new)
- docs: ARCHITECTURE, OPEN_QUESTIONS, README, plans/2026-11-13-user-feedback.md; CLAUDE.md; store/11-18, LOG

## Live smoke on the new base (2026-11-13, 14 calls, $0.0081; stories: `stories_new_base.md`)
Same 3-turn script as stage 17 (Lily + clumsy dragon → "make the dragon funnier" → "end on a cliffhanger").
- Turn 0: passed in round 0 ($0.0018). The extract gave premise "a girl named Lily and her friend, a clumsy dragon", so **rule 3 (ideas) did not fire**. The no-premise path is still unverified live.
- Turn 1: `preferences="Make the dragon funnier."`, no overrides, passed in round 0 ($0.0022). Category became silly again.
- Turn 2: override `wind_down` ("end on a cliffhanger") ✓. Round 0 ended on a cliffhanger; `wind_down` waived; `category_checks` (soft) failed, and **its fix still said to remove the cliffhanger despite the exceptions header**. Round 1 got that fix plus `KEEP_WISHES`, and **kept the cliffhanger** ("a shadow was moving closer... Ember's eyes... flickered open one more time"). The judge then passed everything, including `wind_down`, honouring the exception. Delivered round 1 ($0.0040, 6 calls).
- Reading: the layers covered for each other. The precise waiver doesn't stop every conflicting fix, but this time the keep-wishes line held, and the guard + stop rule were there as a backstop. All three layers stay.

## Live smoke, no-premise path (2026-11-13, 9 calls, $0.0040; script `smoke_no_premise.py`, stories `stories_no_premise.md`)
"Alice and her cat Bob" → "end on a cliffhanger".
- Turn 0: premise None → **rule 3 fired**: ideas call ran, picked "a magical library where the books whisper secrets at night". Passed in round 0.
- Turn 1: **no ideas call; the same idea carried over** (spec.idea identical). The override on `wind_down` was kept. The feedback revision ended on a cliffhanger ("a faded green book slid out from the very back of the shelf"), and the judge *passed* `wind_down`, honouring the exception (it failed it in both earlier runs). Passed in round 0.
- `faithfulness_premise` was skipped on both turns (no premise), as expected. No loop round ran, so the weak spot (no guard protection without a premise) was neither hit nor tested.
- Stage 18 live total: $0.0121. Feature live total: ~$0.046.
