# Experiment: random fallback category (no seeds)

Branch `skeleton_random_category` (worktree `../hippocratic_ai_assessment-random-category`), cut from `skeleton` at `6722df3`. Not committed or merged.

## Change

- `make_spec`: when extraction gives **no premise and no category**, the category is picked at random from `config.FALLBACK_CATEGORIES = ("cozy", "adventure", "silly")`. Previously it was always cozy, and only when nothing at all was named. A premise with an unclear category still gets no category (base prompt alone).
- `pipeline._run` logs the pick in the trace as `category_pick`.
- `make_spec` takes an optional `rng` for tests and reproducible runs. Unit test updated; 89 pass (6 repeated runs).
- No seeds. Prompts unchanged from `skeleton`.

## Run

Same 10 vague requests as `convergence_test.md`, one pipeline run each, no baseline. Traces in `runs/randcat/convergence/` (gitignored). Total cost **$0.0275**. Mean latency **19.2 s**, range 13.1-34.2 s.

Columns: **Before** = original code. **Seeds** = `skeleton_seeding` (`before_after.md`, "After"). **Cozy only** = `skeleton` without seeds (`no_seed_ablation.md`). **Random cat** = this run.

## Categories used

| # | Request | Extraction category | Final category |
|---|---|---|---|
| 0 | tell me a bedtime story | none | adventure (random) |
| 1 | a bedtime story please | none | adventure (random) |
| 2 | can you tell me a story | none | silly (random) |
| 3 | something nice for my son before bed | none | adventure (random) |
| 4 | a story for my 6 year old | none | silly (random) |
| 5 | I need a bedtime story for my daughter | none | cozy (random) |
| 6 | a sleepy story for tonight | **cozy** | cozy (from extraction) |
| 7 | any story is fine | none | adventure (random) |
| 8 | a story to help my kids fall asleep | **cozy** | cozy (from extraction) |
| 9 | surprise me with a bedtime story | none | adventure (random) |

8 of 10 went through the random pick: adventure 5, silly 2, cozy 1. Requests 6 and 8 ("sleepy", "fall asleep") were classified cozy by extraction, so no random pick.

## Motif counts (read and tagged by hand, same rules as before)

| Motif | Before | Seeds | Cozy only | Random cat | Random cat: which stories |
|---|---|---|---|---|---|
| Warm drink | 10/10 | 2/10 | 7/10 | 3/10 | 5 (milk), 6 (tea), 7 (milk, in the ending) |
| Kettle or stove | 7/10 | 1/10 | 3/10 | 1/10 | 8 ("warm from the stove") |
| Stars or moon | 10/10 | 5/10 | 9/10 | 8/10 | 0, 1, 2, 3, 5, 7, 8, 9 |
| Stairs | 3/10 | 0/10 | 0/10 | 1/10 | 8 |
| Goodnight to objects or places | 10/10 | 8/10 | 8/10 | 4/10 | 3 (lantern, world), 5 (garden, moth), 6 (moth), 8 (lamp, stars) |
| Tucking in with blanket/quilt | 9/10 | 1/10 | 1/10 | 3/10 | 6 (grandmother), 8 (mother), 9 (grandpa) |

Tagging notes:
- Goodnight to a person or animal characters only was not counted: 0, 2, 7, 9 (to the protagonist), 4 ("Good night, Mabel ... hens ... ducks, and good night, little one").
- Story 2's "tucked a leaf over Mo's nose, like a tiny blanket" was not counted. Characters wrapping themselves were not counted (0, 3).

## New repeated elements

**Adventure stories (5: 0, 1, 3, 7, 9) share one plot:**

| Element | Count | Stories |
|---|---|---|
| A lantern is lost or goes dark; the child goes to bring it (or its light source) back | 5/5 | 0, 1, 3, 7, 9 |
| A grandparent owns the lantern / sends or waits for the child | 5/5 | 0 grandpa, 1 grandpa, 3 grandmother, 7 grandma, 9 grandpa |
| Water crossing as an obstacle (creek, stream, rope bridge, lake current) | 5/5 | 0, 1, 3, 7, 9 |
| Helping a small stuck or hurt animal | 5/5 | 0 rabbit with thorn, 1 mouse under branch, 3 rabbit ear in thorns, 7 fox's lost key, 9 duckling wing in reeds |
| A riddle or "answer me to pass" gate | 3/5 | 1, 3, 7 |
| Ends with the lantern back on its hook, glowing | 5/5 | 0, 1, 3, 7, 9 |

adventure.md's Do list reads: "Do make each obstacle different (a river to cross, a riddle, a friend who needs help)." These are the three obstacles in the stories above.

**Silly stories (2: 2, 4):** both are an animal with a wish to get off the ground (moose: dance on the moon; cow: fly), three attempts ending in hay, mud or a puddle, then sleep while dreaming of it. silly.md's setup example is "a cow who wants to fly"; story 4 is a cow who wants to fly.

**Across all 10:**
- "Lantern" in the title: 6/10 (0, 1, 3, 7, 8, 9). A lantern or lamp in the story: 9/10 (all but 2 and 4; 6 and 8 have a lamp).
- Blue house or cottage: 4/10 (5, 7, 8; 6 has a blue door).
- Moth at a window or fence: 3/10 (5, 6, 8; all cozy).
- The cozy stories (5, 6, 8) resemble the `no_seed_ablation.md` cozy template: an evening at a window or step, warm drink or stove, moth, goodnights.

## Rubric and rounds

| # | Category | Rounds | Round-by-round hard / soft failures |
|---|---|---|---|
| 0 | adventure | 0 | clean |
| 1 | adventure | 1 | r0 safety; r1 clean |
| 2 | silly | 1 | r0 safety; r1 clean |
| 3 | adventure | 0 | clean |
| 4 | silly | 0 | clean |
| 5 | cozy | 1 | r0 length (395 words); r1 clean |
| 6 | cozy | 0 | clean |
| 7 | adventure | 0 | clean |
| 8 | cozy | 2 | r0 story_arc; r1 safety; r2 clean |
| 9 | adventure | 2 | r0 safety; r1 safety + category_checks; r2 clean |

- Final versions: 10/10 shown as stories, no hard or soft failures.
- Safety failures (round, evidence summary): 1 r0 rushing water at a stone crossing; 2 r0 high balloon ride and tall pot tower; 8 r1 the fox goes into the garden alone at dusk; 9 r0 and r1 the child rows alone on a lake at night.
- Safety passed on first try in 0 (child goes alone into the woods at evening and crosses a slippery creek) and 3 (child crosses a "cold and fast" stream on a log alone at dusk).
- First drafts under 400 words: 1/10 (5). Cozy only: 3/10. Seeds: 7/10.

## Main character and names

| | Child | Other |
|---|---|---|
| Before | 7 | 3 |
| Seeds | 4 | 6 |
| Cozy only | 8 | 2 |
| Random cat | 7 (girls 0, 1, 5, 7, 9; boys 3, 6) | 3 (moose 2, cow 4, fox 8) |

- Names: Mira (0, 9), Maya (1), Mo (2), Tobin (3), Mabel (4), Wren (5), Finn (6), Juniper (7), Marlow (8). Pip 0/10.
- Title/name mismatch: 0 is titled "Maple and the Lost Lantern" but the girl is Mira; 4 is titled "Biscuit the Bouncing Cow" but the cow is Mabel. Neither was flagged by `consistency`.
- Listener fit: 3 "son" → Tobin, a boy. 5 "daughter" → Wren, a girl. 4 "6 year old" → a cow. 8 "kids" → a fox.

## Cost and latency (vague, pipeline only)

| | Before | Seeds | Cozy only | Random cat |
|---|---|---|---|---|
| Total cost | $0.0223 | $0.0243 | $0.0302 | $0.0275 |
| Mean latency | 16.9 s | 17.4 s | 20.7 s | 19.2 s |
| Range | 12.6-32.7 s | 11.6-20.7 s | 11.9-39.1 s | 13.1-34.2 s |

One run per request in every column, so differences of one or two stories may be noise.

---

# Run 2: adventure.md and silly.md examples removed

## Change (on top of run 1)

- adventure.md: the goal hint "(find, deliver, reach, return something)" and the obstacle examples "(a river to cross, a riddle, a friend who needs help)" were replaced by abstract guidance: invent a goal that fits this character; obstacles grow out of this story's place and goal; each obstacle a different kind of problem (thinking, kindness, teamwork).
- silly.md: "(a cow who wants to fly, a teapot who sneezes bubbles)" was replaced by "invent both the character and the wish fresh"; the sound-word examples "(boing, splat, whoosh)" were replaced by "sound words invented to match what is happening".
- The no-leak prompt test now also checks for "river to cross", "riddle", "cow who wants to fly", "teapot", "boing". 89 tests pass.
- "Lantern" does not appear in any prompt, before or after.

## Run

Same 10 requests. To compare like with like, each request was pinned to the **same category as run 1** (adventure 0, 1, 3, 7, 9; silly 2, 4; cozy 5 by pick, 6 and 8 by extraction, which again returned cozy). Traces in `runs/randcat2/convergence/`. Cost **$0.0262**. Mean latency **18.5 s**, range 13.6-33.3 s.

## Adventure stories (0, 1, 3, 7, 9)

| Element | Run 1 | Run 2 | Run 2 stories |
|---|---|---|---|
| Goal: bring back a lost or dark light (lantern, its light, lighthouse key) | 5/5 | 4/5 | 0 lantern light, 3 lighthouse lamp key, 7 lantern glow-moss, 9 "moth lantern". 1 is a silver acorn |
| Lantern specifically | 5/5 | 3/5 | 0, 7, 9 |
| A grandparent sends or waits for the child | 5/5 | 4/5 | 0, 1, 3, 7 |
| Water crossing | 5/5 | 4/5 | 0 muddy stream (log), 1 river (pole), 3 puddle (stones), 9 rushing stream (branch). 7 fills a dry ditch with stones |
| Helping a small stuck or lost animal | 5/5 | 4/5 | 0 lost hedgehog, 3 crab stuck in a crack, 7 rabbit with heavy basket, 9 hedgehog snagged in thorns |
| Riddle | 3/5 | 0/5 | - |
| Protagonist named Mira | 2/5 | 3/5 | 0, 7, 9 |
| Red scarf or red boots | 4/5 | 4/5 | 1, 3, 7, 9 |
| Glowing moss as the light source | 1/5 | 2/5 | 0, 7 |

## Silly stories (2, 4)

- 2: Mabel the hen wants to fly to the moon. Attempts: flapping, jumping off a fence into the duck pond, a hay "rocket" ending in a hay pile. Uses "Whoosh!" and "Boing!".
- 4: Old Mr. Tumbleweed wants to fly. Attempts: jumping off the table into porridge, an umbrella, a hat with socks. Uses "Whoosh!".
- Both wishes are to fly (run 1: both to leave the ground, one a cow who wants to fly). The name Mabel recurs (run 1: Mabel the cow).

## Cozy stories (5, 6, 8)

- 5: a girl in a blue attic room, a toy rabbit's ear caught on a splinter, kettle downstairs, moon, goodnights.
- 6: "The Quiet Little Lighthouse Cottage", a seaside cottage named **Marram House**, a girl and her grandmother, a lost shell, kettle on the stove, a warm cup, stairs, tucked in. Run 1's story 6 was "The Quiet Lighthouse Cottage"; `no_seed_ablation.md` story 7 was "The Quiet Lighthouse Cottage" with a cottage named Marram House.
- 8: "The Quiet Little Lighthouse", a cat named **Marigold** watching a little boat come home. `no_seed_ablation.md` story 6 also has a cat named Marigold.

## Motif counts

| Motif | Before | Seeds | Cozy only | Random cat run 1 | Random cat run 2 | Run 2 stories |
|---|---|---|---|---|---|---|
| Warm drink | 10/10 | 2/10 | 7/10 | 3/10 | 2/10 | 6 (cup from the kettle), 7 (milk) |
| Kettle or stove | 7/10 | 1/10 | 3/10 | 1/10 | 2/10 | 5, 6 |
| Stars or moon | 10/10 | 5/10 | 9/10 | 8/10 | 6/10 | 0, 1, 2, 5, 6, 9 |
| Stairs (climbing) | 3/10 | 0/10 | 0/10 | 1/10 | 2/10 | 3 (lighthouse), 6 |
| Goodnight to objects or places | 10/10 | 8/10 | 8/10 | 4/10 | 9/10 | all but 8 |
| Tucking in by someone else | 9/10 | 1/10 | 1/10 | 3/10 | 2/10 | 3, 6 |

Tagging notes: similes not counted (9 "purring like a warm kettle", 7 "like a tiny star"). 8 says "Good evening, sea", not counted. 5's "floated up the stairs" (a tune) not counted as climbing stairs.

## Rubric and rounds

- Rounds: 0 rounds in 5 (1, 2, 3, 7, 9); 1 round in 4 (4, 5, 6, 8); 2 rounds in 1 (0). Final versions: 10/10 stories, no hard or soft failures.
- Safety failures: 0 r0 and r1 (child out alone, at night); 4 r0 (falls into prickly bushes, "Ouch, ouch, ouch").
- Safety passed on first try in 9 (Mira "slipped out the back door" alone into the evening and crossed a stream where "the water rushed") and 7 (climbs a ladder up an oak).
- Round 0 failures in the 3 cozy stories were story_arc + length (374-395 words). First drafts under 400 words: 3/10.

## Names and main character

- Mira 3/10 (0, 7, 9), Wren 2/10 (5, 6), plus Juniper, Mabel, Oscar, Mr. Tumbleweed (dog Pickle), Marigold. Pip 0/10.
- Juniper also led run 1's story 7. Mira led run 1's 0 and 9.
- Child protagonist 7/10 (girls 0, 1, 5, 6, 7, 9; boy 3); other 3 (hen, old man, cat).
- Listener fit: 3 "son" → Oscar, a boy. 5 "daughter" → Wren, a girl. 4 "6 year old" → an old man. 8 "kids" → a cat.

## Cost and latency

| | Random cat run 1 | Random cat run 2 |
|---|---|---|
| Total cost | $0.0275 | $0.0262 |
| Mean latency | 19.2 s | 18.5 s |
| Range | 13.1-34.2 s | 13.6-33.3 s |

One run per request, so differences of one or two stories may be noise.
