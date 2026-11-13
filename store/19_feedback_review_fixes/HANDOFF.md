---
stage: 19_feedback_review_fixes
status: done
model: orchestrator
completed: 2026-11-13
live_api_cost_usd: 0.00
reviewer_verdict: n/a (author review, step 2 Q&A)
---

# 19_feedback_review_fixes: handoff

Changes from the author's review questions (walkthrough step 2), on `user_feedback_feature` (still uncommitted).

## Built
1. **Rename: one word, "override".** `Waivable` → `OverridableCheck`; `config.WAIVABLE` → `OVERRIDABLE_CHECKS`; `WAIVABLE_DEFINITIONS` → `OVERRIDABLE_DEFINITIONS`; `waivable_text` → `overridable_text`; `$waivable_dimensions` → `$overridable_checks` (extract.md); `Evaluation.waived` → `overridden` (also the trace keys `final.overridden` and `evaluation.overridden`). Every "waive/waiver" in code, prompts, tests and docs now says override. Historical store handoffs 11–18 keep the old word.
2. **Always a session.** `StorySession.spec` and `.story` are optional; `PipelineResult.session` is always set. `run(request)` = `_turn(StorySession(request=request))`. `_run(session, llm, trace, feedback=None)` branches on `is_feedback = feedback is not None`. `give_feedback` raises `ValueError` on a session with no story. The CLI loops `while session.story is not None` and always continues from `result.session`.
3. **Framing: feedback, not "parent's wishes".** `PREFERENCES_HEADER` = "## Feedback on this story (this comes first) / Where this feedback conflicts with anything below, follow the feedback, except the Safety rules, which always apply."; revise line "- Feedback on this story: …"; `KEEP_WISHES` → `KEEP_FEEDBACK` ("- Keep the earlier feedback on this story: …"); `build_feedback(ev, keep=None)`; judge `EXCEPTIONS_HEADER` "Exceptions the feedback on this story explicitly asks for…"; guard stop reason "revision dropped the requested change".
4. **TODOs removed** from `pipeline.py` (critique-check, safety-fallback) and `gate.py` (edgy-requests). All three stay as deferred items in OPEN_QUESTIONS, now pointing at code locations.

## Tests
- New: `test_every_run_returns_a_session_even_when_rejected`, `test_feedback_without_a_story_is_refused`, `test_first_turn_session_has_no_feedback_and_feedback_turn_appends` (also checks the earlier session isn't mutated), `test_cli_feeds_each_result_session_to_the_next_turn` (replaces the "result has no session" defensive test, which is no longer possible).
- Renamed with the vocabulary change. `tests/test_pipeline.py` untouched.
- `.venv/bin/python -m pytest -q` → 179 passed.

## Open for the author
- Optional: drop `faithfulness_named` / `faithfulness_premise` from `OVERRIDABLE_CHECKS`. Re-extraction already updates those fields, so an override for them is rarely right.
- The judge's pre-existing line "The parent's request, word for word" was left as is (not part of this feature).
