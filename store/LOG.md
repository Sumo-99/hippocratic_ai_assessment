# Build log (append-only, newest at bottom)

Format: `YYYY-MM-DD HH:MM | stage | event | detail`. Events: dispatched, handoff, reviewed, fixed, live-call, committed, blocked.

2026-11-11 | 00_plan | handoff | spec + plan + .gitignore + store scaffolded
2026-11-11 | 01_foundation | dispatched | sonnet subagent, Task 1
2026-11-11 | 01_foundation | handoff | 9 tests pass, no live calls
2026-11-11 | 01_foundation | reviewed | approved; added token-based cost fallback
2026-11-11 | 02_prompts | dispatched | opus subagent, Task 2
2026-11-11 | 03_stages | dispatched | sonnet subagent, Task 3
2026-11-11 | 04_evaluation | dispatched | sonnet subagent, Task 4
2026-11-11 | 04_evaluation | handoff | 11 tests pass
2026-11-11 | 03_stages | handoff | 16 tests pass
2026-11-11 | 02_prompts | handoff | 22 tests pass
2026-11-11 | wave2 | reviewed | approved all 3; prompt loader strips author notes; full suite 58 passed
2026-11-11 | 05_pipeline | dispatched | opus subagent, Task 5
2026-11-11 | 05_pipeline | handoff | full suite 78 passed; CLI help ok
2026-11-11 | 05_pipeline | reviewed | approved
2026-11-12 | 06_docs | dispatched | sonnet subagent, Task 6
2026-11-12 | 07_live_runs | dispatched | haiku subagent, Task 7 (3 live runs, est <= $0.10, user supplied key)
2026-11-12 | 06_docs | handoff | ARCHITECTURE + OPEN_QUESTIONS (16 entries) + README section; mermaid unvalidated
2026-11-12 | 07_live_runs | live-call | 3 runs, total $0.0221, all exit 0
2026-11-12 | wave4 | reviewed | approved both; flagged lenient judge + 'my son' as named character
2026-11-12 | 09_human_review | fixed | extract.md: family/relationship words are not character names (+ guard test, 79 passed); lenient judge logged in docs/OPEN_QUESTIONS.md eval backlog
2026-11-12 | 08_auto_review | dispatched | opus read-only reviewer
2026-11-12 | 08_auto_review | reviewed | 11 findings: fixed 8, #10 pre-fixed, #7 accepted, #8 deferred; 84 passed
2026-11-12 | 09_simplify | handoff | trimmed to one draft + code-only guard; full build kept on skeleton_extensive; 67 passed
2026-11-12 | 09_simplify | fixed | dropped mood (tone -> category/premise; rubric item faithfulness_premise); gate = safety + relevance Checks; 67 passed
2026-11-12 | 09_simplify | live-call | 3 runs on simplified build, total $0.0060, all PASS (1 revision on named_characters: story_arc+length); runs/samples replaced
2026-11-13 | 11_feedback_contracts | planned | branch user_feedback_feature from skeleton; plan docs/plans/2026-11-13-user-feedback.md; stages 11-16 contracts written
2026-11-13 | 11_feedback_contracts | handoff | Waivable/Override/StorySession + new fields; 98 passed
2026-11-13 | 12,13,14 | dispatched | parallel: sonnet overrides, opus prompts, opus loop
2026-11-13 | 12_feedback_overrides | handoff | overrides.py + extract quote check; 30 passed (test_overrides + test_stages)
2026-11-13 | 13_feedback_prompts | handoff | extract.md feedback/preferences/overrides + parent's-wishes block first in build_system_prompt; 63 passed (test_prompts + test_stages)
2026-11-13 | 14_feedback_loop | handoff | run->session, give_feedback, conversation_text, CLI loop; 22 flow + 16 CLI tests; 155 passed
2026-11-13 | 15_feedback_docs | handoff | ARCHITECTURE feedback loop + Feedback turn section; OPEN_QUESTIONS user feedback decisions + eval items 7-9; README feedback usage (docs only)
2026-11-13 | 16_feedback_review | handoff | R1-R11 all met (R4 guard-ranking unpinned); 2 medium (category lost on feedback after vague request; 'no' not a quit word), 4 low; 155 passed
2026-11-13 | 16_feedback_review | resolved | fixed M1, M2, L1, L2, L4; L3 deferred; 169 passed; code uncommitted for author review
2026-11-13 | 17_feedback_live_smoke | live-call | 1 request + 2 feedback turns, 20 calls, $0.0145; found: loop undoes waived cliffhanger via category_checks/story_arc fixes (delivered story ends asleep)
2026-11-13 | 17_feedback_live_smoke | fixed | guard protects faithfulness_premise when wishes/feedback + KEEP_WISHES line in loop feedback; 176 passed; not re-run live
2026-11-13 | 17_feedback_live_smoke | live-call | re-run after fix, 18 calls, $0.0130 (live total $0.0275): guard delivered the cliffhanger; keep-wishes line overridden by judge fix that names the cliffhanger; 3 wasted rounds
2026-11-13 | 17_feedback_live_smoke | fixed | precise waiver (exceptions in judge rubric context) + stop when revision only drops the parent's change; 182 passed
2026-11-13 | 17_feedback_live_smoke | live-call | precise waiver check, 12 calls, $0.0066: cliffhanger delivered in round 0 (4 calls); judge still fails wind_down itself, coarse waiver absorbs it; stage total $0.0341
2026-11-13 | 18_feedback_port | handoff | feedback feature re-based onto skeleton a084a1a (three rules); 6 conflicts resolved, category carryover dropped, rule 3 first-turn only; 177 passed; old work kept as patch + stash
2026-11-13 | 18_feedback_port | live-call | 3-turn smoke on new base, 14 calls, $0.0081: cliffhanger delivered (round 1, keep-wishes line held against a conflicting category_checks fix); rule 3 not exercised (premise extracted)
2026-11-13 | 18_feedback_port | live-call | no-premise smoke (Alice and her cat Bob -> cliffhanger), 9 calls, $0.0040: rule 3 fired, idea carried over, no re-pick, cliffhanger in round 0
2026-11-13 | 19_feedback_review_fixes | handoff | waive->override (OverridableCheck), always-a-session (is_feedback), feedback framing, TODOs out of .py; 179 passed
2026-11-13 | 19_feedback_review_fixes | cli | exit/Esc to quit (blank Enter re-asks), story scroll, moon spinner; 196 passed
2026-11-13 | 19_feedback_review_fixes | cli | all UI moved to root ui.py (main.py = flow); banner, captions, unfolding scroll, night-sky loading scene, markdown strip; 210 passed
2026-11-13 | 20_anthropic_invocation | start | worktree anthropic_invocation from skeleton 8ce1517; anthropic 2.8.0 installed; baseline 210 passed
2026-11-13 | 20_anthropic_invocation | code | BaseLLMClient + AnthropicClient + build_client + pipeline swap + docs; 237 passed; test_llm.py untouched; code uncommitted pending review
2026-11-13 | 20_anthropic_invocation | review | no blocking findings; real-SDK offline serialization check passed; waiting on user for key + live-smoke OK
2026-11-13 | 20_anthropic_invocation | live | user-approved smoke on claude-haiku-5-5: 2 pipeline runs PASS, baseline OK, ~$0.005; all schemas accepted
2026-11-13 | 20_anthropic_invocation | push | code committed (f980c0f..ae5bbb7) and pushed for the user's review; open: ANTHROPIC_BASE_URL gap
2026-11-13 | 20_anthropic_invocation | simplify | Anthropic-only at the author's request; OpenRouter + LLM_PROVIDER + openai removed; base-URL gap fixed; 220 passed; live run PASS $0.0018
2026-11-13 | 20_anthropic_invocation | squash | adea93d+d7ac405 squashed into b44b54d (force-pushed, author-approved); every commit after 23b3a2d passes 220; local backup branch backup/anthropic_invocation-pre-squash
2026-11-13 | 20_anthropic_invocation | simplify | removed storyteller/clients.py (build_client) and tests/test_clients.py; pipeline constructs AnthropicClient directly; 218 passed; code uncommitted pending review
