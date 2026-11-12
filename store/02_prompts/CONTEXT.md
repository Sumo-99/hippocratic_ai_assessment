---
stage: 02_prompts
model: opus
plan_section: "Task 2: Prompt templates (opus)"
parallel_with: [03_stages, 04_evaluation]
---

# 02_prompts: write every prompt template

One job: write the `string.Template` prompt files that decide story quality, plus a test showing each file fills in with exactly the placeholders the plan lists.

## Inputs
- Plan: `../../docs/plans/2026-11-11-storyteller-skeleton.md`. Read only "Global Constraints", "Task 2: Prompt templates (opus)" (its placeholder table is the contract), and "Shared Interfaces" (so prompts match the model fields, e.g. `Verdict{evidence, passed, fix}`, `JudgeResult` field names, `Comparison{reason, winner}`).
- Spec, read for content: `../../docs/SPEC.md` "Architecture" §1–6 (gate, extraction rules, brainstorm, BASE and CATEGORY bundles, rubric dimensions).
- Handoff: `../01_foundation/HANDOFF.md`
- Code: `../../storyteller/prompts/__init__.py` (the `load(name)` you fill files for).

Do NOT load: other stage folders, the rest of the plan, Python modules other than `prompts/__init__.py`.

## Process
1. TDD: write `tests/test_prompts.py` first (plan Step 1), then run it and watch it fail.
2. Write the 13 `.md` files in `storyteller/prompts/`. Base prompt length line: "about 500–700 words" using `$target_words` (600). The judge prompt names every `JudgeResult` field and defines hard vs soft dimensions, the skip rule (evidence "N/A", passed true), evidence → passed → fix order, and that a fix must say *where* in the story. Never mention revisions to the judge.
3. Write prompts that are explicit and concrete, kid-safe, and short enough that a human can read them all in 10 minutes. A literal `$` in prose must be written `$$`.
4. No live API calls. Do not `git add` or `git commit`. Don't edit `tests/conftest.py`, `storyteller/models.py` or `config.py`; put any needed change in the HANDOFF instead.

## Outputs
- `storyteller/prompts/*.md` (13 files), `tests/test_prompts.py` (uncommitted)
- `HANDOFF.md` here. In "Open issues / for the human reviewer", list the 3 prompt choices you're least sure of.

## Done when
`.venv/bin/python -m pytest tests/test_prompts.py -v` → all pass.

## Review check
Each category file has Structure / Do-Don't / Judge checks sections. The comfort prompt never says "nothing to be scared of". The gate prompt doesn't reject reshape-able requests. Placeholders match the plan's table exactly.
