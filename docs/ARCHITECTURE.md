# Architecture (DRAFT for the author to refine)

> Status: first-pass diagrams written from the build handoffs, not hand-tuned. Names and boxes match the code in `storyteller/`.

## Legend

```mermaid
flowchart LR
    L1["LLM call"]:::llm
    L2["Plain code"]:::code
    L3["Input / output / file"]:::io
    classDef llm fill:#cfe8ff,stroke:#1f6feb,color:#0b2a55
    classDef code fill:#e6f4d7,stroke:#3b8a1f,color:#173d0a
    classDef io fill:#f3f3f3,stroke:#666,color:#222
```

Blue = one or more LLM calls (all use the same model, Haiku 5.5 via OpenRouter). Green = deterministic code. Grey = user-facing input/output or a file.

## Diagram 1: end to end

```mermaid
flowchart TD
    U["User request"]:::io
    GATE["Gate: is this a bedtime story request?"]:::llm
    REJ["Friendly rejection message"]:::io
    EXT["Extraction: category, characters, setting, premise, mood, worry"]:::llm
    NORM["Normalize and plan drafts"]:::code
    BRANCH{"Premise given?"}:::code
    BRAIN["Premise brainstorm: 3 distinct premises seen at once"]:::llm
    DEPTH["Depth: 1 draft spec"]:::code
    BREADTH["Breadth: 3 draft specs"]:::code
    RUBRIC["Rubric: 4 hard + 6 soft checks"]:::code
    DRAFT["Per-draft loop, 1 or 3 in parallel: write, evaluate, revise, keep better. See Diagram 2"]:::llm
    SAFE{"Does any draft pass safety?"}:::code
    FB["Safety fallback: one fresh cozy story, one evaluation"]:::llm
    FBOK{"Fallback passes safety?"}:::code
    CANNED["Canned safe message"]:::io
    SEL["Selection: drafts passing all hard checks compete by pairwise wins (both orders), then fewer soft failures, then index. If none pass, the safe draft with fewest hard failures"]:::llm
    OUT["Story shown to user"]:::io
    TRACE[("runs/ trace JSON")]:::io

    U --> GATE
    GATE -->|rejected| REJ
    REJ -->|"asks again"| U
    GATE -->|accepted| EXT
    EXT --> NORM --> BRANCH
    BRANCH -->|yes: depth| DEPTH
    BRANCH -->|no: breadth| BRAIN --> BREADTH
    DEPTH --> DRAFT
    BREADTH --> DRAFT
    RUBRIC -.-> DRAFT
    DRAFT --> SAFE
    SAFE -->|none| FB --> FBOK
    FBOK -->|yes| OUT
    FBOK -->|no| CANNED
    SAFE -->|some| SEL --> OUT
    CANNED --> OUT

    GATE -.-> TRACE
    EXT -.-> TRACE
    DRAFT -.-> TRACE
    SEL -.-> TRACE
    FB -.-> TRACE
    OUT -.-> TRACE

    classDef llm fill:#cfe8ff,stroke:#1f6feb,color:#0b2a55
    classDef code fill:#e6f4d7,stroke:#3b8a1f,color:#173d0a
    classDef io fill:#f3f3f3,stroke:#666,color:#222
```

Notes:
- If the budget guard trips (`BudgetExceeded`), `run` returns a friendly message with `status="error"` and still writes the trace. It is not drawn above to keep the picture readable.
- Dotted arrows into the trace mean "recorded"; the trace is written once in a `finally` at the end of `run`.

## Diagram 2: inside one draft

```mermaid
flowchart TD
    SPEC["Draft spec: category, premise, characters, setting, mood"]:::io
    ASM["Prompt assembly: base.md + category file + variables"]:::code
    GEN["Storyteller writes round 0"]:::llm
    EV["Evaluate: length check in code, then one rubric judge call"]:::llm
    PASS{"All checks pass?"}:::code
    KEEP["Keep this version as final for the draft"]:::code
    FBK["Feedback builder: hard failures first, then soft"]:::code
    REV["Revise: story + feedback, rewrite"]:::llm
    EV2["Evaluate the revision"]:::llm
    CMP["Keep better: passing safety wins, then fewer hard failures, else pairwise in both orders, ties keep previous"]:::llm
    RND{"Round below MAX_ROUNDS?"}:::code
    DONE["Draft result: kept version + all versions and comparisons"]:::io

    SPEC --> ASM --> GEN --> EV --> PASS
    PASS -->|yes| KEEP --> DONE
    PASS -->|no| FBK --> REV --> EV2 --> CMP --> RND
    RND -->|"yes: feedback from kept version"| PASSK{"Kept version passes?"}:::code
    PASSK -->|yes| DONE
    PASSK -->|no| FBK
    RND -->|no| DONE

    classDef llm fill:#cfe8ff,stroke:#1f6feb,color:#0b2a55
    classDef code fill:#e6f4d7,stroke:#3b8a1f,color:#173d0a
    classDef io fill:#f3f3f3,stroke:#666,color:#222
```

## Rubric

One structured judge call returns every LLM-judged dimension with evidence written before the verdict. Failures are recomputed in code from each `passed` flag.

| Dimension | Hard / soft | Judged by | Skip rule |
|---|---|---|---|
| safety | hard | LLM | never skipped |
| wind_down | hard | LLM | never skipped |
| faithfulness_named | hard | LLM | skipped when the user named no characters and no setting (settings the brainstorm invents don't count) |
| consistency | hard | LLM | never skipped |
| age_language | soft | LLM | never skipped |
| story_arc | soft | LLM | never skipped |
| engagement | soft | LLM | never skipped |
| faithfulness_premise_mood | soft | LLM | skipped when no premise and no mood |
| category_checks | soft | LLM | uses the `## Judge checks` list of the category file |
| length | soft | code | word count outside 400-900 fails; no LLM call |

Skipped dimensions are told to the judge (evidence "N/A", passed true) and dropped again in code.

## Cost and latency guards

- One model for every call; no temperature (the model does not accept it). Diversity comes from the brainstorm, not sampling.
- `MAX_RUN_COST_USD` (default 0.10) is checked before and after each call; `BudgetExceeded` ends the run with a friendly message and a saved trace.
- Drafts run in parallel (`asyncio.gather`); pairwise comparisons run both orders concurrently.
- Early stop: a draft stops revising as soon as its kept version passes everything. `MAX_ROUNDS` (default 3) caps revisions.
- Fewer hard failures decides without a comparison call.
- Retries only on 429, 5xx, connection errors and schema-validation failures; other 4xx fail fast.
- `LATENCY_BUDGET_S` (default 60) is only recorded in the trace as `latency_budget_exceeded`; nothing acts on it.
- Worst case with MAX_ROUNDS=3 in breadth is roughly 51 calls.
