"""Turn an Evaluation into revision feedback. Hard failures take priority over soft ones."""
from . import config
from .models import Evaluation


def build_feedback(ev: Evaluation) -> str:
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
    return "\n".join(bullets)
