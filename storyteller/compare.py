"""Pairwise story comparison, run in both orders to cancel position bias, plus keep-better."""
import asyncio
from typing import Literal

from . import prompts
from .models import Comparison, DraftVersion


async def compare_once(llm, a: str, b: str) -> Literal["A", "B"]:
    system = prompts.load("compare").substitute()
    user = f"STORY A:\n{a}\n\nSTORY B:\n{b}"
    result = await llm.structured(system, user, Comparison, stage="compare")
    return result.winner


async def compare_both_orders(llm, x: str, y: str) -> Literal["x", "y", "tie"]:
    # DECISION: a judge that favours position A would otherwise decide by order alone, so we
    # ask twice with the stories swapped and only accept an answer both orders agree on.
    first, second = await asyncio.gather(compare_once(llm, x, y), compare_once(llm, y, x))
    pick1 = "x" if first == "A" else "y"
    pick2 = "y" if second == "A" else "x"
    return pick1 if pick1 == pick2 else "tie"


async def keep_better(llm, prev: DraftVersion, new: DraftVersion) -> tuple[DraftVersion, dict]:
    """Decide which version survives a revision round; returns (winner, trace record)."""
    # DECISION: safety outranks the other hard checks. Compare (fails safety?, number of hard
    # failures) so a safe version is never replaced by an unsafe one, even if the unsafe one
    # fails fewer checks overall. False < True, so "passes safety" sorts first.
    p = ("safety" in prev.evaluation.hard_failures, len(prev.evaluation.hard_failures))
    n = ("safety" in new.evaluation.hard_failures, len(new.evaluation.hard_failures))
    if p != n:  # one version is clearly better on hard checks; no model call needed
        kept, result = (new, "new") if n < p else (prev, "prev")
        rule = "hard_checks"
    else:
        verdict = await compare_both_orders(llm, prev.text, new.text)
        # DECISION: ties keep the previous draft, so a revision must clearly win to replace it.
        kept, result = (new, "new") if verdict == "y" else (prev, "prev")
        rule = f"pairwise:{verdict}"
    return kept, {"rule": rule, "result": result, "kept_round": kept.round}
