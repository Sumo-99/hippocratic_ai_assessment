---
stage: 06_docs
model: sonnet
plan_section: "Task 6: Docs (sonnet), in parallel with T7"
parallel_with: [07_live_runs]
---

# 06_docs: architecture diagrams, open questions, run instructions

One job: write the draft block diagram the assignment requires, compile every `# DECISION:` into one list, and add run instructions.

## Inputs
- Plan: `../../docs/plans/2026-11-11-storyteller-skeleton.md`. Read only "Task 6".
- Spec: `../../docs/SPEC.md`. Read only the "Structure (suggested…)" bullet about `docs/ARCHITECTURE.md` (the diagram requirements) and "Deferred".
- Handoffs, the source of truth for what was built: `../01_foundation/HANDOFF.md` … `../05_pipeline/HANDOFF.md` (especially 05's data-flow paragraph).
- Code: only `grep -rn "DECISION:\|TODO(" storyteller main.py` and the `HARD`/`SOFT` lists in `storyteller/config.py`. Don't read whole modules.
- `../../README.md`: append only. The original assignment text stays untouched above your section.

Do NOT load: `runs/`, `.env`, `store/07_live_runs/`, test files.

## Process
1. `docs/ARCHITECTURE.md`:
   - Diagram 1, end to end: user; gate with a reject path back to the user; extraction; depth/breadth diamond with the brainstorm; the per-draft loop as ONE box (×1 or ×3, in parallel); selection; the all-fail-safety check leading to the cozy fallback, then the canned message; output; the trace written to `runs/`. Show the rubric as a small box.
   - Diagram 2, inside one draft: prompt assembly (base + category + variables) → storyteller → evaluation (length code + rubric judge) → all pass? → feedback builder (hard-first) → revise → evaluate → keep-better (hard count, then two-order pairwise) → round < MAX_ROUNDS?
   - Mermaid `classDef llm` vs `classDef code` with distinct fills, and a legend.
   - The rubric table: dimension | hard/soft | judged by LLM/code | skip rule.
   - A short "Cost & latency guards" note.
   - Mark it as a draft for the author to refine.
2. `docs/OPEN_QUESTIONS.md`: one entry per `# DECISION:` (file:line, what was chosen, the alternative), plus the spec overrides (OpenRouter, no temperature) and every `TODO(...)` deferred hook.
3. README: append `## Running this solution` (venv with python3.12, `pip install -r requirements.txt`, `cp .env.example .env` and add the key, `python main.py "…"`, `--verbose`, `--baseline`, `pytest`, where traces go, the cost guard).
4. Check that the Mermaid parses: `npx -y @mermaid-js/mermaid-cli -i <tmpfile> -o <tmpfile>.svg` in the scratch dir if it's available offline-fast; otherwise reason through the syntax carefully. **No API calls.** Do not `git add` or `git commit`.

## Outputs
- `docs/ARCHITECTURE.md`, `docs/OPEN_QUESTIONS.md`, appended `README.md` (uncommitted)
- `HANDOFF.md` here

## Done when
Both diagrams render or parse. Every `# DECISION:` from the grep appears in OPEN_QUESTIONS.md. The original README text is byte-identical above the new section (`git diff README.md` shows only additions at the end).

## Review check
Diagram 1 has the reject path, the brainstorm, the fallback exit and the trace. LLM steps and code steps are colored differently.
