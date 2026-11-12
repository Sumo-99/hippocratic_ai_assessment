---
stage: 03_stages
model: sonnet
plan_section: "Task 3: Stage modules (sonnet)"
parallel_with: [02_prompts, 04_evaluation]
---

# 03_stages: gate, extract, brainstorm, generate

One job: write the thin LLM-stage modules and the routing logic, tested offline with FakeLLM.

## Inputs
- Plan: `../../docs/plans/2026-11-11-storyteller-skeleton.md`. Read only "Global Constraints", "Shared Interfaces", "Task 3: Stage modules (sonnet)", and the placeholder table in "Task 2" (prompt names and `$` keys you call `.substitute()` with).
- Handoff: `../01_foundation/HANDOFF.md`. Its "Interfaces as built" overrides the plan.
- Code: `../../storyteller/{config,models,llm,fake}.py`, `../../storyteller/prompts/__init__.py`, `../../tests/conftest.py`

Do NOT load: other stage folders, `storyteller/prompts/*.md` (stage 02 is writing them right now), judge/compare/feedback/pipeline.

## Process
1. TDD from the plan's Task 3 test list. The prompt files may not exist yet, so in tests **monkeypatch `storyteller.prompts.load`** to return `string.Template` stubs that use the planned placeholders. Never depend on the real `.md` files.
2. Implement `storyteller/{gate,extract,brainstorm,generate}.py` with the exact signatures from the plan.
3. No live API calls. Do not `git add` or `git commit`. Don't edit shared files (`tests/conftest.py`, `models.py`, `config.py`, `llm.py`, `fake.py`); if you need a change there, describe it in the HANDOFF.

## Outputs
- `storyteller/{gate,extract,brainstorm,generate}.py`, `tests/test_stages.py` (uncommitted)
- `HANDOFF.md` here

## Done when
`.venv/bin/python -m pytest tests/test_stages.py -v` → all pass.

## Review check
Routing: premise present → depth, otherwise breadth. Unknown category → `[cozy, adventure, silly]`. Comfort without a worry → cozy. Brainstorm forces exactly 3 premises and keeps the named characters. The system prompt leaves out absent variables.
