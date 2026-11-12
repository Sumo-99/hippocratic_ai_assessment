# store/: build-stage context store

This folder holds the working memory for building the storyteller skeleton. Each stage folder has a **contract** (`CONTEXT.md`, what to read, do and write) and, once the stage is done, a **handoff** (`HANDOFF.md`, what was actually built). A cold agent or human should never need the chat history.

## Where things live
- Spec: `../docs/SPEC.md`. Plan: `../docs/plans/2026-11-11-storyteller-skeleton.md`
- Stage templates: `_templates/CONTEXT.md`, `_templates/HANDOFF.md`
- Event log (append-only, one line per event): `LOG.md`

## Stages (numbering = plan wave order; same prefix digit group = may run in parallel)

| Folder | Plan section | Model | Runs with |
|---|---|---|---|
| `00_plan/` | Spec + plan written | (me) | — |
| `01_foundation/` | Task 1 | sonnet | — |
| `02_prompts/` | Task 2 | opus | 03, 04 |
| `03_stages/` | Task 3 | sonnet | 02, 04 |
| `04_evaluation/` | Task 4 | sonnet | 02, 03 |
| `05_pipeline/` | Task 5 | opus | — |
| `06_docs/` | Task 6 | sonnet | 07 |
| `07_live_runs/` | Task 7 | haiku | 06 |
| `08_auto_review/` | Wave 5 | opus | — |
| `09_human_review/` | Wave 6 | (me + user) | — |
| `09_simplify/` | Author-requested trim to one draft, no LLM comparison | (me) | — |
| `10_commit_pr/` | Waves 6–7 commit/push | (me) | — |

## Status
Status comes from the files that exist. A stage is **done** iff its `HANDOFF.md` exists and its frontmatter has `status: done`. It is **in progress** iff `CONTEXT.md` exists but `HANDOFF.md` doesn't. It is **not started** iff its folder has no `CONTEXT.md` yet. Check with: `ls store/*/HANDOFF.md`.

## Loading rule (keep each step at ~2k–8k tokens)
An agent working on stage NN reads only these files:
1. this file
2. `NN_*/CONTEXT.md`
3. the `HANDOFF.md` files that its contract lists as inputs
4. the plan section its contract names

It reads nothing else: no other stages' contracts, no full plan, no chat.
