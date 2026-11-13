"""Extraction: pull the story variables out of a request that already passed the gate.
On a feedback turn the text is the whole conversation (pipeline.conversation_text)."""
import re

from . import overrides, prompts
from .models import Extraction


async def extract(llm, text: str) -> Extraction:
    system = prompts.load("extract").substitute(overridable_checks=overrides.overridable_text())
    e = await llm.structured(system, text, Extraction, stage="extract")
    # A character with neither name nor role carries nothing; drop it.
    # DECISION: keep an override only if its quote really appears in the user's text. An
    # over-eager override (e.g. wind_down for "an exciting adventure") is the main risk, so code
    # checks the model's evidence instead of trusting it. overrides.active() also drops any
    # safety override, so the StorySpec built from this never even sees one.
    return e.model_copy(update={
        "characters": [c for c in e.characters if c.name or c.role],
        "overrides": [o for o in overrides.active(e.overrides) if quoted(o.quote, text)],
    })


def _squash(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def quoted(quote: str, text: str) -> bool:
    """quote appears in text as whole words, ignoring case and runs of whitespace
    (so "end" does not match inside "friend")."""
    q = _squash(quote)
    return bool(q) and re.search(rf"(?<!\w){re.escape(q)}(?!\w)", _squash(text)) is not None
