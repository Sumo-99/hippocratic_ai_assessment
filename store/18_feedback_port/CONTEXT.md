---
stage: 18_feedback_port
model: orchestrator
plan_section: "n/a: port of stages 11-17 onto the minified skeleton (a084a1a)"
parallel_with: []
---

# 18_feedback_port: move the feedback feature onto the three-rule skeleton

One job: re-base the uncommitted feedback work (built on `a3ebb70`) onto `skeleton` at `a084a1a` ("Minification #2": three rules, no worry, gentle_lesson or cozy fallback, `StorySpec(Extraction)`).

## Inputs
- Old work: `old_base/tracked_changes.patch` (17 tracked files) + `old_base/new_files.tgz` (overrides.py and 3 test files). Also kept as `git stash` entry "WIP on user_feedback_feature: a3ebb70".
- Requirements: `../11_feedback_contracts/CONTEXT.md`. Design as it stood: `../17_feedback_live_smoke/HANDOFF.md`.

## Done when
`.venv/bin/python -m pytest -q` is all green on `user_feedback_feature` = `skeleton` + uncommitted port.
