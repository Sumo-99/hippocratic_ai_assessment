# Hippocratic AI Coding Assignment
Welcome to the [Hippocratic AI](https://www.hippocraticai.com) coding assignment

## Instructions
The attached code is a simple python script skeleton. Your goal is to take any simple bedtime story request and use prompting to tell a story appropriate for ages 5 to 10.
- Incorporate a LLM judge to improve the quality of the story
- Provide a block diagram of the system you create that illustrates the flow of the prompts and the interaction between judge, storyteller, user, and any other components you add
- Do not change the openAI model that is being used. 
- Please use your own openAI key, but do not include it in your final submission.
- Otherwise, you may change any code you like or add any files

---

## Rules
- This assignment is open-ended
- You may use any resources you like with the following restrictions
   - They must be resources that would be available to you if you worked here (so no other humans, no closed AIs, no unlicensed code, etc.)
   - Allowed resources include but not limited to Stack overflow, random blogs, chatGPT et al
   - You have to be able to explain how the code works, even if chatGPT wrote it
- DO NOT PUSH THE API KEY TO GITHUB. OpenAI will automatically delete it

---

## What does "tell a story" mean?
It should be appropriate for ages 5-10. Other than that it's up to you. Here are some ideas to help get the brain-juices flowing!
- Use story arcs to tell better stories
- Allow the user to provide feedback or request changes
- Categorize the request and use a tailored generation strategy for each category

---

## How will I be evaluated
Good question. We want to know the following:
- The efficacy of the system you design to create a good story
- Are you comfortable using and writing a python script
- What kinds of prompting strategies and agent design strategies do you use
- Are the stories your tool creates good?
- Can you understand and deconstruct a problem
- Can you operate in an open-ended environment
- Can you surprise us

---

## Other FAQs
- How long should I spend on this? 
No more than 2-3 hours
- Can I change what the input is? 
Sure
- How long should the story be?
You decide
---

## Running this solution

Requires Python 3.12.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then put your OpenRouter key in OPENROUTER_API_KEY
```

Run it:

```bash
python main.py "A story about a shy dragon who loves baking"
python main.py "..." --verbose     # also prints the per-stage summary read from the trace
python main.py "..." --baseline    # single plain model call, no pipeline (for comparison)
pytest                             # unit tests, fake LLM, no network or API key needed
```

- Traces: every pipeline run writes a JSON trace to `runs/` (override with `RUNS_DIR`). It holds the request, gate result, extraction, every story version with its judge verdicts and the feedback it was revised from, the guard's keep decisions, timings, token usage and cost. `--baseline` writes none.
- Cost guard: `MAX_RUN_COST_USD` (default 0.10) stops a run once its spend passes the cap and returns a friendly message. Other knobs (`MAX_ROUNDS`, `TARGET_WORDS`, `MAX_TOKENS`, `LATENCY_BUDGET_S`) can be overridden in the shell or in `.env`. The model and endpoint are fixed in `storyteller/config.py` on purpose.
- Design: see `docs/ARCHITECTURE.md` (diagrams) and `docs/OPEN_QUESTIONS.md` (decisions and deferred items).
