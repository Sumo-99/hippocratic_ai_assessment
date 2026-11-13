# Character roles: design (short)

## Intent
Trace `runs/revised_trace.json` ("a story about Alice and her cat Bob") showed Bob written as a person. Extraction flattened the request to `["Alice", "Bob"]`, dropping "her cat". The writer and the judge only ever saw that list, so `faithfulness_named` passed because the name "Bob" appeared. A requested detail was lost at the one stage that reads the raw request, and no later stage could catch it.

## Goals
- Preserve each character's **name and role** (species or relationship: "Alice's cat", "a badger") from the request through extraction, writer and judge.
- Make a missing or contradicted role a **hard** failure under `faithfulness_named`.

## Non-goals
- Personality or other traits ("grumpy", "tiny"). Deferred: iterate on this later. The `Character` type should be easy to extend with a field.
- Changing the category, setting or premise handling.

## Anti-goals
- A keyword check in code for the role word (brittle: "kitten", "purred"). The judge does this.
- New false failures on stories that are faithful but never use the exact role word.

## Approaches considered
- **A. Structured `Character {name, role}` end to end.** Chosen.
- B. Keep `list[str]`, role inside the string. Prompt-only, but nothing structured and no place for traits later.
- C. A plus a code-side keyword scan. Rejected as brittle.

## Design
1. `models.py`: add `Character(name: str | None, role: str | None)`. `Extraction.characters` and `StorySpec.characters` become `list[Character]`. A character needs at least one of the two.
   - "Alice and her cat Bob" gives `{Alice, null}`, `{Bob, "Alice's cat"}`.
   - "a grumpy badger" gives `{null, "badger"}` (the trait is dropped for now).
2. `prompts/extract.md`: describe the two fields. Rewrite the "keep only the name" rule so it applies only to bare relationship words of the *requester's* family ("my son"); a role attached to a story character ("her cat Bob") is kept. Update the "my daughter Priya and her dog" example to the new shape.
3. `generate.py`: the writer line renders one entry per character, e.g. `Characters: Alice; Bob (Alice's cat)`. Add one line to the writer prompt: keep each character recognisably what they are, as a role not just a name.
4. `judge.py`: the rubric context renders the same strings. `skipped_dimensions` logic is unchanged (empty list = nothing named).
5. `prompts/judge.md`: `faithfulness_named` also requires each named role to be recognisable in the story (stated, or clearly shown through behaviour). A person-like Bob fails. Stays a hard dimension; the `fix` should say where to change.
6. Tests (FakeLLM only): update fixtures that build `characters=[...]` and the extract-prompt assertions in `tests/test_prompts.py`; add a test that the writer prompt and judge context contain "Bob (Alice's cat)"; update `docs/SPEC.md` line 47 and the ARCHITECTURE note on extraction.

## Constraints
- No live API calls without the user's OK (OpenRouter budget). Verifying the fix against the real model is one live run of the Alice/Bob request, estimated ~$0.003, to be approved separately.
- No commit of generated code before the user has reviewed it.

## Left to the builder
- Exact wording of the prompt changes and the rendering format.
- Whether to validate "at least one of name/role" in the model or leave it to the prompt.
