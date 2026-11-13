"""Rubric judge: one fresh structured call per story, then code decides what failed."""
import re
from functools import lru_cache

from pydantic import BaseModel, create_model

from . import config, prompts
from .models import (Evaluation, JudgedVerdict, JudgeResult, StorySpec, Verdict,
                     describe_characters)

DIMENSIONS = list(JudgeResult.model_fields)  # schema order: evidence-first per dimension
SKIPPED = Verdict(evidence="skipped: does not apply to this request", passed=None, fix=None)


def word_count(text: str) -> int:
    return len(text.split())


def length_ok(text: str) -> bool:
    lo, hi = config.WORD_RANGE
    return lo <= word_count(text) <= hi  # inclusive


def skipped_dimensions(spec: StorySpec) -> set[str]:
    """Dimensions with nothing to check against; the judge's verdict on them is ignored."""
    skipped = set()
    # Every value in the spec came from the user's request, so empty = nothing was named.
    if not spec.characters and spec.setting is None:
        skipped.add("faithfulness_named")
    if spec.premise is None:
        skipped.add("faithfulness_premise")
    if spec.category is None:  # no category bundle, so no category checks
        skipped.add("category_checks")
    return skipped


def _category_checks(category: str | None) -> str:
    """Pull the '## Judge checks' section out of the category prompt (whole text if absent)."""
    if category is None:
        return "(no category: skip category_checks)"
    text = prompts.load(category).template
    m = re.search(r"^## Judge checks\s*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return (m.group(1) if m else text).strip()


@lru_cache(maxsize=None)
def _reply_schema(dims: tuple[str, ...]) -> type[BaseModel]:
    """A strict schema with only the dimensions the judge is asked about. A skipped dimension
    is not in it, so the judge cannot pass or fail it."""
    return create_model("JudgeReply", **{d: (JudgedVerdict, ...) for d in dims})


def _rubric_context(spec: StorySpec, request: str) -> str:
    """Plain-text description of what the story was supposed to honour."""
    lines = [
        f"The parent's request, word for word: {request!r}",
        f"Category: {spec.category or 'none'}",
        f"Characters named by the user: {describe_characters(spec.characters) or 'none'}",
        f"Setting named by the user: {spec.setting or 'none'}",
        f"Premise: {spec.premise or 'none specified'}",
        f"Worry: {spec.worry or 'none'}",
    ]
    return "\n".join(lines)


async def evaluate(llm, spec: StorySpec, story: str, request: str) -> Evaluation:
    """Judge `story` against the spec and the raw `request` (faithfulness_premise checks the
    story against the request text itself, not only the extracted summary)."""
    skipped = skipped_dimensions(spec)
    asked = tuple(d for d in DIMENSIONS if d not in skipped)
    system = prompts.load("judge").substitute(
        rubric_context=_rubric_context(spec, request),
        category_checks=_category_checks(spec.category),
    )
    # Fresh call each time, and the story is the only thing sent: no hint of earlier rounds.
    reply = await llm.structured(system, f"STORY:\n{story}", _reply_schema(asked), stage="judge")
    # DECISION: skipped dimensions are recorded as skipped (passed None), never as passed.
    result = JudgeResult(**{d: Verdict(**getattr(reply, d).model_dump()) if d in asked
                            else SKIPPED for d in DIMENSIONS})

    # DECISION: failures are computed in code from `passed`, never trusted from the judge's
    # own summary. A skipped dimension (passed None) is neither a pass nor a failure.
    def failed(names):
        return [n for n in names if getattr(result, n).passed is False]

    ok = length_ok(story)
    return Evaluation(
        judge=result,
        word_count=word_count(story),
        length_ok=ok,
        hard_failures=failed(config.HARD),
        soft_failures=failed([n for n in config.SOFT if n != "length"]) + ([] if ok else ["length"]),
    )
