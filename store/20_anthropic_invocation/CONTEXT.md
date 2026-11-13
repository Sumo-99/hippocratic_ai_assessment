---
stage: 20_anthropic_invocation
model: sonnet (code), opus (final review)
plan_section: "Tasks 0-6"
parallel_with: []
---

# 20_anthropic_invocation: direct Anthropic API backend

One job: add `AnthropicClient` behind a `build_client()` factory and `LLM_PROVIDER`, with OpenRouter as the default and its behaviour unchanged.

## Inputs
- Plan: `../../docs/plans/2026-11-13-anthropic-invocation.md` (the whole plan; it is small). Base is `skeleton` at **8ce1517** (the plan text says a084a1a; the wrapper files are identical in both).
- Code it may read: `storyteller/llm.py`, `storyteller/config.py`, `storyteller/pipeline.py` (only the `OpenRouterClient` lines), `tests/test_llm.py`, `tests/test_pipeline.py` (only the two monkeypatch lines), `tests/conftest.py`.

Do NOT load: other stages' folders, `docs/SPEC.md`, `runs/`, `.env`.

## Environment
- Worktree: `/Users/sumanthramesh/Documents/dev/hippocratic_takehome/hippocratic_ai_assessment-anthropic` (branch `anthropic_invocation`).
- Python: the main checkout's venv, `PY=/Users/sumanthramesh/Documents/dev/hippocratic_takehome/hippocratic_ai_assessment/.venv/bin/python`. `anthropic` 2.8.0 is installed there (it uses `httpx2`; `openai` uses `httpx`).
- Baseline before any change: **210 passed**.

## Progress (RESUME HERE: update after every finished step)
- [x] Task 0: worktree, `anthropic>=2,<3` in requirements, `.env.example`, CLAUDE.md rows, this file
- [x] Task 1: `BaseLLMClient` + `RetryableError` in `llm.py`; `tests/test_llm.py` unmodified and green (210 passed)
- [x] Task 2: config additions + `storyteller/llm_anthropic.py` + `tests/test_llm_anthropic.py` (220 passed)
- [x] Task 3: `storyteller/clients.py` (`build_client`), pipeline swap, `test_pipeline.py` target rename, `tests/test_clients.py`, `tests/test_llm_contract.py` (237 passed)
- [x] Task 4: README + OPEN_QUESTIONS, `HANDOFF.md` (status in_progress until Task 6)
- [ ] Opus review of the whole diff (switch the session model to opus first)
- [ ] Task 5: live smoke (needs the user's OK; the user puts `ANTHROPIC_API_KEY` in this worktree's `.env`)
- [ ] Task 6: user review, then commit

Next step: Opus review of `git diff skeleton` (code is written and green, 237 passed). Then ask the user for the live-smoke OK.

## Outputs
- Code left **uncommitted** until the user's review (Task 6). Notes in `store/` may be committed.
- `HANDOFF.md` in this folder.

## Done when
`$PY -m pytest -q` is all green, `git diff --stat skeleton -- tests/test_llm.py` is empty, and the live smoke runs cleanly.

## Review check
OpenRouter path byte-for-byte unchanged (request kwargs, error messages); only `clients.py` names concrete clients.
