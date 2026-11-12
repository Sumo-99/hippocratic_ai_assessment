---
stage: 02_prompts
status: done
model: opus
completed: 2026-11-11
live_api_cost_usd: 0.00
reviewer_verdict: approved
---

# 02_prompts: handoff

## Built
- `storyteller/prompts/base.md`: audience, safety, bedtime shape, length ("About 500–700 words. Aim for roughly $target_words words."), output = story only with optional title line.
- `storyteller/prompts/{adventure,silly,comfort,gentle_lesson,cozy}.md`: each has `# Category: x`, then `## Structure`, `## Do / Don't`, `## Judge checks` (judge checks is the LAST section in every file).
- `storyteller/prompts/gate.md`: judges the request; reshape-able = safe; "when unsure, choose true"; field order reason → safe → relevant.
- `storyteller/prompts/extract.md`: spec §2 rules (no invented premise, comfort only with worry, moral dilemma → gentle_lesson, unclear → null).
- `storyteller/prompts/brainstorm.md`: 3 distinct premises, one per listed category in order; named characters/setting in every premise.
- `storyteller/prompts/judge.md`: all 9 `JudgeResult` fields, hard vs soft, evidence → passed → fix, fix must say where, skip rule (evidence "N/A", passed true, fix null). No mention of revisions.
- `storyteller/prompts/revise.md`: a suffix starting `## Editing an existing story`, meant to be appended after base + category + variable lines.
- `storyteller/prompts/compare.md`: parent-at-bedtime question, reason → winner, tells it to ignore order and length.
- `storyteller/prompts/baseline.md`: empty.
- `tests/test_prompts.py`: 22 tests (placeholders exact per file, category headings, comfort phrase absent, judge names every field and never says "revis", base length line).

## Interfaces as built
Placeholders match the plan table exactly. Notes for callers (T3/T4):
- `judge` `$rubric_context`: free text the caller builds. The prompt tells the judge "if a dimension does not apply (the context above says so)" → the caller must state skips explicitly, e.g. "No characters or setting were named: skip faithfulness_named." and "No premise or mood given: skip faithfulness_premise_mood." Also include named characters, setting, premise, mood, worry, category.
- `judge` `$category_checks`: intended to be the bullet list under `## Judge checks` of the category file (easy split: text after `"## Judge checks"`).
- `brainstorm` `$characters` / `$setting`: the prompt says "(empty means none)", so pass `""` (or `", ".join([])`) when not named. `$categories`: comma-separated list in order.
- Story text is not a placeholder anywhere: judge/compare/revise expect the story(ies) in the user message. Compare expects labels "Story A" / "Story B".

## Decisions
- gate.md line 1: TODO for edgy requests is an HTML comment (`<!-- AUTHOR NOTE ... -->`). `load()` does not strip it, so it IS sent to the model. Alternative: strip `<!-- -->` lines in `prompts/load()` (not my file) — recommend T3/T5 or reviewer decide.
- Category files include `## Judge checks` in the generation prompt too (spec bundles them); writer sees what it will be judged on.
- comfort: "never dismiss" phrased as "Don't tell the character the worry is silly or that there is no reason to feel scared" to satisfy the review rule while still forbidding it.

## Verification
- `.venv/bin/python -m pytest tests/test_prompts.py -v` → `22 passed`. All 13 prompts total ~2,700 words.

## Open issues / for the human reviewer
Three prompt choices I'm least sure of:
1. **Gate leniency** ("when unsure, choose true", a short list of hard-no topics). Could let through requests the author would want refused; relies on the writer + safety judge downstream.
2. **Judge strictness and skip signalling**: the judge decides skips from free-text `$rubric_context`, and "Pass only if all are met" for category_checks may make that soft dimension fail often and burn revision rounds.
3. **Revise as a suffix**: assumes the caller puts base + category + variables first, then revise.md, and sends previous story + feedback in the user message. If T3 builds it differently, the "rules above" reference breaks.
- Also: the gate's author-note comment reaches the model (see Decisions).

## Files touched (uncommitted)
- New: `storyteller/prompts/*.md` (13), `tests/test_prompts.py`, `store/02_prompts/HANDOFF.md`

## Orchestrator review (2026-11-11)
- Approved. Fix applied by orchestrator: `prompts.load()` now strips `<!-- -->` author notes so gate.md's TODO isn't sent to the model. Flag for human review: gate leans permissive; category_checks is all-or-nothing and may burn revision rounds (watch in live runs).
