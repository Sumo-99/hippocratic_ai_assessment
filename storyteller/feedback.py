"""Turn an Evaluation into revision feedback. Hard failures take priority over soft ones."""
from . import config
from .models import Evaluation

# DECISION: appended to every loop revision whenever the spec has feedback (preferences). Live run
# (store/17_feedback_live_smoke): a judge fix for another dimension ("make the ending sleepy")
# reached the reviser as an explicit instruction and undid an overridden cliffhanger; the feedback
# block in the system prompt alone did not hold. The revise prompt itself stays unchanged.
KEEP_FEEDBACK = ("- Keep the earlier feedback on this story: {feedback} If a change above "
                 "would undo any of it, keep the feedback and make the rest of that change "
                 "around it.")


def build_feedback(ev: Evaluation, keep: str | None = None) -> str:
    # Fix the serious problems first; soft notes only appear once no hard check fails.
    failures = ev.hard_failures or ev.soft_failures
    bullets = []
    for name in failures:
        if name == "length":
            lo, hi = config.WORD_RANGE
            bullets.append(f"- length: the story is {ev.word_count} words; "
                           f"aim for about {config.TARGET_WORDS} (acceptable {lo}-{hi}).")
        else:
            v = getattr(ev.judge, name)
            bullets.append(f"- {name}: {v.fix or v.evidence}")
    if keep:
        bullets.append(KEEP_FEEDBACK.format(feedback=keep))
    return "\n".join(bullets)
