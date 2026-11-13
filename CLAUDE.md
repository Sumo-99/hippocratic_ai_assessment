# Bedtime storyteller (Hippocratic AI take-home)

Before any work in this repo, read this file. It explains the rules and the `store/` folder, the build's working memory. A cold agent or human should never need the chat history.

## Standing rules
- **No live API calls without the user's OK.** The OpenRouter budget is $10 total, for the build and the evals. Before any live run, state how many runs and the estimated cost, then wait. Tests use `FakeLLM` only.
- **No commits of generated code before the user has reviewed it.** Notes in `store/` may be committed as they change.
- **Never open, print or echo `.env`.** The code reads the key itself.
- Run tests with `.venv/bin/python -m pytest -q`.

## Branches
- `main`: the original assignment `README.md` and `main.py`, unchanged.
- `skeleton`: the simplified first version (one draft, rubric judge, code-only regression guard).
- `skeleton_extensive`: the full first build (3 drafts, brainstorm, LLM pairwise comparison).
- `user_feedback_feature` (from `skeleton` at a084a1a, the three-rule flow): post-story feedback loop. Plan: `docs/plans/2026-11-13-user-feedback.md`; port notes: `store/18_feedback_port/`.

## Where things live
- Spec: `docs/SPEC.md`. Plan: `docs/plans/2026-11-11-storyteller-skeleton.md`
- Design: `docs/ARCHITECTURE.md` (diagrams). Decisions, deferred work and the eval backlog: `docs/OPEN_QUESTIONS.md`
- Context store: `store/`. Each stage folder has a **contract** (`CONTEXT.md`: what to read, do and write) and, once the stage is done, a **handoff** (`HANDOFF.md`: what was actually built).
- Stage templates: `store/_templates/CONTEXT.md`, `store/_templates/HANDOFF.md`
- Event log (append-only, one line per event): `store/LOG.md`

## Stages (numbering = plan wave order; the same leading digit = may run in parallel)

| Folder | Plan section | Model | Runs with |
|---|---|---|---|
| `store/00_plan/` | Spec + plan written | (orchestrator) | — |
| `store/01_foundation/` | Task 1 | sonnet | — |
| `store/02_prompts/` | Task 2 | opus | 03, 04 |
| `store/03_stages/` | Task 3 | sonnet | 02, 04 |
| `store/04_evaluation/` | Task 4 | sonnet | 02, 03 |
| `store/05_pipeline/` | Task 5 | opus | — |
| `store/06_docs/` | Task 6 | sonnet | 07 |
| `store/07_live_runs/` | Task 7 | haiku | 06 |
| `store/08_auto_review/` | Wave 5 | opus | — |
| `store/09_human_review/` | Wave 6 | (orchestrator + user) | — |
| `store/09_simplify/` | Author-requested trim to one draft, no LLM comparison | (orchestrator) | — |
| `store/10_commit_pr/` | Waves 6–7 commit/push | (orchestrator) | — |
| `store/11_feedback_contracts/` | Feedback plan Task 0 (shared types; holds requirements R1–R11) | (orchestrator) | — |
| `store/12_feedback_overrides/` | Feedback plan Task 1 | sonnet | 13, 14 |
| `store/13_feedback_prompts/` | Feedback plan Task 2 | opus | 12, 14 |
| `store/14_feedback_loop/` | Feedback plan Task 3 | opus | 12, 13 |
| `store/15_feedback_docs/` | Feedback plan Task 4 | haiku | 16 |
| `store/16_feedback_review/` | Feedback plan Task 5 | opus | 15 |
| `store/17_feedback_live_smoke/` | Live smoke test of the feedback loop (author-approved) | (orchestrator) | — |
| `store/18_feedback_port/` | Port of the feedback feature onto the three-rule skeleton (a084a1a) | (orchestrator) | — |
| `store/19_feedback_review_fixes/` | Author review fixes: override rename, always-a-session, feedback framing, TODOs out | (orchestrator) | — |

## Status
Status comes from the files that exist:
- **Done:** the stage's `HANDOFF.md` exists and its frontmatter has `status: done`.
- **In progress:** `CONTEXT.md` exists but `HANDOFF.md` doesn't.
- **Not started:** the folder has no `CONTEXT.md` yet.

Check with: `ls store/*/HANDOFF.md`.

## Loading rule (keep each step at ~2k–8k tokens)
An agent working on stage NN reads only these files:
1. this file
2. `store/NN_*/CONTEXT.md`
3. the `HANDOFF.md` files that its contract lists as inputs
4. the plan section its contract names

It reads nothing else: no other stages' contracts, no full plan, no chat. When a stage finishes, write its `HANDOFF.md` from the template and append a line to `store/LOG.md`.
