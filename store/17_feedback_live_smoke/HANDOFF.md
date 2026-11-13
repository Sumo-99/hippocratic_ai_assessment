---
stage: 17_feedback_live_smoke
status: done
model: orchestrator
completed: 2026-11-13
live_api_cost_usd: 0.0145
reviewer_verdict: n/a
---

# 17_feedback_live_smoke: handoff

Author-approved live run: 1 request + 2 feedback turns, 20 calls, **$0.0145**. Script: `smoke_feedback.py` (run from the repo root). Stories: `stories.md`. Traces (gitignored): `runs/20261113T0630{30,44}*`, `runs/20261113T063131*`.

Request: "A story about a girl named Lily and her friend, a clumsy dragon" → "make the dragon funnier" → "end on a cliffhanger".

## What worked
- Turn 0: one consistency fix, then all passed ($0.0035).
- Turn 1 ("funnier"): the extraction gave `preferences="Make the dragon funnier."` and no overrides (no false positive). The feedback revision passed every check in round 0 ($0.0025, 4 calls).
- Turn 2 ("cliffhanger"): `overrides=[{quote:"end on a cliffhanger", dimension:wind_down}]`, and the quote check kept it. Preferences built up across turns: "Make the dragon funnier. End on a cliffhanger." The round-0 revision ended on a cliffhanger, and `wind_down` was waived ✓.

## Finding (high): the loop undoes the waived change through *other* dimensions
The turn-2 delivered story (round 3) ends asleep, so the user's cliffhanger was lost.
- Round 0 cliffhanger → `category_checks` (silly) fails, and its fix says "make the ending fully sleepy, remove the rustle and peeking eyes".
- Round 1 asleep → `faithfulness_premise` fails ("the cliffhanger was requested").
- Round 2 cliffhanger → `story_arc` fix: "resolve the mystery of the noise".
- Round 3 asleep → delivered. Soft failures don't count at the guard and a tie goes to the new version.

Root cause: the coarse waiver covers only `wind_down`, but the calm-ending rule is also encoded in `category_checks` and `story_arc`. Their fixes reach the reviser as explicit instructions in the user message, and they beat the preference block in the system prompt. The guard can't see the regression, because the one dimension that notices it (`faithfulness_premise`, which reads the whole conversation) is soft.

FakeLLM tests didn't catch this, because the fake judge's fixes never contradict the preferences.

## Minor
- Turn 1 set `category=silly` from "make it funnier", although the prompt says feedback tone goes in preferences. It's harmless here (silly fits), but it shows the rule isn't held.

## Fix options (author to choose)
See the session. The candidates are: protect the change at the guard on feedback turns, tell each loop revision not to undo the wishes, widen overrides to all dimensions in conflict, or the precise judge-prompt form.

## Resolution (author chose "guard + keep-wishes line", 2026-11-13)
- `pipeline.keep_better(prev, new, protect=())`: with `protect=PROTECT_WISHES` (`("faithfulness_premise",)`), a revision that ties on hard checks but newly fails a protected dimension does not replace the kept version. `write_and_revise` passes it when the spec has preferences or it is a feedback turn. First runs without wishes behave as before.
- `feedback.build_feedback(ev, wishes=None)`: appends `KEEP_WISHES` when wishes exist. Not added to the feedback revision itself (that one carries only the parent's change).
- Tests: `test_guard_protects_listed_dimensions_on_a_tie`, `test_loop_never_trades_the_users_change_for_a_soft_fix` (the smoke flip-flop scripted: delivers v3, not v4), `test_loop_revisions_carry_the_keep_wishes_line`, `test_upfront_wishes_are_protected_too`, `test_first_run_without_wishes_keeps_the_old_tie_rule`, plus 2 `build_feedback` unit tests. `test_waiver_does_not_hide_other_hard_failures` updated for the extra line (it still asserts that wind_down is never sent).
- Mutation check: guard ignoring protect → 3 fail; no keep-wishes line → 2 fail.
- `.venv/bin/python -m pytest -q` → 176 passed. Not yet re-verified live.

## Live re-run after the fix (2026-11-13, $0.0130, 18 calls; stories: `stories_after_fix.md`)
- Turns 0 and 1 passed in round 0. Turn 1 again had no false-positive override.
- Turn 2: **the guard worked.** The delivered story is round 0, which ends on a cliffhanger ("what if it's coming down the hill?"). Guard log: kept_round 0 in all 3 rounds.
- **The keep-wishes line did not work.** The judge's `category_checks` fix (silly bundle: "silliness fades into sleep") said literally "removing the glittering light and the 'what if it's coming down the hill' cliffhanger". The reviser obeyed that specific order over the general keep line, all 3 times (every ending asleep, `faithfulness_premise` failed). Since the kept version never changed, the identical feedback was resent each round, about $0.006 for nothing.
- Net: the user now gets what they asked for, but a waived turn can burn MAX_ROUNDS on revisions that can't succeed while the judge keeps issuing fixes that undo the change.

## Next options (author to choose)
1. Precise waiver (the deferred upgrade): pass the allowed exceptions (`allow` text) into the judge's rubric context, so no dimension issues a fix that undoes them. This is the real fix. It changes the judge's context/prompt, which v1 kept static.
2. Cheap cost stop (code only): when the guard rejected a revision and the next feedback would be identical, stop the loop instead of resending it.
3. Filter fixes in code: drop a fix bullet that quotes the override's text (fragile).

## Second resolution (author chose "precise waiver + stop", 2026-11-13)
- `judge._rubric_context` adds `EXCEPTIONS_HEADER` ("Exceptions the parent explicitly asked for. Do not fail any dimension because of them, and never write a fix that removes or weakens them. Safety always applies in full:") plus `- {dimension}: {allow}` per `overrides.active(spec.overrides)`. The judge is no longer fully frozen: its *context* changed, and `judge.md` did not.
- `overrides.active()` is the single place that drops safety; `apply_overrides` uses it too.
- `write_and_revise`: if `kept is prev` and the hard ranks tie, stop (`guard[-1]["stopped"] = "revision dropped the parent's change"`). This only applies when `protect` is active, since without it a tie can't be rejected.
- Tests: 4 in `test_evaluation.py` (byte-identical without overrides, exceptions listed, safety never listed, exceptions reach the system prompt) and 2 in `test_feedback_flow.py` (exceptions reach every feedback-turn judge call; a new-hard-failure rejection still retries). Two flip-flop tests now expect the early stop.
- Mutations: exceptions removed → 3 fail; stop removed → 2 fail; stop on every rejection → 3 fail (including the walkthrough). 182 passed.

## Live check of the precise waiver (2026-11-13, 12 calls, $0.0066; stories: `stories_precise_waiver.md`)
- Turn 2 ("end on a cliffhanger"): **passed in round 0, in 4 calls for $0.0025** (before: 10 calls, $0.0085, and the cliffhanger was lost or wasted). The delivered story ends "Something is knocking on the roof...". `category_checks`, `story_arc` and `faithfulness_premise` all passed, so no dimension wrote a conflicting fix.
- `wind_down` itself still failed, with the fix "remove the knocking". The judge doesn't fully obey the exception for the dimension being waived. The coarse guard waiver absorbed it (`waived: [wind_down]`), so it was never sent to revision. **Keep both layers.**
- The stop rule wasn't exercised (no loop rounds were needed).
- Live total for stage 17: $0.0341 (3 runs).
