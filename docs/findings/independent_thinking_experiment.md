# Experiment: let the model choose its own idea for vague requests

Date: 2026-11-12. Branch `skeleton_independent_thinking_experiement` (worktree, not pushed). Facts only.

## Setup

- **Code base:** `skeleton` at `6722df3` (fixes 1-5). The seed step (fix 6) is not on `skeleton`; it exists only as commit `40178a7` on `skeleton_seeding`. So "remove the seed step" needed no code change: this branch starts from a tree that has no seed step.
- **Switch:** `VAGUE_MODE` in `storyteller/config.py`, `off` (as on `skeleton`), `invent` (A) or `options` (B). Both act only when the spec has no characters, setting or premise.
- **Condition A ("invent your own"):** one line added to the variables section of the writer prompt, after the cozy bundle:
  > The request gives no characters, setting or premise. Invent your own: choose characters, a setting and a small situation for this story yourself. Make them specific and fresh rather than the most obvious choice.

  No other prompt was changed.
- **Condition B (model-made options):** before writing, one extra structured call (`storyteller/options.py`, stage `options`, no system prompt beyond the request for options) asks for 5 distinct options for a calm bedtime story, each with characters, setting and a small situation, one line each. Code picks one with `random.Random(f"{seed}:{request}")`, with `OPTIONS_SEED=20261113`. The pick goes into the writer prompt as `Characters:`, `Setting:` and `Premise:` lines. The condition A line is not added. The trace logs the full list, the picked index and the seed (`options` key). The pick is stored as `spec.idea` and **only the writer sees it**: the judge still sees no named characters, setting or premise, so the same judge dimensions are skipped in every condition.
- **Requests:** the same 10 vague requests as `convergence_test.md`, one `pipeline.run()` each, model `anthropic/claude-haiku-5.5`. Runner: `scripts/run_independent.py`.
- **Traces:** `runs/independent/A/` and `runs/independent/B/` (gitignored), each with a `results.json`.
- Extraction returned no characters, setting, premise, worry or category for all 20 runs, so all 20 were cozy and all 20 triggered the condition.
- **Tagging:** every story was read and tagged by hand, using the rules in `convergence_test.md` and `no_seed_ablation.md`. Similes are not counted, nor a character pulling up their own blanket, nor a goodnight said only to a person.
- **Column sources:** Original = `convergence_test.md`. Rewrite + seeds = `before_after.md` ("After", `40178a7`). Rewrite only = `no_seed_ablation.md`. That run's code was `40178a7` with the seed call removed from `pipeline._run`, so its `base.md` still had one extra, unused line about a "Story idea" line. Conditions A and B start from `6722df3`, which lacks that line.
- **One run per request in every column.** Differences of one or two stories may be run-to-run variance.

## Motif counts

| Motif | Original | Rewrite + seeds | Rewrite only | Condition A | Condition B |
|---|---|---|---|---|---|
| Warm drink (cocoa/milk/tea) | 10/10 | 2/10 | 7/10 | 3/10 (2 milk, 6 mint tea, 8 milk) | 0/10 |
| Kettle or stove | 7/10 | 1/10 | 3/10 | 1/10 (9 kettle on stove) | 1/10 (8 wood stove) |
| Stars or moon | 10/10 | 5/10 | 9/10 † | 4/10 (1, 2, 5, 7) | 7/10 (0, 1, 2, 4, 6, 8, 9) |
| Stairs | 3/10 | 0/10 | 0/10 | 0/10 | 1/10 (4, stairs up to the roof) |
| Goodnight to objects or places | 10/10 | 8/10 | 8/10 | 8/10 (0, 2, 3, 4, 5, 6, 7, 8) | 3/10 (5 snowflakes, 8 lake and rain, 9 garden) |
| Tucked in with blanket/quilt | 9/10 | 1/10 | 1/10 | 3/10 (1, 6, 8) | 2/10 (0, 8) |

† Rewrite only: 5/10 had real stars or moon in the sky and 4 more had only star patterns on a lantern. Conditions A and B count the real sky only; on the ablation's looser rule, A would be 5/10 (9 has stars cut into a lantern's tin) and B stays 7/10.

Tagging notes for A and B:
- A: similes not counted: 2 "like a kettle thinking about boiling", 6 "like a kettle cooling on the stove", 7 "like a blanket tucked just right". A9 fills a kettle on the stove but nobody drinks anything, so it counts for Stove but not for Drink.
- A0: the grandmother tucks a corner of her shawl under Mira's chin. A shawl is not a blanket or quilt, so N. A5 tucks her own feet under a shawl, so N. A9 pulls her own blanket over her knees, so N.
- A1: "Hello, lantern" and "Hello, star", but no goodnight to an object, so N. A1's three wooden steps are outside the back door: not counted, the same rule as the porch steps before.
- B: goodnights said only to animals were not counted: 3 (a sparrow, and the snowman Bramble as a character) and 6 (the hens). Counting animals, B would be 5/10.
- B1 "tucked her in beside the clover", B3 "Ada was tucked in" and B7 the mother curls around her cub: no blanket or quilt, so N. B2's toes are under a quilt, but nobody tucks him in, so N.
- B6: the bread is in an oven, with no kettle or stove, so N. B6's song lyric "the moon has come" is in the story text, and stars also appear in its narration.

## Per-story facts: condition A

| # | Request | Title | Setting | One-line premise | Main character (type, name) | Others |
|---|---|---|---|---|---|---|
| 0 | tell me a bedtime story | The Lantern Garden | small house by a pond; garden with reeds | Mira sits with her grandmother on a bench by the pond at dusk, says goodnight to pond/reeds/lantern, sleeps | girl, Mira | grandmother Oona |
| 1 | a bedtime story please | The Lantern Garden | house in a village; lantern garden with an apple tree | Mira and her grandmother sit among paper lanterns; Mira wishes to see the first star, sees it, is tucked in | girl, Mira | Oma Tessaly |
| 2 | can you tell me a story | The Quiet Lantern | house with a round blue door on a hill | An old clockmaker fixes her stopped clock, drinks warm milk by the window with her cat, falls asleep | old woman, Mabel Rooke | cat Thimble, a moth |
| 3 | something nice for my son before bed | The Lantern Boat on Willow Pond | reed house on Willow Pond | An otter sets his lantern boat drifting and wonders where it goes; it bumps home into the reeds; he sleeps | otter (male), Mo | heron Ilsa |
| 4 | a story for my 6 year old | The Quiet Lighthouse Garden | Marigold Hollow, a garden next to a lighthouse | A snail climbs a grass stalk at dusk, watches the lighthouse beam with a ladybug, both sleep | snail, Tobin | ladybug Wren |
| 5 | I need a bedtime story for my daughter | The Quiet Lantern Garden | house on a green hill; garden of paper lanterns, apple tree | Mira and her grandmother walk the lantern garden, sit on a bench, say goodnight to star/garden | girl, Mira | Oma Ruth |
| 6 | a sleepy story for tonight | The Lantern Garden | small green house on a hill; grandmother's garden | Mira and her grandmother (with mint tea) watch fireflies from a bench; Mira is tucked in and sleeps there | girl, Mira | Oma Ansel |
| 7 | any story is fine | The Quiet Lantern Garden | house with a green door; garden with a pond | A tortoise and a humming grandmother walk to the pond with a paper lantern, watch the moon in the water, go home | tortoise, Marlow | grandmother Ada, a moth |
| 8 | a story to help my kids fall asleep | The Quiet Lantern | small house by the sea; blue window seat | A fox wishes to really look at a boat's light on the water; with warm milk and her grandmother she finds it; tucked in | fox (female), Mabel Thorne | Grandma |
| 9 | surprise me with a bedtime story | The Quiet Lantern Shop | Mossbell Lantern House, a shop with a round green door on a hill | Old Hesper wants every lantern lit before dark, lights them one by one, sleeps in her chair with her cat | old woman, Hesper | cat Thimble |

## Per-story facts: condition B

| # | Picked option (index) | Title | Setting | One-line premise | Main character (type, name) | Others |
|---|---|---|---|---|---|---|
| 0 | 2 | The Cloud Castle Stroll | cloud castle above green hills | Theo and a dragon walk a cloud path toward the river, step over a gap, don't reach the river, go home at dusk | boy, Theo | dragon Moss |
| 1 | 0 | Pip and the Sleepy Fireflies | meadow under a silver moon | A hedgehog who can't sleep counts fireflies to seven with her tortoise grandmother and falls asleep | hedgehog (female), Pip | tortoise Gran Shell |
| 2 | 4 | The Cloud Bear | Leo's bedroom with a crescent-moon nightlight | Leo imagines floating over the sleeping town on his teddy bear's back until he sleeps | boy, Leo | teddy bear Tobin |
| 3 | 4 | Bramble and Ada in the Snow Garden | winter garden with a streetlamp and an apple tree | A talking snowman and a girl build a snow nest for the birds; she goes in to bed | snowman (male), Bramble; girl, Ada | a sparrow |
| 4 | 1 | Nia and the Rooftop Garden | rooftop garden above a sleeping city | Nia and her grandpa water tomatoes and lavender, count fireflies to ten as the stars come out | girl, Nia | Grandpa |
| 5 | 3 | Rory and the Gentle Snow | snowy meadow | A bear cub fears the first snow will hurt; his mother shows him how gently it falls; goodnight to snowflakes | bear cub (male), Rory | Mother Hazel |
| 6 | 4 | Bolt and the Hens | farmhouse kitchen and hen house | A robot helps a farmer shut the hens in and sings them a lullaby | robot, Bolt | Mrs. Haddock; hens Clover, Dot, Biscuit |
| 7 | 2 | Snowfall in the Mountain Cave | moss-lined cave in snowy mountains | A shy bear cub hears snow falling; his mother tells him each snowflake has its own song | bear cub (male), Tomas | mother Rosa |
| 8 | 3 | The Lakeside Lullaby | lakeside cabin with a wood stove and rocking chair | A bear rocks a duckling to sleep under a quilt while rain taps the window | bear, Oswin | duckling Dot |
| 9 | 4 | Juniper and the Sleepy Frogs | walled garden with a fountain and an apple tree | A girl walks the garden at dusk, greets a frog family, plants a seed, says goodnight to the garden | girl, Juniper | frog family |

All 10 B stories use the picked option's characters (with the option's names), setting and situation.

## Distinct premises and shared template

**Condition A**
- **Shared plot shape, 10/10:** dusk at a home or its garden; slow description of sounds, smells and light; the main character falls asleep there. 3/10 add a small wish or task: 1 (see the first star), 8 (look at the boat's light), 9 (light every lantern). 2 fixes a stopped clock.
- **Premises:** about 6 distinct. Five stories (0, 1, 5, 6, 7) share one: a grandmother and a child or small animal sit in a garden among lanterns or fireflies at dusk until the child sleeps. The other five each have their own: 2 the clockmaker, 3 the otter's lantern boat, 4 the snail in the lighthouse garden, 8 the fox watching a boat light, 9 the lantern shop.
- **Titles:** 9/10 contain "Lantern" (all but 4, which has "Lighthouse"). Some repeat exactly: "The Lantern Garden" ×3 (0, 1, 6), "The Quiet Lantern Garden" ×2 (5, 7), "The Quiet Lantern" ×2 (2, 8). 6/10 contain "Quiet" (2, 4, 5, 7, 8, 9).
- **A lantern in the story:** 9/10 (all but 4; 4 has a lighthouse beam instead).
- **Names:** the main character is named Mira in 4/10 (0, 1, 5, 6), and all four are a girl with her grandmother. The grandmother is called "Oma" in 3 (1, 5, 6). A grey cat named Thimble appears in 2 (2, 9). The name Mabel is used twice (2 Mabel Rooke, 8 Mabel Thorne). Ada is used once (7, the grandmother). Pip 0/10.
- **Grandmother present:** 6/10 (0, 1, 5, 6, 7, 8).
- **Garden as the main setting:** 6/10 (0, 1, 4, 5, 6, 7). A house on a hill: 4/10 (2, 5, 6, 9).
- **Other repeated details:**
  - lavender: 6/10 (0, 2, 4, 6, 8, 9)
  - cedar smell: 5/10 (0, 1, 5, 8, 9)
  - frogs: 5/10 (0, 3, 4, 6, 7)
  - a moth: 4/10 (1, 2, 3, 7)
  - a bench: 4/10 (0, 5, 6, 7)
  - a dog that "barked once, then stopped": 3/10 (1, 6, 8)
  - a round green or blue door: 4/10 (1 green, 2 blue, 7 green, 9 round green)
  - a blue window seat: 2/10 (1, 8)
  - honey-coloured lantern light: 3/10 (0, 1, 7)
  - an owl's single "hoo": 3/10 (2, 3, 7)
- **Main character type:** girl 4 (0, 1, 5, 6), old woman 2 (2, 9), animal 4 (otter, snail, tortoise, fox). How the listener showed up: 3 "son" → a male otter. 5 "daughter" → Mira, a girl. 4 "6 year old" → a snail. 8 "kids" → a fox.

**Condition B**
- **Premises:** 10 distinct, one per pick. Two pairs overlap:
  - 5 and 7 are both a bear cub with his mother in a snowy place, the mother explaining falling snowflakes.
  - 0 and 2 are both a boy on a slow journey through clouds above sleeping land.
  - Fireflies are counted in 2 stories (1 to seven, 4 to ten).
- **Titles:** no repeats. 0/10 contain "Lantern" or "Quiet". 6/10 start with the main character's name (1, 3, 4, 5, 6, 9).
- **Snow setting:** 3/10 (3, 5, 7). **Garden:** 3/10 (3, 4, 9). **Bear:** 4/10 (2 teddy, 5, 7, 8).
- **Names:** Pip 1/10 (1, from the option). Dot appears twice (6 a hen, 8 a duckling). Other names appear once each. Ada is used once (3).
- **Grandparent present:** 2/10 (1 grandmother, 4 grandfather). A mother: 2/10 (5, 7).
- **Repeated details:**
  - lavender: 3/10 (2, 4, 9)
  - an apple tree: 2/10 (3, 9)
  - warm bread: 3/10 (6, 8, 9)
  - a dog that "barked once": 2/10 (2, 4)
  - cedar: 1/10 (2)
  - a moth: 0/10
- **Main character type:** boy 2 (0, 2), girl 3 (3 shares the lead with a snowman, 4, 9), animal 4 (hedgehog, two bear cubs, bear), robot 1. How the listener showed up: 3 "son" → a male snowman with a girl. 5 "daughter" → a male bear cub. 4 "6 year old" → Nia, a girl. 8 "kids" → a bear and a duckling.
- **Plot shape:** 10/10 end with the characters asleep or going to bed. 7/10 have a small goal or worry:
  - 0: reach the river, and a gap in the path
  - 1: can't sleep
  - 3: build a nest
  - 4: water the plants
  - 5: fear of snow
  - 6: shut the hens in
  - 9: plant a seed

  The other 3 (2, 7, 8) are calm scenes.

## Condition B: do the 5-option lists repeat across requests?

Each request made its own options call, so 10 lists of 5 options. Counts are lists out of 10 that contain the item:

| Item | Lists | Detail |
|---|---|---|
| Option 0 is a small woodland animal at night under the moon (owl, hedgehog, fox) | 10/10 | owl + field mouse (0, 2, 3), hedgehog (1, 6, 9), fox (5, 7, 8), owl + hedgehog (4) |
| A character named Pip | 9/10 | in option 0 in 8 lists (0, 1, 2, 3, 5, 6, 7, 8); a robot Pip in list 4; none in list 9 |
| Option 0 is "can't fall asleep" | 6/10 | 1, 2, 5, 7, 8, 9 (list 0: "so he can finally fall asleep") |
| Option 0 has a grandmother | 6/10 | 1, 5, 6, 7, 8, 9 (list 0 mentions a grandmother's lullaby) |
| "silver moon" in option 0 | 5/10 | 0, 1, 2, 5, 7 |
| Counting fireflies/leaves/stars to fall asleep, in option 0 | 4/10 | fireflies 1, 2, 5; leaves 7 |
| Same owl + mouse pair "Hattie and Pip" in an oak forest | 3/10 | 0, 2, 3 |
| A moon anywhere in the list | 10/10 | |
| Snow or a snowy place | 8/10 | all but 0 and 8; "snowy meadow" in 4 (2, 4, 5, 9); a bear cub in snow in 4 (5, 6, 7, 9) |
| Fireflies | 7/10 | 0, 1, 2, 4, 5, 7, 8 |
| A lighthouse | 6/10 | 0, 2, 3, 6, 7, 9; a girl with a lighthouse-keeping grandfather or keeper in 3 (0, 2, 7), two named Mira |
| A robot | 6/10 | 0, 4, 5, 6, 7, 8; named Bolt in 3 (0, 6, 8) |
| A dragon | 3/10 | 0 Moss, 2 Ember, 3 Ember |
| A gentle giant | 3/10 | 1 Oswin, 2 Bram, 5 Bram |
| A sea turtle | 3/10 | 4, 5, 8 |
| A child with a teddy bear in a bedroom | 2/10 | 1, 2 |
| A music box in an attic | 2/10 | 5, 8 |

- Names that recur across lists: Pip (9 lists), Mira (4: 1, 2, 7, 8), Ada (4: 3, 6, 8, 9), Hattie (3), Ember (3), Bramble (3), Clover (3), Bolt (3), Oswin (2), Bram (2), Hollis (2), Teo (2), Tobin (2), Lila (2), Lina (2), Oscar (2), Biscuit (2), Dot (2).
- Within one list the 5 options always differ from each other in species, setting and situation.
- Picks by request 0-9: 2, 0, 4, 4, 1, 3, 4, 2, 3, 4. Option 0 (the woodland-animal slot) was picked once (request 1, the hedgehog Pip), and option 4 four times (2, 3, 6, 9).

## First drafts, revisions, cost and latency (vague requests, pipeline only)

| | Original | Rewrite + seeds | Rewrite only | Condition A | Condition B |
|---|---|---|---|---|---|
| First-draft words, mean | 458 | 398 | 431 | 429 | 445 |
| First-draft words, range | 336-555 | 342-502 | 338-531 | 374-490 | 396-529 |
| First drafts under 400 words | 1/10 | 7/10 | 3/10 | 4/10 | 1/10 |
| Runs with 0 / 1 / 2 / 3 revisions | 7 / 2 / 1 / 0 | 3 / 7 / 0 / 0 | 2 / 7 / 0 / 1 | 4 / 6 / 0 / 0 | 8 / 2 / 0 / 0 |
| Round-0 failures | story_arc ×2, length ×1 | (see before_after.md) | (see no_seed_ablation.md) | story_arc ×5, length ×4 | story_arc ×1, length ×1 |
| Final stories passing every rubric item | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| Total cost | $0.0223 | $0.0243 | $0.0302 | $0.0249 | $0.0223 |
| Mean latency | 16.9 s | 17.4 s | 20.7 s | 16.9 s | 17.6 s |
| Latency range | 12.6-32.7 s | 11.6-20.7 s | 11.9-39.1 s | 11.5-20.7 s | 14.8-26.6 s |

- First-draft figures for Original, Rewrite + seeds and Rewrite only were recomputed from their traces (`runs/convergence/`, `runs/after/convergence/`, `runs/noseed/convergence/`).
- A: round-0 failures were story_arc in 1, 2, 3, 8, 9 and length in 3 (385), 4 (399), 8 (374), 9 (380). Every revision passed on the first try.
- B: round-0 failures were story_arc in 0 and length in 2 (396). B0's final version is 695 words.
- B's options call cost $0.0030 in total over 10 runs (about $0.0003 each) and took 3.4-5.5 s per run. It is included in B's totals.
- No run went over the latency budget. Cost for this experiment: $0.0472 (A $0.0249 + B $0.0223).
- One run per request in every column; no repeats.
