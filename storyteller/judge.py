"""Rubric judge: one fresh structured call per story, then code decides what failed."""
import re

from . import config, prompts
from .models import Evaluation, JudgeResult, StorySpec, describe_characters


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
    return skipped


def _category_checks(category: str) -> str:
    """Pull the '## Judge checks' section out of the category prompt (whole text if absent)."""
    text = prompts.load(category).template
    m = re.search(r"^## Judge checks\s*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return (m.group(1) if m else text).strip()


def _rubric_context(spec: StorySpec, skipped: set[str]) -> str:
    """Plain-text description of what the story was supposed to honour."""
    lines = [
        f"Category: {spec.category}",
        f"Characters named by the user: {describe_characters(spec.characters) or 'none'}",
        f"Setting named by the user: {spec.setting or 'none'}",
        f"Premise: {spec.premise or 'none specified'}",
        f"Worry: {spec.worry or 'none'}",
        f"Skipped dimensions (write evidence 'N/A', passed true): "
        f"{', '.join(sorted(skipped)) or 'none'}",
    ]
    return "\n".join(lines)


async def evaluate(llm, spec: StorySpec, story: str) -> Evaluation:
    skipped = skipped_dimensions(spec)
    system = prompts.load("judge").substitute(
        rubric_context=_rubric_context(spec, skipped),
        category_checks=_category_checks(spec.category),
    )
    # Fresh call each time, and the story is the only thing sent: no hint of earlier rounds.
    result = await llm.structured(system, f"STORY:\n{story}", JudgeResult, stage="judge")

    # DECISION: failures are computed in code from `passed`, never trusted from the judge's
    # own summary, and skipped dimensions are dropped even if the judge failed them.
    def failed(names):
        return [n for n in names if n not in skipped and not getattr(result, n).passed]

    ok = length_ok(story)
    return Evaluation(
        judge=result,
        word_count=word_count(story),
        length_ok=ok,
        hard_failures=failed(config.HARD),
        soft_failures=failed([n for n in config.SOFT if n != "length"]) + ([] if ok else ["length"]),
    )
