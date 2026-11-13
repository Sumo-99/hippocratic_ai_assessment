"""The whole story flow:

    gate -> extract -> [5 ideas, if no premise] -> write -> [judge -> feedback -> revise -> judge -> keep better]
    x up to MAX_ROUNDS -> final safety check -> story (or a friendly message)

A feedback turn takes the same path on the whole conversation text (request + every piece of
feedback so far), except that round 0 revises the delivered story instead of writing a new one,
and the ideas step never runs (the first turn's idea carries over):

    gate -> extract -> revise(delivered story, the change) -> [judge -> ... as above]

`run(request)` and `give_feedback(session, feedback)` are the public entries; the CLI and a
future eval script use them. Every turn writes its own JSON trace to config.RUNS_DIR, even when
it fails."""
import time

from . import config
from .extract import extract
from .feedback import build_feedback
from .gate import check_request, gate_message
from .generate import revise_story, write_story
from .judge import evaluate
from .clients import build_client
from .llm import BudgetExceeded, LLMClient
from .options import get_options, pick
from .models import DraftVersion, Evaluation, PipelineResult, StorySession, StorySpec
from .overrides import apply_overrides
from .trace import Trace

CANNED_SAFETY_MESSAGE = (
    "I'm sorry, I couldn't make a story for that request that I'm happy to tell at bedtime. "
    "Could you try a different idea?")
BUDGET_MESSAGE = (
    "Sorry, this story was getting too expensive to make, so I stopped. "
    "Please try again, maybe with a simpler request.")


# ---- the regression guard (pure code, no LLM) --------------------------------------------

# Soft dimensions the guard also weighs when there is feedback (preferences, or a
# feedback turn). faithfulness_premise reads the whole conversation, so it is the judge's signal
# that a revision dropped the requested change.
PROTECT_FEEDBACK = ("faithfulness_premise",)


def _hard_rank(v: DraftVersion, protect: tuple[str, ...] = ()) -> tuple[bool, int, int]:
    """Lower is better: (fails safety?, number of hard failures, number of protected
    dimensions failing). False sorts before True. Overridden failures are in neither list."""
    ev = v.evaluation
    failing = set(ev.hard_failures) | set(ev.soft_failures)
    return ("safety" in ev.hard_failures, len(ev.hard_failures),
            sum(d in failing for d in protect))


def keep_better(prev: DraftVersion, new: DraftVersion,
                protect: tuple[str, ...] = ()) -> DraftVersion:
    """Keep the previous version only if the revision is strictly worse on hard checks, or
    equal on them and worse on a `protect`ed dimension.
    """
    return prev if _hard_rank(new, protect) > _hard_rank(prev, protect) else new


# ---- the conversation and the judge ------------------------------------------------------

def conversation_text(request: str, feedback: list[str]) -> str:
    """What the gate, the extraction and the judge read. With no feedback it is the bare
    request, so a request-only run sends exactly what it always did."""
    if not feedback:
        return request
    lines = [f"Original request: {request}",
             "Changes asked for after hearing the story (newest last):"]
    lines += [f"{i}. {f}" for i, f in enumerate(feedback, 1)]
    return "\n".join(lines)


async def _judge(llm, spec: StorySpec, text: str, request: str) -> Evaluation:
    """The unchanged rubric judge, then the user's overrides (never safety) applied in code.
    Every evaluation in the pipeline goes through here."""
    return apply_overrides(await evaluate(llm, spec, text, request), spec.overrides)


# ---- write, judge, revise ----------------------------------------------------------------

async def write_and_revise(llm, spec: StorySpec, trace: Trace, request: str,
                           previous: DraftVersion | None = None,
                           change: str | None = None) -> DraftVersion:
    """Round 0, then up to MAX_ROUNDS revisions. Returns the version we keep.

    Round 0 is a fresh draft, or, on a feedback turn (`previous` set), a revision of the
    delivered story asked to make the feedback's `change`."""
    with trace.stage("write_and_revise"):
        if previous is None:
            text, sent = await write_story(llm, spec), None
        else:
            sent = f"- Feedback on this story: {change}"
            text = await revise_story(llm, spec, previous.text, sent)
        kept = DraftVersion(round=0, text=text, evaluation=await _judge(llm, spec, text, request),
                            feedback_sent=sent)
        versions, guard_log = [kept], []
        # There is feedback (preferences, or this is a feedback turn): the guard protects it,
        # and every loop revision is told not to undo it.
        protect = PROTECT_FEEDBACK if (previous is not None or spec.preferences) else ()

        for rnd in range(1, config.MAX_ROUNDS + 1):
            if kept.evaluation.all_passed:
                break  # nothing left to fix
            # Feedback lists only the FAILED items of the version we kept: hard ones if any
            # failed, otherwise the soft ones (see feedback.build_feedback). Overridden failures
            # are already out of those lists, so they are never sent.
            feedback = build_feedback(kept.evaluation, keep=spec.preferences)
            # The revision starts from the kept version, in full, under the same system prompt.
            new_text = await revise_story(llm, spec, kept.text, feedback)
            new = DraftVersion(round=rnd, text=new_text,
                               evaluation=await _judge(llm, spec, new_text, request),
                               feedback_sent=feedback)
            versions.append(new)
            prev = kept
            kept = keep_better(prev, new, protect)  # the next round starts from the kept one
            guard_log.append({"round": rnd, "kept_round": kept.round,
                              "previous_hard": prev.evaluation.hard_failures,
                              "new_hard": new.evaluation.hard_failures})
            if kept is prev and _hard_rank(new)[:2] == _hard_rank(prev)[:2]:
                # Stop when a tied revision only drops the requested change; retry new hard failures.
                guard_log[-1]["stopped"] = "revision dropped the requested change"
                break

    trace.set("spec", spec.model_dump())
    trace.set("versions", [v.model_dump() for v in versions])
    trace.set("guard", guard_log)
    return kept


# ---- the whole run -----------------------------------------------------------------------

async def _run(session: StorySession, llm, trace: Trace,
               feedback: str | None = None) -> PipelineResult:
    """One turn of the conversation: the first story (feedback None), or one more change to
    the delivered story. On anything but a delivered story, the incoming session comes back
    unchanged."""
    is_feedback = feedback is not None
    all_feedback = [*session.feedback, feedback] if is_feedback else session.feedback
    text = conversation_text(session.request, all_feedback)

    # 1. Gate: judge the REQUEST (the whole conversation on a feedback turn). A failed request
    #    stops here, before any extraction.
    with trace.stage("gate"):
        g = await check_request(llm, text)
    trace.set("gate", g.model_dump())
    rejection = gate_message(g)
    if rejection:
        trace.set("final", {"status": "rejected"})
        return PipelineResult(status="rejected", story=None, message=rejection, trace_path=None,
                              session=session)

    # 2. Extraction -> the story's variables (characters, premise, category, setting), plus the
    #    feedback (preferences) and overrides. Anything not asked for stays empty. The same path
    #    handles an ask made up front or as feedback: it always reads the whole conversation.
    with trace.stage("extract"):
        e = await extract(llm, text)
    trace.set("extraction", e.model_dump())
    spec = StorySpec(**e.model_dump())

    # 3. No premise on the FIRST turn -> 5 model-made ideas that keep what was named; code
    #    picks one. A feedback turn never asks for ideas again.
    if is_feedback:
        # Keep the original idea on feedback turns; feedback still fills empty fields.
        spec = spec.model_copy(update={"idea": session.spec.idea})
    elif spec.premise is None:
        with trace.stage("options"):
            options = await get_options(llm, spec)
        i = pick(options, config.OPTIONS_SEED, session.request)
        trace.set("options", {"list": [o.model_dump() for o in options],
                              "picked_index": i, "seed": config.OPTIONS_SEED})
        spec = spec.model_copy(update={"idea": options[i]})

    # 4. Write (or revise the delivered story), judge and revise.
    final = await write_and_revise(llm, spec, trace, text,
                                   previous=session.story if is_feedback else None,
                                   change=feedback)
    ev = final.evaluation
    summary = {"round": final.round, "all_passed": ev.all_passed,
               "hard_failures": ev.hard_failures, "soft_failures": ev.soft_failures,
               "overridden": ev.overridden}

    # 5. Final safety check: a story that fails safety is never shown. The session keeps the
    #    last good story, so the user can try different feedback.
    if "safety" in ev.hard_failures:
        trace.set("final", {"status": "safety_message", **summary})
        return PipelineResult(status="safety_message", story=None,
                              message=CANNED_SAFETY_MESSAGE, trace_path=None, session=session)

    # Other hard failures (e.g. wind_down) don't block: the best version we have is shown.
    trace.set("final", {"status": "story", **summary})
    return PipelineResult(status="story", story=final.text, message=None, trace_path=None,
                          session=session.model_copy(update={"feedback": all_feedback,
                                                             "spec": spec, "story": final}))


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


async def _turn(session: StorySession, llm: LLMClient | None,
                feedback: str | None = None) -> PipelineResult:
    """Trace, budget and usage handling shared by the first story and every feedback turn."""
    trace = Trace(session.request)
    all_feedback = [*session.feedback, feedback] if feedback is not None else session.feedback
    trace.set("feedback", all_feedback)
    trace.set("turn", len(all_feedback))
    start = time.monotonic()
    try:
        if llm is None:
            # One fresh client per turn: its total_cost (the budget guard) is per instance.
            # Created inside `try` so a missing key still writes a trace.
            llm = build_client(on_usage=trace.on_usage)
        result = await _run(session, llm, trace, feedback)
    except BudgetExceeded as exc:
        # Report budget exhaustion gracefully so feedback turns preserve the last good story.
        trace.set("error", f"BudgetExceeded: {exc}")
        trace.set("final", {"status": "error"})
        result = PipelineResult(status="error", story=None, message=BUDGET_MESSAGE,
                                trace_path=None, session=session)
    finally:  # the trace is written whatever happened above
        total = time.monotonic() - start
        trace.timings["total"] = total
        trace.set("latency_budget_exceeded", total > config.LATENCY_BUDGET_S)
        trace.set("usage", _usage_summary(trace.calls))
        trace_path = trace.write()
    return result.model_copy(update={"trace_path": trace_path})


async def run(request: str, llm: LLMClient | None = None) -> PipelineResult:
    """Start a conversation: a new session with the request, and its first story.
    `result.session` is always set; its `story` is None if no story was delivered."""
    return await _turn(StorySession(request=request), llm)


async def give_feedback(session: StorySession, feedback: str,
                        llm: LLMClient | None = None) -> PipelineResult:
    """One more turn: revise the session's delivered story to make `feedback`'s change, through
    the same gate -> extract -> judge -> guard path. Never asks for new ideas."""
    if session.story is None:
        raise ValueError("There is no story to give feedback on yet.")
    return await _turn(session, llm, feedback)


async def baseline(request: str, llm: LLMClient | None = None) -> str:
    """The original main.py behaviour, for comparison: one call, just the request."""
    llm = llm or build_client()
    return await llm.text("", request, stage="baseline")
