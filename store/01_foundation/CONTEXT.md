---
stage: 01_foundation
model: sonnet
plan_section: "Task 1: Foundation (sonnet)"
parallel_with: []
---

# 01_foundation: contract code every stage depends on

One job: build config, the pydantic models, the OpenRouter client (with retries and the budget guard), FakeLLM, Trace, and the prompt loader, all tested offline.

## Inputs
- Plan: `../../docs/plans/2026-11-11-storyteller-skeleton.md`. Read only these sections: "Global Constraints", "API Budget (hard rule)", "Shared Interfaces (defined in T1, referenced by all)", "Task 1: Foundation (sonnet)".
- Handoff: `../00_plan/HANDOFF.md`
- Existing files: `../../.gitignore` (maintain it; don't rewrite it).

Do NOT load: other `store/` stage folders, `docs/SPEC.md`, the rest of the plan, the root `main.py` (Task 5 owns it).

## Process
1. Environment: create `.venv` with `python3.12 -m venv .venv` and install from `requirements.txt` into it. Run everything through `.venv/bin/python -m pytest`.
2. Task 1 Step 1: check current syntax with Context7 (the `openai` python SDK: `AsyncOpenAI`, `chat.completions.create`, `response_format` json_schema, `usage`). Check OpenRouter docs for structured outputs, `provider.require_parameters`, how to disable reasoning, and `usage: {include: true}` / where `cost` appears in the response. Record what you find in the HANDOFF.
3. Task 1 Steps 2–5 (TDD). Also add `MAX_RUN_COST_USD`, `BudgetExceeded`, and `LLMError` per "API Budget".
4. **No live API calls at all.** No key exists yet. Every test mocks the raw call.
5. **Do not `git commit`.** Leave the work uncommitted.

## Outputs
- `requirements.txt`, `.env.example`, `storyteller/{__init__,config,models,llm,fake,trace}.py`, `storyteller/prompts/__init__.py`, `tests/conftest.py`, `tests/test_llm.py` (uncommitted)
- Append to `.gitignore` only if you introduce a new generated artifact.
- `HANDOFF.md` here, from `../_templates/HANDOFF.md`

## Done when
`.venv/bin/python -m pytest tests/test_llm.py -v` → all pass, with no network access needed.

## Review check
Confirm: no `temperature` is sent; model is `anthropic/claude-haiku-5.5`; the budget guard raises; validation failures retry and then raise `LLMError`; model field order puts evidence/reason first.
