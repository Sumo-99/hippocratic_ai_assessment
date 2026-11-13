"""The whole story flow:

    gate -> extract -> spec -> write -> [judge -> feedback -> revise -> judge -> keep better]
    x up to MAX_ROUNDS -> final safety check -> story (or a friendly message)

`run(request)` is the one public entry; the CLI and a future eval script both use it.
Every run writes a JSON trace to config.RUNS_DIR, even when it fails."""
import time

from . import config
from .extract import extract
from .feedback import build_feedback
from .gate import check_request, gate_message
from .generate import is_vague, make_spec, revise_story, write_story
from .judge import evaluate
from .llm import BudgetExceeded, LLMClient, OpenRouterClient
from .models import DraftVersion, PipelineResult, StorySpec
from .seeds import pick_seed
from .trace import Trace

CANNED_SAFETY_MESSAGE = (
    "I'm sorry, I couldn't make a story for that request that I'm happy to tell at bedtime. "
    "Could you try a different idea?")
BUDGET_MESSAGE = (
    "Sorry, this story was getting too expensive to make, so I stopped. "
    "Please try again, maybe with a simpler request.")


# ---- the regression guard (pure code, no LLM) --------------------------------------------

def _hard_rank(v: DraftVersion) -> tuple[bool, int]:
    """Lower is better: (fails safety?, number of hard failures). False sorts before True."""
    hard = v.evaluation.hard_failures
    return ("safety" in hard, len(hard))


def keep_better(prev: DraftVersion, new: DraftVersion) -> DraftVersion:
    """Keep the previous version only if the revision is strictly worse on hard checks.

    Only hard failures count; soft failures play no part here. On a tie the NEW version wins,
    because it was written to fix the latest feedback."""
    # DECISION: safety outranks the count, so a safe version is never replaced by an unsafe
    # one even if the unsafe one fails fewer hard checks overall.
    return prev if _hard_rank(new) > _hard_rank(prev) else new


# ---- write, judge, revise ----------------------------------------------------------------

async def write_and_revise(llm, spec: StorySpec, trace: Trace, request: str) -> DraftVersion:
    """First draft, then up to MAX_ROUNDS revisions. Returns the version we keep."""
    with trace.stage("write_and_revise"):
        text = await write_story(llm, spec)
        kept = DraftVersion(round=0, text=text, evaluation=await evaluate(llm, spec, text, request),
                            feedback_sent=None)
        # TODO(critique-check): an open-ended "what would a parent dislike?" pass would go
        # here, after evaluate. Deferred until evals show the rubric misses things.
        versions, guard_log = [kept], []

        for rnd in range(1, config.MAX_ROUNDS + 1):
            if kept.evaluation.all_passed:
                break  # nothing left to fix
            # Feedback lists only the FAILED items of the version we kept: hard ones if any
            # failed, otherwise the soft ones (see feedback.build_feedback).
            feedback = build_feedback(kept.evaluation)
            # The revision starts from the kept version, in full, under the same system prompt.
            new_text = await revise_story(llm, spec, kept.text, feedback)
            new = DraftVersion(round=rnd, text=new_text,
                               evaluation=await evaluate(llm, spec, new_text, request),
                               feedback_sent=feedback)
            versions.append(new)
            previous = kept
            kept = keep_better(previous, new)  # the next round starts from whichever is kept
            guard_log.append({"round": rnd, "kept_round": kept.round,
                              "previous_hard": previous.evaluation.hard_failures,
                              "new_hard": new.evaluation.hard_failures})

    trace.set("spec", spec.model_dump())
    trace.set("versions", [v.model_dump() for v in versions])
    trace.set("guard", guard_log)
    return kept


# ---- the whole run -----------------------------------------------------------------------

async def _run(request: str, llm, trace: Trace) -> PipelineResult:
    # 1. Gate: judge the REQUEST. A failed request stops here, before any extraction.
    with trace.stage("gate"):
        g = await check_request(llm, request)
    trace.set("gate", g.model_dump())
    rejection = gate_message(g)
    if rejection:
        trace.set("final", {"status": "rejected"})
        return PipelineResult(status="rejected", story=None, message=rejection, trace_path=None)

    # 2. Extraction -> the story's variables (cozy only if nothing was named).
    with trace.stage("extract"):
        e = await extract(llm, request)
    trace.set("extraction", e.model_dump())
    spec = make_spec(e)
    if is_vague(spec):  # vague request: one random calm situation, so stories don't converge
        index, seed = pick_seed(request, config.STORY_SEED)
        spec = spec.model_copy(update={"seed": seed})
        trace.set("seed", {"index": index, "text": seed, "rng_seed": config.STORY_SEED})

    # 3. Write, judge and revise.
    final = await write_and_revise(llm, spec, trace, request)
    ev = final.evaluation
    summary = {"round": final.round, "all_passed": ev.all_passed,
               "hard_failures": ev.hard_failures, "soft_failures": ev.soft_failures}

    # 4. Final safety check: a story that fails safety is never shown.
    if "safety" in ev.hard_failures:
        # TODO(safety-fallback): a later version could retry with a fresh cozy draft first.
        trace.set("final", {"status": "safety_message", **summary})
        return PipelineResult(status="safety_message", story=None,
                              message=CANNED_SAFETY_MESSAGE, trace_path=None)

    # Other hard failures (e.g. wind_down) don't block: the best version we have is shown.
    trace.set("final", {"status": "story", **summary})
    return PipelineResult(status="story", story=final.text, message=None, trace_path=None)


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
