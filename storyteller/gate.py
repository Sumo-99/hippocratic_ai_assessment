"""Gate stage: judges the REQUEST (is it safe and a story request?), not any story.
Unsafe-but-reshapeable requests count as safe; the story prompt reshapes them."""
# TODO(edgy-requests): requests like "a dragon who eats the villagers" are borderline. Decide
# whether the gate should pass them (and let the judge catch it) or reject up front.
from . import prompts
from .models import GateResult


async def check_request(llm, request: str) -> GateResult:
    return await llm.structured(prompts.load("gate").substitute(), request, GateResult, stage="gate")


def gate_message(g: GateResult) -> str | None:
    """Friendly rejection text, or None when the request may proceed."""
    if g.safe and g.relevant:
        return None
    return f"{g.reason} Please try another request and I'll be happy to tell a story."
