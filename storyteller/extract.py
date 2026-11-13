"""Extraction: pull the story variables out of a request that already passed the gate."""
from . import prompts
from .models import Extraction


async def extract(llm, request: str) -> Extraction:
    e = await llm.structured(prompts.load("extract").substitute(), request, Extraction,
                             stage="extract")
    # A character with neither name nor role carries nothing; drop it.
    return e.model_copy(update={"characters": [c for c in e.characters if c.name or c.role]})
