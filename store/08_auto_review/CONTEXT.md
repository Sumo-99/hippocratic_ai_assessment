---
stage: 08_auto_review
model: opus
plan_section: "Wave 5: Automated review (orchestrator + opus reviewer)"
parallel_with: []
---

# 08_auto_review: independent review of the whole working tree

One job: find real defects in the uncommitted implementation, checked against the spec and plan, and report them. **Read-only: don't edit any file except this stage's `HANDOFF.md`.**

## Inputs
- Spec: `../../docs/SPEC.md` (the overrides at the top win over the brief)
- Plan: `../../docs/plans/2026-11-11-storyteller-skeleton.md`. Read "Global Constraints", "API Budget", "Review Focus", "Shared Interfaces".
- All handoffs: `../0[1-7]_*/HANDOFF.md`. Their "Interfaces as built" and "Decisions" are intentional; don't re-report a documented DECISION unless it is actually wrong.
- Code: `../../storyteller/**`, `../../main.py`, `../../tests/**`, `../../requirements.txt`, `../../.gitignore`, `../../.env.example`
- One real trace: `../../runs/samples/worry.json` (shape only)

Do NOT load or print: `.env`. Don't make any network calls and don't run `main.py` (it would spend money). `pytest` is fine; it's offline.

## Process
1. Run `.venv/bin/python -m pytest -q`.
2. Check against the spec, in priority order:
   - **Safety.** Can an unsafe story ever reach the user? Trace every return path of `pipeline.run`.
   - **Money.** Can any path spend without the budget guard, retry endlessly, or create more than one client per run?
   - **Correctness of the spec rules:**
     - hard-first feedback;
     - keep-better order and two-order pairwise, with a tie keeping the previous draft;
     - selection: survivors only, a tie gives no win, then fewer soft failures, then index;
     - the MAX_ROUNDS cap;
     - the depth/breadth routing and the fixed category set;
     - skip rules;
     - the judge is never told a draft is a revision.
   - **Secrets.** No key in code, traces, or tracked files. `.env` is ignored.
   - **Async.** Drafts are actually concurrent, and there's no shared mutable state race in Trace.
   - **Readability.** Flag only things the author would struggle to explain.
3. For each finding: verify it by reading the exact code path (and write a tiny offline test in your scratch dir if that helps; don't add it to `tests/`). Report only CONFIRMED or clearly PLAUSIBLE defects.

## Outputs
- `HANDOFF.md` here, from `../_templates/HANDOFF.md`. Replace "Built" with a **Findings** table: # | severity (high/med/low) | file:line | defect | concrete failure scenario | suggested fix | CONFIRMED/PLAUSIBLE. Sort most severe first, at most 12 rows. Then a short "Checked and fine" list.

## Done when
HANDOFF.md exists with the findings table and the pytest result.

## Review check
The orchestrator re-verifies each finding before fixing it.
