---
stage: 15_feedback_docs
status: done
model: haiku
completed: 2026-11-13
live_api_cost_usd: 0.00
reviewer_verdict: n/a
---

# 15_feedback_docs: handoff

<!-- Keep under ~80 lines. Later stages read THIS instead of the code or the chat. -->

## Built
- `docs/ARCHITECTURE.md`: Diagram 1 gains the feedback loop (feedback input, conversation text, re-extraction, feedback revision into the loop, session end); Diagram 2's judge box notes that code applies overrides after the judge; new "## Feedback turn" section.
- `docs/OPEN_QUESTIONS.md`: new "## User feedback (2026-11-13)" section (decisions, deferred items); the "User feedback" deferred bullet removed (now built); eval backlog items 7-9 (over-eager overrides, whether preferences are honoured, judge request display).
- `README.md`: `--verbose` note for feedback turns, and a feedback paragraph under "Run it" with quit words.

## Interfaces as built
none (docs only).

## Decisions
- Docs describe only what the handoffs of 12, 13 and 14 state. The gate is described as judging only the original request, taken from the plan's deferred item, not from a handoff.
- The feedback revision and the feedback-turn trace keys are documented as the handoffs give them.

## Verification
- Docs only: no code or tests changed, no live calls, no test run. Mermaid syntax was checked by eye only, not rendered.

## Open issues / for the human reviewer
- Plan's Task 4 said "README: a feedback example in the CLI usage". The README example is prose with two sample changes, not a shell block, because the feedback prompt text is not in the handoffs.
- ARCHITECTURE's status banner still says "the simplified first version"; it was left as is, since the feedback loop adds to it without changing the design.

## Files touched (uncommitted)
- `docs/ARCHITECTURE.md`, `docs/OPEN_QUESTIONS.md`, `README.md`, `store/15_feedback_docs/HANDOFF.md`, `store/LOG.md` (one line appended)
