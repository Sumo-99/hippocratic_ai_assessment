"""Extraction: pull the story variables out of a request that already passed the gate."""
from . import prompts
from .models import Extraction


async def extract(llm, request: str) -> Extraction:
    return normalize(await llm.structured(prompts.load("extract").substitute(), request,
                                          Extraction, stage="extract"))


def normalize(e: Extraction) -> Extraction:
    """Code-side fixups of the LLM's extraction."""
    # A character with neither name nor role carries nothing; drop it.
    e = e.model_copy(update={"characters": [c for c in e.characters if c.name or c.role]})
    # DECISION: comfort needs a worry to address; without one, fall back to cozy in code
    # rather than trusting the model. A null category is turned into cozy later, in generate.make_spec.
    if e.category == "comfort" and not e.worry:
        return e.model_copy(update={"category": "cozy"})
    return e

