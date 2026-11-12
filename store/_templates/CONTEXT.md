---
stage: NN_name
model: sonnet | opus | haiku | orchestrator
plan_section: "Task N: …"
parallel_with: []
---

# NN_name: {the job in five words}

One job: {the single thing this stage does}.

## Inputs
- Plan (read only this section): `../../docs/plans/2026-11-11-storyteller-skeleton.md` → "{plan_section}", plus "Global Constraints", "API Budget", "Shared Interfaces"
- Handoffs (as built, these override the plan where they differ): `../MM_*/HANDOFF.md`
- Code it may read: {exact paths}

Do NOT load: {other stages' folders, the whole plan, docs/SPEC.md unless named, runs/}

## Process
1. {steps, pointing at the plan's checkboxes rather than copying them}

## Outputs
- Code/files: {exact paths} (left **uncommitted**)
- `HANDOFF.md` in this folder, from `../_templates/HANDOFF.md`

## Done when
{the exact verification command and its expected output}

## Review check
{the one concrete thing the per-task reviewer verifies}
