"""Story generation: system prompt assembly, first draft and revision."""
from . import config, prompts
from .models import StorySpec, describe_characters


def build_system_prompt(spec: StorySpec) -> str:
    """Base prompt + the category's recipe (if any) + one line per variable that is present.

    The picked idea (if any) fills only what the request left empty; what the parent named
    always wins."""
    parts = [prompts.load("base").substitute(target_words=config.TARGET_WORDS)]
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
