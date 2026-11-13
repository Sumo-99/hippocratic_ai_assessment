---
stage: 16_feedback_review
status: done
model: opus
completed: 2026-11-13
live_api_cost_usd: 0.00
reviewer_verdict: changes_requested
---

# 16_feedback_review: handoff

Read-only review of the uncommitted `user_feedback_feature` diff against R1–R11. No code or test edits. Claims were checked by reading the tests, by FakeLLM repro scripts and by in-memory mutation runs (monkeypatched in a pytest plugin outside the repo, never written to disk in the repo).

## Requirements

| Req | Verdict | Code | Pinning test(s) |
|---|---|---|---|
| R1 reuse gate/revise/judge | met | `gate.py`, `judge.py`, `feedback.py` not in the diff; `generate.revise_story` body unchanged (only `build_system_prompt` grew the wishes block) | `tests/test_pipeline.py` untouched and green; `test_make_the_dragon_funnier_end_to_end` (stages = gate, extract, revise, judge) |
| R2 preferences + overrides, extract gets waivable defs | met | `models.py` Extraction/Override; `extract.py:10-11` substitutes `waivable_text()`; `overrides.py:6-27`; `prompts/extract.md` Follow-up feedback / Overrides | `test_extract_substitutes_waivable_dimensions`, `test_extract_explains_follow_up_feedback`, `test_make_spec_carries_preferences_and_overrides` |
| R3 safety unrepresentable | met | `models.Waivable`; `config.WAIVABLE`; belt-and-braces `overrides.py:39` | `test_safety_is_not_representable`, `test_waivable_enum_matches_config`, `test_safety_is_never_waived_even_if_smuggled_in`, `test_safety_failure_is_never_waived` (mutation: dropping the `- {"safety"}` fails both) |
| R4 guard consults overrides, waived = non-blocking, not fed to revision | met (partly pinned) | `pipeline._judge:68-71` applies waivers to every evaluation before `build_feedback` and `keep_better` | Not-fed-to-revision: `test_waiver_does_not_hide_other_hard_failures` (mutation that feeds wind_down back fails it). Non-blocking: `test_cliffhanger_waives_wind_down_and_delivers`. Guard ranking: NOT pinned (see L4) |
| R5 wishes block on top, supersedes all but Safety | met | `generate.py:5-12, 37-39` | `test_preferences_block_sits_on_top_of_the_prompt`, `test_revise_keeps_preferences_on_top`, `test_no_preferences_means_prompt_unchanged`, flow test asserts index < `<base>` |
| R6 full rubric every feedback revision | met | judge unchanged; waivers applied after | `test_full_rubric_runs_on_every_feedback_revision` (1+MAX_ROUNDS judge schemas, all DIMENSIONS) |
| R7 safety on feedback (gate) and draft (judge) | met | `pipeline.py:135-142` gate on conversation text; `:178-182` canned message | `test_unsafe_feedback_is_rejected_by_the_gate_and_session_kept`, `test_unsafe_draft_after_feedback_shows_canned_message_and_keeps_session`, `test_safety_failure_is_never_waived` |
| R8 wind_down stays hard | met | `config.HARD` unchanged | `test_feedback_turn_respects_max_rounds_and_returns_best_available` (final hard = wind_down, no override), `test_later_feedback_can_take_back_a_waiver`, assert in `test_cliffhanger_...` |
| R9 start from kept draft, MAX_ROUNDS unchanged | met | `pipeline.py:84-116`; round 0 = revise(delivered story), never guard-compared with it | `test_revisions_start_from_the_kept_draft`, `test_feedback_revision_is_not_discarded_by_the_guard`, `test_feedback_revision_that_never_clears_is_still_delivered_over_the_old_story`, `test_feedback_turn_respects_max_rounds_...` |
| R10 same extraction path | met | `_run` always `extract(llm, conversation_text(...))` | `test_upfront_ask_uses_the_same_path`, `test_multiple_feedback_turns_accumulate` |
| R11 thorough whole-flow tests | met | — | `tests/test_feedback_flow.py` (22) + `tests/test_cli.py` (16). Gap: no test drives `main.main` through the real pipeline (CLI tests stub `pipeline`; `main` cannot inject a FakeLLM) |

Checked and fine: session threading on rejected / safety_message / BudgetExceeded returns the incoming session (pinned, including retry from v0); `waived` never contains safety; feedback-turn round 0 is never replaced by the old story (only by a not-worse revision of itself); trace keys `feedback`, `turn`, `final.waived`, `versions[i].evaluation.waived`, `versions[0].feedback_sent` all pinned by `test_each_feedback_turn_writes_its_own_trace`; the wishes header exempts the Safety section by name and the judge is unchanged.

## Findings

| Sev | File:line | Problem | Concrete failure scenario | Suggested fix |
|---|---|---|---|---|
| medium | `storyteller/pipeline.py:151-155` with `generate.py:23-24` | A feedback turn re-derives `category` from the re-extraction but copies only `idea`. When a vague first request got the cozy fallback, any feedback that names something flips category to None. The idea lines and the newly named lines are also both sent. | Reproduced with FakeLLM: "tell me a story" → category `cozy`, idea "a fox… finds a star". Feedback "call the fox Rusty" → category `None`; revise system prompt = `<base>\n\nCharacters: a fox\nSetting: woods\nPremise: finds a star\nCharacters: Rusty (a fox)\n\n<revise>`. The cozy bundle disappears and `category_checks` is skipped for this and all later turns, though the user only renamed a character. No test covers it. | On a feedback turn use `category = spec.category or session.spec.category`. Consider dropping `idea` fields the re-extraction now fills (or skip the idea's Characters line when `spec.characters` is set). Add a flow test for vague request + naming feedback. |
| medium | `main.py:14, 75` | `QUIT_WORDS` misses the natural answers to "Anything to change?". | User types "no", "nope", "no thanks" or "it's perfect" → a full paid turn (gate, extract, revise, judge, up to 3 more rounds) runs with "The parent asked for this change: no", and the story they liked is rewritten. This spends the $10 budget. | Add `n`, `no`, `nope`, `no thanks`, `nothing`, or change the prompt to "type q to finish". Add the words to the parametrised CLI test. |
| low | `storyteller/extract.py:22-24` | The quote check is a plain substring over the squashed text. Short quotes match inside other words, and on feedback turns the scaffolding ("Original request:", "Changes asked for after hearing the story (newest last):") is part of the haystack. | "a story about my friend's dragon"; the model emits `Override(quote="end", dimension="wind_down")` → `"end"` is in `"friend"` → kept → wind_down waived with no ask. A quote like "the story" always matches on a feedback turn. | Word-boundary match (`re.search(rf"\b{re.escape(q)}\b", hay)`), a minimum of 2 words or 6 chars, and match against the request + feedback strings rather than `conversation_text`. |
| low | `main.py:71-79` | Only EOFError is caught. An `LLMError` (retries exhausted, malformed reply) or Ctrl-C during a feedback turn exits with a traceback and ends the conversation. | Turn 3: OpenRouter returns 5xx past the retries → traceback; the user can't continue from the last good story. Ctrl-C at the prompt (a common way to leave) → `KeyboardInterrupt` traceback. | Catch `LLMError` around `give_feedback`, print a friendly line and keep `session`. Treat `KeyboardInterrupt` at `input` like EOF. |
| low | `storyteller/pipeline.py:216-219` | A fresh client per turn means `MAX_RUN_COST_USD` ($0.10) caps each turn, not the conversation. | 30 feedback turns → up to $3 of the $10 total, with no guard firing. | A per-conversation cap in the CLI loop (sum `trace usage` cost, or carry spent cost on the session). |
| low (test gap) | `tests/test_feedback_flow.py:227-242`; `pipeline.py:39-42` | R4's "guard consults overrides" is unpinned. A mutation making `_hard_rank` count waived hard failures passes all 155 tests. In `test_cliffhanger_waives_wind_down_and_delivers`, `assert not any("wind_down" in c[2] …)` is vacuous: only wind_down fails and it is waived, so no loop revision runs and the only revise call is the change line. | A refactor that ranks on the raw judge verdicts (e.g. `v.evaluation.judge.wind_down.passed`) would make the guard prefer a calm-ending revision over the cliffhanger the user asked for, and no test would catch it. | Add a test: v1 fails {wind_down (waived), engagement}, v2 fails {consistency} → assert v1 is kept (rank 0 < 1). |

## Verification
- `.venv/bin/python -m pytest -q` → 155 passed.
- Mutations (in-memory, via a pytest plugin): no safety subtraction → 2 fail; no quote check → 2 fail; waived wind_down fed to revision → 1 fails; guard counts waived → 0 fail (L4).
- FakeLLM repro for the category finding (scratchpad script, not in the repo).

## Files touched (uncommitted)
- `store/16_feedback_review/HANDOFF.md`, `store/LOG.md`

## Resolution (orchestrator, 2026-11-13)
| Finding | Outcome | Test |
|---|---|---|
| M1 category lost after cozy fallback | fixed: feedback turn uses `spec.category or session.spec.category` (`pipeline.py`, DECISION). The idea plus named-character double "Characters" line is left as is: the preference block and the existing story text dominate. Revisit if a live run shows confusion. | `test_feedback_keeps_the_category_when_the_reextraction_has_none`, `test_feedback_can_still_change_the_category` |
| M2 "no" runs a paid turn | fixed: `main.is_quit` (punctuation ignored) adds stop/no/nope/no thanks/nothing/that's all | `test_cli_quits_on_a_plain_no` (7 cases) |
| L1 substring quote match | fixed: whole-word match. Scaffolding text left in the haystack (a scaffolding-only quote can't name a real conflict; low value) | `test_quote_must_match_whole_words` |
| L2 LLMError / Ctrl-C in CLI | fixed: LLMError → friendly line, session kept; Ctrl-C ends quietly | `test_cli_survives_an_llm_error_during_feedback`, `test_cli_ctrl_c_ends_the_conversation_quietly` |
| L3 per-turn cost cap only | deferred → OPEN_QUESTIONS | — |
| L4 guard waiver unpinned + vacuous assert | fixed: unit test kills the "guard counts waived" mutant (verified); a new flow test forces a real loop revision | `test_guard_ignores_waived_failures`, `test_waived_dimension_is_never_sent_to_a_loop_revision` |

After fixes: `.venv/bin/python -m pytest -q` → 169 passed.
