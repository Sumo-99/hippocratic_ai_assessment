---
stage: 03_stages
status: done
model: sonnet
completed: 2026-11-11
live_api_cost_usd: 0.00
reviewer_verdict: approved
---

# 03_stages: handoff

## Built
- `storyteller/gate.py`: `check_request` (stage `gate`), `gate_message`. TODO(edgy-requests) in docstring area.
- `storyteller/extract.py`: `extract` (stage `extract`, calls `normalize`), `normalize`, `plan_drafts`, `breadth_categories`.
- `storyteller/brainstorm.py`: `brainstorm` (stage `brainstorm`).
- `storyteller/generate.py`: `depth_spec`, `breadth_specs`, `build_system_prompt`, `write_story` (stage `generate`), `revise_story` (stage `revise`).
- `tests/test_stages.py`: 16 tests, prompts stubbed via monkeypatching `storyteller.prompts.load`.

## Interfaces as built (where the plan was silent)
- Placement: routing helpers (`normalize`, `plan_drafts`, `breadth_categories`) are in `extract.py`; spec builders and prompt assembly are in `generate.py`. Pipeline should import from those.
- Modules call `prompts.load(...)` through the package (`from . import prompts`), so patching `storyteller.prompts.load` works.
- Prompt templates used: `gate`, `extract` (no placeholders); `brainstorm` (`$characters`, `$setting`, `$categories`; unset values pass as "none specified", categories comma-joined); `base` (`$target_words`); category file by name; `revise`.
- User messages: gate/extract get the raw request; brainstorm gets "Brainstorm the premises."; generate gets "Please write the story."; revise gets `Story:\n...\n\nFeedback:\n...`.
- `breadth_specs` uses `breadth_categories(e)[i]` (not the premise's category) and sets `named_characters = bool(e.characters)`.
- `build_system_prompt` = base + category, then a block of `Characters/Setting/Premise/Mood/Worry` lines for non-empty fields, joined by blank lines.

## Decisions
- `# DECISION:` in `extract.normalize`: comfort without a worry becomes cozy in code.
- Brainstorm: our category plan always overrides the model's; user-named characters/setting override; model-invented ones kept when the user named none.

## Verification
- `.venv/bin/python -m pytest tests/test_stages.py -v` -> `16 passed`. No network.

## Open issues
- Real prompt files (stage 02) not yet cross-checked against these placeholder keys; `tests/test_prompts.py` covers the keys.
- Gate message wording is generic: "<reason> Please try another request and I'll be happy to tell a story."

## Files touched (uncommitted)
- New: the four modules, `tests/test_stages.py`, this file. No shared files edited.

## Orchestrator review (2026-11-11)
- Approved. Verified with real prompt files: comfort spec builds a 478-word system prompt with Worry line and no Mood line; revise appends revise.md after base+category+variables as 02 expects.
