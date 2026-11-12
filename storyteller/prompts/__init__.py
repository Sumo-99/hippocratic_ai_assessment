"""Prompt templates live as .md files next to this module."""
import re
from pathlib import Path
from string import Template

_DIR = Path(__file__).parent

# <!-- ... --> blocks are notes for the human author; they are never sent to the model.
_AUTHOR_NOTE = re.compile(r"<!--.*?-->\s*", re.DOTALL)


def load(name: str) -> Template:
    """Read prompts/<name>.md as a string.Template ($var placeholders), minus author notes."""
    text = (_DIR / f"{name}.md").read_text()
    return Template(_AUTHOR_NOTE.sub("", text))
