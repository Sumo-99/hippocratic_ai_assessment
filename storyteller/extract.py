"""Extraction stage plus the routing logic that decides depth vs breadth."""
from typing import Literal

from . import config, prompts
from .models import Category, Extraction


async def extract(llm, request: str) -> Extraction:
    return normalize(await llm.structured(prompts.load("extract").substitute(), request,
                                          Extraction, stage="extract"))


def normalize(e: Extraction) -> Extraction:
    """Code-side fixups of the LLM's extraction."""
    # DECISION: comfort needs a worry to address; without one, fall back to cozy in code
    # rather than trusting the model. Category otherwise stays None here (see breadth_categories).
    if e.category == "comfort" and not e.worry:
        return e.model_copy(update={"category": "cozy"})
    return e


def plan_drafts(e: Extraction) -> Literal["depth", "breadth"]:
    """Premise given -> refine that one idea (depth); otherwise explore three (breadth)."""
    return "depth" if e.premise else "breadth"


def breadth_categories(e: Extraction) -> list[Category]:
    if e.category:
        return [e.category] * 3
    return list(config.UNKNOWN_CATEGORY_SET)
