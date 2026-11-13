"""Story generation: system prompt assembly, first draft and revision."""
from . import config, prompts
from .models import StorySpec, describe_characters

# DECISION: framed as feedback on the story, not as anyone's wishes: the person asking may be
# a parent or a child, so the block names neither.
# DECISION: the feedback beats base/category/variables but never the Safety rules. Asking for a
# cliffhanger is the user's call; asking for something unsafe for a child is not, and the judge
# would reject that draft anyway (safety can never be overridden).
PREFERENCES_HEADER = ("## Feedback on this story (this comes first)\n"
                      "Where this feedback conflicts with anything below, follow the feedback, "
                      "except the Safety rules, which always apply.")


def build_system_prompt(spec: StorySpec) -> str:
    """[Feedback block] + base prompt + the category prompt (if any) + one line per variable
    that is present. No preferences -> no feedback block, so a request-only prompt is unchanged.

    The picked idea (if any) fills only what the request left empty; what the parent named
    always wins."""
    parts = []
    if spec.preferences:  # on top: they supersede everything below except Safety
        parts.append(f"{PREFERENCES_HEADER}\n{spec.preferences}")
    parts.append(prompts.load("base").substitute(target_words=config.TARGET_WORDS))
    if spec.category:
        parts.append(prompts.load(spec.category).substitute())
    idea = spec.idea
    lines = [(label, value) for label, value in (
        ("Characters", describe_characters(spec.characters) or (idea and idea.characters)),
        ("Setting", spec.setting or (idea and idea.setting)),
        ("Premise", spec.premise or (idea and idea.situation)),
        ("Listener", spec.listener),
    ) if value]
    if lines:
        parts.append("\n".join(f"{label}: {value}" for label, value in lines))
    return "\n\n".join(parts)


async def write_story(llm, spec: StorySpec) -> str:
    return await llm.text(build_system_prompt(spec), "Please write the story.", stage="generate")


async def revise_story(llm, spec: StorySpec, previous: str, feedback: str) -> str:
    system = build_system_prompt(spec) + "\n\n" + prompts.load("revise").substitute()
    user = f"Story:\n{previous}\n\nFeedback:\n{feedback}"
    return await llm.text(system, user, stage="revise")
