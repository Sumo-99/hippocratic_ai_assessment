"""Gate stage: one LLM call that judges the REQUEST with two checks (safety, relevance),
not any story. Both must pass before extraction runs.
Unsafe-but-reshapeable requests count as safe; the story prompt reshapes them."""
from . import prompts
from .models import GateResult


async def check_request(llm, request: str) -> GateResult:
    return await llm.structured(prompts.load("gate").substitute(), request, GateResult, stage="gate")


def gate_message(g: GateResult) -> str | None:
    """None when BOTH checks pass (the request may proceed); otherwise a friendly rejection
    built from the evidence of whichever check failed (safety first)."""
    if g.safety.passed and g.relevance.passed:
        return None
    failed = g.safety if not g.safety.passed else g.relevance
    return f"{failed.evidence} Please try another request and I'll be happy to tell a story."
