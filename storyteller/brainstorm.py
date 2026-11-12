"""Brainstorm stage: three distinct premises for breadth mode."""
from . import prompts
from .extract import breadth_categories
from .llm import LLMError
from .models import Brainstorm, Extraction, Premise


async def brainstorm(llm, e: Extraction) -> list[Premise]:
    system = prompts.load("brainstorm").substitute(
        characters=", ".join(e.characters) or "none specified",
        setting=e.setting or "none specified",
        categories=", ".join(breadth_categories(e)),
    )
    result = await llm.structured(system, "Brainstorm the premises.", Brainstorm, stage="brainstorm")
    if len(result.premises) != 3:
        raise LLMError(f"brainstorm: expected 3 premises, got {len(result.premises)}")
    cats = breadth_categories(e)
    out = []
    for p, cat in zip(result.premises, cats):
        # The model may drift; the user's named characters/setting and our category plan win.
        update = {"category": cat}
        if e.characters:
            update["characters"] = e.characters
        if e.setting:
            update["setting"] = e.setting
        out.append(p.model_copy(update=update))
    return out
