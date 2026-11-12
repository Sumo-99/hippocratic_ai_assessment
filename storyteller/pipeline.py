"""The whole story flow: gate -> extract -> depth/breadth -> parallel draft loops -> selection
-> safety fallback. `run(request)` is the one public entry; the CLI and an eval script both use it.
Every run writes a JSON trace to config.RUNS_DIR, even when it fails."""
import asyncio
import time
from itertools import combinations

from . import config
from .brainstorm import brainstorm
from .compare import compare_both_orders, keep_better
from .extract import extract, plan_drafts
from .feedback import build_feedback
from .gate import check_request, gate_message
from .generate import breadth_specs, depth_spec, revise_story, write_story
from .judge import evaluate
from .llm import BudgetExceeded, LLMClient, OpenRouterClient
from .models import Draft, DraftVersion, Extraction, PipelineResult
from .trace import Trace

CANNED_SAFETY_MESSAGE = (
    "I'm sorry, I couldn't make a story for that request that I'm happy to tell at bedtime. "
    "Could you try a different idea?")
BUDGET_MESSAGE = (
    "Sorry, this story was getting too expensive to make, so I stopped. "
    "Please try again, maybe with a simpler request.")


async def _all_or_cancel(coros) -> list:
    """Run coroutines concurrently. If one fails, cancel the rest and re-raise that error.

    Plain asyncio.gather would leave the other drafts running (and spending money) after a
    failure; a TaskGroup cancels them. TaskGroup wraps errors in an ExceptionGroup, so we
    unwrap the first one to keep `except BudgetExceeded` in `run()` simple."""
    try:
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(c) for c in coros]
    except ExceptionGroup as group:
        raise group.exceptions[0] from None
    return [t.result() for t in tasks]


# ---- one draft: write, judge, revise up to MAX_ROUNDS times ------------------------------

async def run_draft(llm, spec, index: int, trace: Trace) -> Draft:
    with trace.stage(f"draft_{index}"):
        text = await write_story(llm, spec)
        first = DraftVersion(round=0, text=text, evaluation=await evaluate(llm, spec, text),
                             feedback_sent=None)
        # TODO(critique-check): an open-ended "what would a parent dislike?" pass would go
        # here, after evaluate. Deferred until evals show the rubric misses things.
        versions, comparisons, kept = [first], [], first

        for rnd in range(1, config.MAX_ROUNDS + 1):
            if kept.evaluation.all_passed:
                break  # nothing to fix: no more judge or compare calls for this draft
            feedback = build_feedback(kept.evaluation)
            new_text = await revise_story(llm, spec, kept.text, feedback)
            # DECISION: `feedback_sent` is stored on the version it PRODUCED (the feedback
            # this revision was asked to address), so round 0 has none.
            new = DraftVersion(round=rnd, text=new_text,
                               evaluation=await evaluate(llm, spec, new_text),
                               feedback_sent=feedback)
            versions.append(new)
            kept, record = await keep_better(llm, kept, new)  # next round starts from `kept`
            comparisons.append({"round": rnd, **record})

    trace.append("drafts", {
        "index": index, "spec": spec.model_dump(),
        "versions": [v.model_dump() for v in versions],
        "comparisons": comparisons, "kept_round": kept.round,
    })
    return Draft(index=index, spec=spec, versions=versions, kept=kept)


# ---- selection across drafts -------------------------------------------------------------

def _soft(d: Draft) -> int:
    return len(d.kept.evaluation.soft_failures)


def _hard(d: Draft) -> int:
    return len(d.kept.evaluation.hard_failures)


async def _rank_by_wins(llm, drafts: list[Draft], record: dict) -> Draft:
    """Compare every pair (both orders, all at once), count wins, then sort with tiebreaks."""
    if len(drafts) == 1:
        return drafts[0]
    pairs = list(combinations(drafts, 2))
    verdicts = await _all_or_cancel(
        compare_both_orders(llm, x.kept.text, y.kept.text) for x, y in pairs)
    wins = {d.index: 0 for d in drafts}
    for (x, y), verdict in zip(pairs, verdicts):
        if verdict == "x":
            wins[x.index] += 1
        elif verdict == "y":
            wins[y.index] += 1
        # a tie (the two orders disagreed) gives nobody a win
    record["pairs"] = [{"x": x.index, "y": y.index, "verdict": v}
                       for (x, y), v in zip(pairs, verdicts)]
    record["wins"] = wins
    # More wins first, then fewer soft failures, then the earlier draft.
    return sorted(drafts, key=lambda d: (-wins[d.index], _soft(d), d.index))[0]


async def best_available(llm, drafts: list[Draft], record: dict) -> Draft:
    """Every draft fails some hard check: pick the least bad one (never a safety failure)."""
    # DECISION: drafts failing SAFETY are dropped first even if they have the fewest hard
    # failures, because an unsafe story must never be shown. `run` only calls selection when
    # at least one draft passes safety, so this list is never empty there.
    safe = [d for d in drafts if "safety" not in d.kept.evaluation.hard_failures] or drafts
    fewest = min(_hard(d) for d in safe)
    tied = [d for d in safe if _hard(d) == fewest]
    # DECISION: when 2 or 3 drafts tie on hard failures, reuse the same win counting as normal
    # selection (pairwise both orders, then soft failures, then index) rather than a new rule.
    return await _rank_by_wins(llm, tied, record)


async def select(llm, drafts: list[Draft], trace: Trace | None = None) -> Draft:
    """Pick the final draft. One draft: no selection step and no calls."""
    if len(drafts) == 1:
        return drafts[0]
    record: dict = {}
    survivors = [d for d in drafts if not d.kept.evaluation.hard_failures]
    if survivors:
        record["rule"] = "survivors"
        record["survivors"] = [d.index for d in survivors]
        chosen = await _rank_by_wins(llm, survivors, record)
    else:
        record["rule"] = "best_available"
        chosen = await best_available(llm, drafts, record)
    record["chosen"] = chosen.index
    if trace is not None:
        trace.set("selection", record)
    return chosen


# ---- safety fallback ---------------------------------------------------------------------

async def _safety_fallback(llm, e: Extraction, trace: Trace) -> PipelineResult:
    # TODO(safety-fallback): first pass. One fresh cozy draft (no premise), one evaluation,
    # no revisions. A later version might retry or soften the request instead.
    spec = depth_spec(e).model_copy(update={"category": "cozy", "premise": None})
    with trace.stage("fallback"):
        text = await write_story(llm, spec)
        ev = await evaluate(llm, spec, text)
    trace.set("fallback", {"spec": spec.model_dump(), "text": text,
                           "evaluation": ev.model_dump()})
    if "safety" in ev.hard_failures:
        trace.set("final", {"status": "safety_fallback_message",
                            "reason": "every draft and the cozy fallback failed safety"})
        return PipelineResult(status="safety_fallback_message", story=None,
                              message=CANNED_SAFETY_MESSAGE, trace_path=None)
    # The fallback passed safety; other failures are tolerated (it gets no revisions).
    trace.set("final", {"status": "story", "source": "fallback",
                        "all_passed": ev.all_passed, "hard_failures": ev.hard_failures,
                        "soft_failures": ev.soft_failures})
    return PipelineResult(status="story", story=text, message=None, trace_path=None)


# ---- the whole run -----------------------------------------------------------------------

async def _run(request: str, llm, trace: Trace) -> PipelineResult:
    with trace.stage("gate"):
        g = await check_request(llm, request)
    trace.set("gate", g.model_dump())
    rejection = gate_message(g)
    if rejection:
        trace.set("final", {"status": "rejected"})
        return PipelineResult(status="rejected", story=None, message=rejection, trace_path=None)

    with trace.stage("extract"):
        e = await extract(llm, request)
    trace.set("extraction", e.model_dump())

    branch = plan_drafts(e)
    trace.set("branch", branch)
    if branch == "depth":
        specs = [depth_spec(e)]
    else:
        with trace.stage("brainstorm"):
            premises = await brainstorm(llm, e)
        trace.set("premises", [p.model_dump() for p in premises])
        specs = breadth_specs(e, premises)

    with trace.stage("drafts"):  # wall clock for all drafts together (they run in parallel)
        drafts = await _all_or_cancel(run_draft(llm, s, i, trace) for i, s in enumerate(specs))
    trace.data["drafts"].sort(key=lambda d: d["index"])  # drafts finish in any order

    if all("safety" in d.kept.evaluation.hard_failures for d in drafts):
        return await _safety_fallback(llm, e, trace)

    with trace.stage("selection"):
        chosen = await select(llm, list(drafts), trace)
    ev = chosen.kept.evaluation
    trace.set("final", {"status": "story", "source": "draft", "draft_index": chosen.index,
                        "round": chosen.kept.round, "all_passed": ev.all_passed,
                        "hard_failures": ev.hard_failures, "soft_failures": ev.soft_failures})
    return PipelineResult(status="story", story=chosen.kept.text, message=None, trace_path=None)


def _usage_summary(calls: list[dict]) -> dict:
    """Token and cost totals, overall and per stage, from the client's on_usage records."""
    by_stage: dict[str, dict] = {}
    for c in calls:
        s = by_stage.setdefault(c["stage"], {"calls": 0, "prompt_tokens": 0,
                                             "completion_tokens": 0, "cost_usd": 0.0})
        s["calls"] += 1
        s["prompt_tokens"] += c["prompt_tokens"]
        s["completion_tokens"] += c["completion_tokens"]
        s["cost_usd"] += c["cost_usd"]
    return {"calls": len(calls),
            "prompt_tokens": sum(s["prompt_tokens"] for s in by_stage.values()),
            "completion_tokens": sum(s["completion_tokens"] for s in by_stage.values()),
            "by_stage": by_stage}


async def run(request: str, llm: LLMClient | None = None) -> PipelineResult:
    trace = Trace(request)
    start = time.monotonic()
    try:
        if llm is None:
            # One fresh client per run: its total_cost (the budget guard) is per instance.
            # Created inside `try` so a missing key still writes a trace.
            llm = OpenRouterClient(on_usage=trace.on_usage)
        result = await _run(request, llm, trace)
    except BudgetExceeded as exc:
        # DECISION: running out of budget is expected behaviour, not a crash: tell the user
        # kindly and keep the trace. Other errors (e.g. LLMError) still raise to the caller.
        trace.set("error", f"BudgetExceeded: {exc}")
        trace.set("final", {"status": "error"})
        result = PipelineResult(status="error", story=None, message=BUDGET_MESSAGE,
                                trace_path=None)
    finally:  # the trace is written whatever happened above
        total = time.monotonic() - start
        trace.timings["total"] = total
        trace.set("latency_budget_exceeded", total > config.LATENCY_BUDGET_S)
        trace.set("usage", _usage_summary(trace.calls))
        trace_path = trace.write()
    return result.model_copy(update={"trace_path": trace_path})


async def baseline(request: str, llm: LLMClient | None = None) -> str:
    """The original main.py behaviour, for comparison: one call, just the request."""
    llm = llm or OpenRouterClient()
    return await llm.text("", request, stage="baseline")
