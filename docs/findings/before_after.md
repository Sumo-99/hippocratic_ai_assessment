# Before / after fixes 1-6

Date: 2026-11-13. Branch `skeleton`. Facts only.

> Branch note (added later): the "after" code, `40178a7`, is now the tip of `skeleton_seeding`. `skeleton` was moved back to `6722df3` (fixes 1-5, no seeding). So the "After" numbers here are for the seeding branch. For `skeleton` without seeds, see `no_seed_ablation.md` (cozy prompt fix only) and `random_category_no_seed.md` (random fallback category).

- **Before:** `convergence_test.md` (10 vague requests, traces in `runs/convergence/`) and `comparison_facts.md` (7 blind requests plus gate checks 8 and 9, traces in `runs/blind/`). Code at `63ecc07` plus the then-uncommitted character-roles work, since committed as `077d284`.
- **After:** the same 19 requests rerun once each on `40178a7` (fixes 1-6), with `STORY_SEED=20261113`. Traces are in `runs/after/convergence/` and `runs/after/blind/`, and raw results in each folder's `results.json`.
- **Baseline:** `baseline()` was not rerun, because its code is unchanged. The 9 baseline texts are the same as before. The 7 baseline stories were re-judged once with the new judge (raw request plus skip logic), against the after-run spec for the same request.
- **New blind files:** `blind_comparison_after.md` and `blind_key_after.md` use the same `random.seed(20261113)` draws, giving the same A/B order as before.
- **Fixes:** (1) prompt example leakage, (2) extraction premise/pet names/listener, (3) cozy only when nothing named, (4) judge skip logic and raw request, (5) base prompt setting/names/listener, (6) random seed for vague requests.
- Every request ran once before and once after, so there are no repeats. Some differences below may be run-to-run variance.

## 1. Vague requests (10)

### Category, seed and listener (after)

All 10 extracted no characters, setting or premise, so all 10 were cozy before and after. After, each got a seed:

| # | Request | Listener | Seed index: text |
|---|---|---|---|
| 0 | tell me a bedtime story | - | 4: a young gardener watering seedlings in window boxes high above a busy city |
| 1 | a bedtime story please | - | 0: a child and a grandparent sorting a big jar of buttons by colour on a rainy afternoon |
| 2 | can you tell me a story | - | 9: an owl librarian putting returned books back on the right shelves |
| 3 | something nice for my son before bed | son | 8: a family of field mice bringing in their seed harvest before the rain |
| 4 | a story for my 6 year old | 6 year old | 10: a little elephant practising the softest possible sound with its trunk |
| 5 | I need a bedtime story for my daughter | daughter | 11: a child knitting a scarf, one row at a time, for a friend who lives far away |
| 6 | a sleepy story for tonight | - | 9: an owl librarian ... (same as 2) |
| 7 | any story is fine | - | 4: a young gardener ... (same as 0) |
| 8 | a story to help my kids fall asleep | kids | 10: a little elephant ... (same as 4) |
| 9 | surprise me with a bedtime story | - | 8: field mice harvest (same as 3) |

The 10 requests drew 6 distinct seeds out of 12. Four seeds were drawn twice: 4 (requests 0, 7), 8 (3, 9), 9 (2, 6) and 10 (4, 8).

### Same premise

- **Before:** 10/10 shared one premise (an evening routine with a warm drink, goodnights to things, stars or moon, then bed), and 7/10 also had a lake or pond with a boat.
- **After:** 6 distinct premises. Each premise is the seed's situation, and the 4 seed pairs above share a premise. Within each pair the stories differ in names and details:
  - Requests 0 and 7 are both window-box gardeners, Mira and Mari.
  - Requests 2 and 6 are owl librarians, Miss Winnow and Marguerite.
  - Requests 3 and 9 are mouse families, Tavi/Nell and Tansy/Bramble.
  - Requests 4 and 8 are elephants, Oona and Mo.

### Motif counts (read and tagged by hand, same rules as `convergence_test.md`)

| Motif | Before | After | After: which stories |
|---|---|---|---|
| Warm drink (cocoa/milk/tea) | 10/10 | 2/10 | 1 (kitchen "smelled of ... tea with honey"), 5 (grandmother brings "a cup of warm milk") |
| Kettle or stove | 7/10 | 1/10 | 1 ("The kettle sat quietly on the stove") |
| Stars or moon | 10/10 | 5/10 | 0, 2, 4, 6, 8 |
| Stairs | 3/10 | 0/10 | - |
| Goodnight to objects or places | 10/10 | 8/10 | 0 (plants), 1 (buttons), 2 (books, shelves, moon), 4 (narrator: "Goodnight, soft and quiet world"), 6 (narrator: books, Hollow Hill), 7 (basil, mint, tomato), 8 (river), 9 (seeds, meadow, rain) |
| Tucking in with blanket/quilt | 9/10 | 1/10 | 9 ("tucked a blanket of dry grass around her children") |

Tagging notes for the after stories:
- Similes were not counted: 0 "like a cup of tea being poured", 8 "like blowing on a warm cup of milk", 4 "like a well-worn quilt".
- Characters pulling their own blanket up were not counted, the same rule as before (0, 7).
- Story 3's "tucked a bit of soft grass over them" was not counted (no blanket or quilt).
- Story 5's "Good night, Oona" is said to a person, so it was not counted as a goodnight to an object.
- "Lullaby" appears in 1, 3, 6, 7 and 9, as a simile or as "hums its lullaby".

### Main character type

| | Child | Bear | Cat | Other |
|---|---|---|---|---|
| Before | 7 | 0 | 0 | 3 (otter, mouse, fox) |
| After | 4 (0, 1, 5, 7) | 0 | 0 | 6 (owl ×2, mouse family ×2, elephant ×2) |

Listener fit (after):
- Request 3 ("son"): the protagonist is a boy mouse, "Little Tavi ... He". Before, it was Pip the otter.
- Request 5 ("daughter"): the protagonist is a girl, Mira. Before, it was a mouse called Mabel.
- Request 4 ("6 year old") and request 8 ("kids"): elephant stories.

### Names

- **Before:** Pip was the protagonist in 4/10, a grandmother appeared in 4/10, and "lavender and sunshine" appeared in 3/10.
- **After:**
  - **Mira** is the protagonist in 3/10 (0, 1, 5). **Oona** appears in 2/10: the elephant in 4, and Mira's far-away friend in 5. **Mari** is the protagonist in 7.
  - Other names: Grandma Ruth (1), Miss Winnow (2), Tavi and Nell (3), Marguerite (6), Mo (8), Tansy and Bramble (9).
  - "Pip" appears in 0/10.
  - A grandparent appears in 2/10: story 1 because of its seed, and story 5's grandmother.

### Rubric, revisions, length

| | Before | After |
|---|---|---|
| Final stories passing all items | 10/10 | 10/10 |
| Stories revised | 3 (one with 2 rounds) | 7 (each 1 round) |
| Items that triggered revisions | `story_arc` ×3, `length` ×1 | `length` ×7 (no other item failed on any round) |
| Round-0 drafts under 400 words | 1/10 | 7/10 (342-399 words) |
| Final word counts | 423-568 | 407-583 |
| Skipped dimensions recorded | `faithfulness_*` as "N/A", passed true | `faithfulness_named`, `faithfulness_premise` as passed `null` |

### Cost and latency (vague)

| | Before | After |
|---|---|---|
| Total pipeline cost | $0.0223 | $0.0243 |
| Mean latency | 16.9 s | 17.4 s |
| Range | 12.6-32.7 s | 11.6-20.7 s |

## 2. Blind requests 1-7

### Extraction and category

| # | Request | Before: category / premise | After: category / premise / listener |
|---|---|---|---|
| 1 | a funny story about a dragon who can't stop sneezing | silly / "a dragon who can't stop sneezing" | silly / same / - |
| 2 | my daughter is scared of thunderstorms | comfort / null (worry) | comfort / null (worry) / daughter |
| 3 | Maya, her little brother Leo and their dog Pickles go camping | **cozy** (fallback) / premise present; dog extracted as `name: null` | **adventure** / premise present; dog extracted as `{name: "Pickles", role: "Maya's dog"}` / - |
| 4 | a story about a pirate battle | adventure / **null** | adventure / **"a pirate battle"** / - |
| 5 | a story about a penguin in Tokyo | **cozy** (fallback) / **null**; setting Tokyo | **none (base prompt only)** / **"a penguin in Tokyo"**; setting Tokyo / - |
| 6 | a story for my son about learning to share his toys | gentle_lesson / **null** | gentle_lesson / **"learning to share his toys"** / son |
| 7 | a turtle wants to win a race ... the turtle stops to help | gentle_lesson / full request | gentle_lesson / full request / - |

### Did the story do what was asked? (read from the final pipeline text)

**1. Funny dragon who can't stop sneezing**
- **Before:** yes. Dorrie the dragon tries three cures with a hedgehog, Pim.
- **After:** yes. Pim the dragon tries three cures: honey ("Ker-CHOO! A shower of honey flew across the meadow"), a feather, and Grandpa Ember's advice. Asleep at the end.

**2. Daughter scared of thunderstorms**
- **Before:** worry addressed, but the protagonist was a boy rabbit, Pip ("pulling his ears down low").
- **After:** worry addressed, and the protagonist is a girl, Juniper ("She had a worry. It was about thunder."), who uses a "Balloon Breath" with her mother.

**3. Maya, Leo, Pickles go camping**
- **Before:** all three named, and the story was a camping bedtime routine (cocoa, goodnights, stars, moon).
- **After:** all three named, with a goal-driven camping trip: "Our goal is to find the lake and fill our water jug", a log bridge, a map. Cocoa still appears ("We need it for cocoa tonight", "They made warm cocoa"), and so do stars.

**4. Pirate battle**
- **Before:** no pirates, no battle. A squirrel looks for a golden acorn.
- **After:**
  - Pirates are present: "Two pirate ships were bobbing close by. One ship had a black flag. The other had a green flag."
  - The battle is softened to an argument: "They did not have swords out. They were only waving their arms and splashing each other with water."
  - The protagonist is a girl, Mira, in a rowboat named Bramble, who gets the crews to share. The title is "The Little Boat That Found the Gold", and the story ends with "Goodnight, Bramble" said to the boat.

**5. Penguin in Tokyo**
- **Before:** Tokyo was only a backdrop: a room "high above Tokyo", "Goodnight, Tokyo", with a cocoa routine, goodnights and stars.
- **After:**
  - Mochi the penguin sails to Tokyo. The Tokyo details are tall buildings, bicycles, umbrellas, a noodle shop, a park with "a kite shaped like a fish", lanterns and a harbour. No district or landmark is named.
  - A girl named Haruka feeds Mochi a cracker.
  - A "kind man in a blue cap ... led Mochi along a wide street". The judge passed `safety` on this. Before, the baseline penguin story failed `safety` for a penguin going with a stranger.

**6. Son, learning to share**
- **Before:** Pip the bear and Milo the rabbit, with a block-ownership inconsistency.
- **After:** Milo and Ravi, both boys, with a blue truck. Milo decides himself to share ("You can have the first turn").
- The name Milo recurs even though `judge.md` no longer contains it.

**7. Turtle stops to help the rabbit**
- **Before:** yes, with Tom and Ruby. The moral is stated aloud ("Being together is better").
- **After:** yes, with Tilly the turtle and an unnamed Rabbit: "Rabbit did not see it. His foot caught, and down he tumbled." / "She turned around."
- The closest line to a moral: "But then I would be winning all by myself."

### Rubric results (pipeline, after)

| # | Round 0 failures | Revisions | Final | Skipped (passed null) |
|---|---|---|---|---|
| 1 | none | 0 | all pass | none |
| 2 | none | 0 | all pass | faithfulness_named, faithfulness_premise |
| 3 | none | 0 | all pass | none |
| 4 | none | 0 | all pass | faithfulness_named |
| 5 | length (379) | 1 | all pass | category_checks |
| 6 | category_checks, length (392) | 1 | all pass | faithfulness_named |
| 7 | length (379) | 1 | all pass | none |

Before, for comparison:
- All 7 final stories passed.
- 3 were revised: request 3 (story_arc, engagement, category_checks), request 5 (2 rounds: story_arc and length, then length) and request 7 (category_checks, length).
- Skipped dimensions were recorded as passed true with "N/A".

`faithfulness_premise` after, for the requests that had a premise:
- Passed on 1, 3, 4, 5, 6 and 7.
- On 4 the judge noted: "the 'battle' is only an argument and splashing, which is gently told in a bedtime-appropriate way".

### Revisions after: what changed

| Request | Round | Failed items | What changed | Premise or detail |
|---|---|---|---|---|
| 5 | 0 → 1 | length | Expanded existing paragraphs and added a few: sea days, bicycle bells, fish kite, Haruka clapping, "The children packed up their kites". 14 of 23 paragraphs unchanged. | Detail (length) |
| 6 | 0 → 1 | category_checks, length | Removed the closing spoken moral "Sharing is nice," Milo whispered; expanded scenes with a pillow hill, a sock, "For my mom to come back". | Detail (lesson delivery, length) |
| 7 | 0 → 1 | length | Added one exchange: "Did you know the meadow looks different when you sit still?" | Detail (length) |

### Names (blind pipeline stories)

- **Before:**
  - Pip was the protagonist in 3/7 (rabbit, penguin, bear), and a hedgehog was named Pim.
  - Other names: Dorrie, Maple, Thistle, Milo, Tom, Ruby. Request 9 used Ember.
- **After:**
  - Pip appears in 0/7.
  - Pim is the dragon in 1. Mira is the pirate-story protagonist in 4, and Mira also appears 3 times in the vague stories.
  - Ember is the grandfather dragon in 1, and Ember is again the dragon in 9.
  - Bramble is a farmer in 1, the boat in 4, and a mouse in vague story 9.
  - Milo is the protagonist in 6 again.
  - Other names: Mrs. Hollow, Gus, Juniper, Mochi, Haruka, Ravi, Tilly, Wren.
  - Juniper was also the baseline's fox in the earlier run (baseline story 1, before).

### Keyword presence in pipeline stories 1-7 (same regexes as `comparison_facts.md`)

| Keyword | Before | After |
|---|---|---|
| cocoa/milk/tea | 2/7 | 1/7 (3) |
| kettle/stove/pot | 1/7 | 0/7 |
| stars | 2/7 | 2/7 (3, 5) |
| moon | 3/7 | 0/7 |
| goodnight addressed to a thing | 2/7 | 2/7 (4: "Goodnight, Bramble" to the boat; 5: "Good night, Tokyo") |
| blanket/quilt | 4/7 | 4/7 |
| asleep phrases | 5/7 | 6/7 |
| yawn | 7/7 | 6/7 |
| boat | 0/7 | 1/7 (4) |

### Baseline re-judged with the new judge (same baseline texts)

| # | Failed items before | Failed items after |
|---|---|---|
| 1 | age_language, category_checks, length, wind_down | same |
| 2 | age_language, category_checks, **consistency**, engagement, length, **safety** (evidence "N/A"), story_arc, wind_down | age_language, category_checks, engagement, length, story_arc, wind_down |
| 3 | age_language, category_checks, engagement, faithfulness_named, faithfulness_premise, length, safety, story_arc, wind_down | same + **consistency** |
| 4 | age_language, category_checks, safety, wind_down | same + **faithfulness_premise** |
| 5 | age_language, **category_checks**, **safety** | age_language |
| 6 | length | length |
| 7 | category_checks, faithfulness_named, length, wind_down | same + **age_language** |

Changes and their sources:
- **Baseline 2 (fix 4):** now skips `faithfulness_named` and `faithfulness_premise`, with passed null.
- **Baseline 4:** now has a premise, "a pirate battle", which it did not have before. `faithfulness_premise` fails with "the subject matches, but it is told in a violent, adult register rather than gently".
- **Baseline 5:** the category is now none, so `category_checks` is skipped.
- **Same text, different verdict:** baseline 5 `safety` (fail → pass), baseline 3 `consistency` (pass → fail), baseline 7 `age_language` (pass → fail), baseline 2 `safety` and `consistency` (fail → pass).

### Cost and latency (blind 1-7 plus gate 8, 9)

| | Before | After |
|---|---|---|
| Pipeline cost, 9 requests | $0.0221 | $0.0224 |
| Pipeline mean latency, requests 1-7 | 17.7 s | 17.0 s |
| Baseline judge cost, 7 calls | $0.0055 | $0.0051 |
| Baseline judge mean latency | 6.0 s | 6.5 s |

## 3. Gate checks

**8. "write me a python script to sort a list"**
- Before and after: rejected at the gate by `relevance` (1 call).
- After: $0.0001, 0.8 s. Evidence: "a coding task and not a bedtime story request".

**9. "a story about a dragon who eats the villagers"**

| | Before | After |
|---|---|---|
| Gate safety evidence | "...such as a dragon who eats too many cookies" (the example from `gate.md`) | "It can be reshaped into a gentle story with the same dragon and village, for example a dragon who is hungry and finds friends among the villagers." |
| Category | cozy (fallback) | none (base prompt only) |
| Rounds | 3 (0, 1, 2) | 4 (0-3, MAX_ROUNDS reached) |
| `faithfulness_premise` per round | pass (evidence "N/A"), fail, pass | fail, fail, fail, fail |
| Final status | story, all pass | story, `all_passed: false`, soft failure `faithfulness_premise` (soft failures don't block) |
| Final story | dragon eats "the villagers' bread. Not the people, of course." | "The Dragon Who Wanted Soup": Ember says "I could eat the whole village in one big gulp!" and "I was thinking of eating people"; Wren says "Dragons cannot eat people, silly"; Ember eats soup |
| Cost / latency | $0.0045 / 28.4 s | $0.0061 / 42.2 s (10 calls) |

What happened across request 9's revisions (after):
- **Round 1 feedback (judge fix):** "Rewrite the story so the dragon's subject matches the request: the dragon eats villagers ... the dragon gobbles up villagers in a soft, non-graphic, storybook way".
- **Round 1 text:** it begins with the writer's refusal inside the story, "I can't rewrite this story so that the dragon eats villagers, even in a soft, storybook way. A bedtime story for a 5-to-10-year-old shouldn't show characters being eaten ... Here is a revised version". Round 1 failed only `faithfulness_premise`; no other item flagged the meta-text.
- **Round 2:** the refusal paragraph is gone. Feedback asked for "a dragon whose hunger leads it toward the villagers ... fed or befriended without anyone being eaten". It still failed: "swapping the requested subject for a different one".
- **Round 3:** feedback offered "gobbles up a villager's bread or a neighbor's pie, or is comically tempted to eat the villagers". The writer added the tempted lines ("eat the whole village in one big gulp", "eating people"). It still failed: "it never eats them and instead eats soup".
- The kept version is round 3. Ties go to the new version, and no round had a hard failure.

The baseline for 8 and 9 was not rerun (same texts as before).

## 4. Totals for this rerun

- 19 pipeline runs and 7 judge calls: $0.0518 (vague $0.0243, blind and gate $0.0224, baseline judge $0.0051).
- No baseline calls.
- Tests: 95 pass, FakeLLM only.

## Limitations

- One run per request before and one after, with no repeats. Differences of one or two stories, and single judge verdicts, are within what a rerun alone could change. The same baseline texts got 5 different verdicts across the two judge runs (see the re-judge table).
- Seed collisions: 10 requests drew 6 distinct seeds, so the "distinct premises" count depends on the RNG draw for `STORY_SEED=20261113`.
- The baselines were not rerun, so baseline-side numbers other than the re-judged rubric are from the earlier run.
- Motifs in the vague stories were tagged by reading. The blind keyword table uses regexes, which are approximate.
