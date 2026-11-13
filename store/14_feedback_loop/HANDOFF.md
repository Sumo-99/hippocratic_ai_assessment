---
stage: 14_feedback_loop
status: done
model: opus
completed: 2026-11-13
live_api_cost_usd: 0.00
reviewer_verdict: n/a
---

# 14_feedback_loop: handoff

## Built
- `storyteller/pipeline.py`: `conversation_text`, `_judge` (evaluate + `apply_overrides`, used for every evaluation), `write_and_revise(..., previous=None, change=None)`, one `_run` path for first and feedback turns, shared `_turn` wrapper (trace/budget/usage), public `run` and `give_feedback`.
- `main.py`: feedback loop after a delivered story (`FEEDBACK_PROMPT`, `QUIT_WORDS`, `show()`); quits on blank / q / quit / exit / done (any case, whitespace) or EOF; keeps the last non-None session; `--verbose` details per turn (`print_details` adds a "feedback turn N" line). `TODO(user-feedback)` removed.
- `tests/test_feedback_flow.py` (22 tests): every Task 3 test plus `test_rejected_first_run_has_no_session` and `test_feedback_revision_that_never_clears_is_still_delivered_over_the_old_story`. Covers Review focus 1, 2, 4, 5.
- `tests/test_cli.py` (16 tests incl. 10 parametrised quit words): the 4 planned tests + EOF quit, missing-session fallback, verbose-per-turn.

## Interfaces as built
- `run(request, llm=None) -> PipelineResult` (now with `.session`); `give_feedback(session: StorySession, feedback: str, llm=None) -> PipelineResult`; `conversation_text(request, feedback: list[str]) -> str`. As planned.
- Feedback-turn round-0 revise feedback is `"- The parent asked for this change: {feedback}"` (orchestrator change from the plan's "listener", matching Task 2's "parent's wishes" header).
- New trace keys: `feedback` (list, all feedback incl. this turn's; `[]` on a first run), `turn` (= len(feedback)), `final.waived`; each `versions[i].evaluation.waived` (from the model). Feedback-turn traces use the original request as `request`; `versions[0].feedback_sent` holds the change line. No `options` key on feedback turns.
- On rejected / safety_message / error, `result.session` is the incoming session (None on a first run); the failed feedback is not recorded in it.

## Decisions
- `pipeline.py:87`: round 0 of a feedback turn is the turn's baseline, never guard-compared with the delivered story (alternative: let the guard keep the old story; rejected, it would silently drop the user's change).
- `pipeline.py:152`: a feedback turn always copies `idea` from `session.spec` and never runs options, even if re-extraction is still vague (alternative: re-pick; it would throw the story away). If the re-extraction now names characters too, the writer sees both the idea lines and the named lines.
- `pipeline.py:222`: BudgetExceeded on a feedback turn returns the incoming session.

## Verification
- `.venv/bin/python -m pytest -q` → 155 passed (test_feedback_flow 22, test_cli 16). `tests/test_pipeline.py` untouched and green, so request-only runs send the same bytes.

## Open issues / for the human reviewer
- The judge's `request` on a feedback turn is the multi-line conversation text; `judge._rubric_context` prints it with `!r`, so newlines show as `\n` in the judge prompt (judge.py is frozen by the plan). Worth a glance in a live run.
- `give_feedback` doesn't reject blank feedback itself; the CLI filters it.

## Files touched (uncommitted)
- `storyteller/pipeline.py`, `main.py`, `tests/test_feedback_flow.py` (new), `tests/test_cli.py` (new)
