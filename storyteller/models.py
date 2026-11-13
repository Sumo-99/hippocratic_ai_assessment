"""Pydantic types shared by every stage. Field ORDER matters: evidence/reason fields come
first so the model writes its reasoning before it commits to a verdict."""
from typing import Literal

from pydantic import BaseModel

Category = Literal["adventure", "silly", "comfort", "gentle_lesson", "cozy"]


# ---- schemas the LLM fills in (sent as strict JSON schemas) ------------------------------

class Check(BaseModel):
    """One input check. Evidence first, so the model reasons before it decides."""
    evidence: str
    passed: bool


class GateResult(BaseModel):
    """Input check on the REQUEST: is it safe, and is it a bedtime-story request at all?
    Both checks must pass before extraction runs."""
    safety: Check
    relevance: Check


class Character(BaseModel):
    """A story character as the request describes them: a name, a role, or both.
    role = what they are (species or relationship): "Alice's cat", "a badger". Personality
    traits ("grumpy") are not stored yet."""
    name: str | None
    role: str | None

    def describe(self) -> str:
        """One line for prompts: "Bob (Alice's cat)", "Alice", "a badger"."""
        if self.name and self.role:
            return f"{self.name} ({self.role})"
        return self.name or self.role or ""


def describe_characters(characters: "list[Character]") -> str:
    return "; ".join(c.describe() for c in characters)


class Extraction(BaseModel):
    """What the user actually asked for. Anything not in the request stays empty/null."""
    characters: list[Character]
    setting: str | None
    premise: str | None  # what happens, plus any tone the category doesn't cover
    worry: str | None    # only a fear the request actually states; never invented
    listener: str | None  # who the story is for ("daughter", "6 year old"); not a character
    category: Category | None


class Verdict(BaseModel):
    evidence: str
    passed: bool
    fix: str | None


class JudgeResult(BaseModel):
    """Fixed fields, so a strict schema guarantees every dimension is judged."""
    safety: Verdict
    wind_down: Verdict
    faithfulness_named: Verdict
    consistency: Verdict
    age_language: Verdict
    story_arc: Verdict
    engagement: Verdict
    faithfulness_premise: Verdict
    category_checks: Verdict


# ---- types only our code uses ------------------------------------------------------------

class StorySpec(BaseModel):
    """The variables the storyteller and judge work from (the extraction, with a category).
    category None = the request named something but no clear category: base prompt only."""
    category: Category | None
    characters: list[Character]
    setting: str | None
    premise: str | None
    worry: str | None
    listener: str | None = None


class Evaluation(BaseModel):
    judge: JudgeResult
    word_count: int
    length_ok: bool
    hard_failures: list[str]  # dimension names, skipped dimensions removed
    soft_failures: list[str]

    @property
    def all_passed(self) -> bool:
        return not self.hard_failures and not self.soft_failures


class DraftVersion(BaseModel):
    round: int                 # 0 = first draft, 1..MAX_ROUNDS = revisions
    text: str
    evaluation: Evaluation
    feedback_sent: str | None  # the feedback this version was revised from (None for round 0)


class PipelineResult(BaseModel):
    # "safety_message": the final draft failed safety, so the canned message is shown instead.
    # "error": the run stopped early (e.g. BudgetExceeded); `message` says so in plain words.
    status: Literal["story", "rejected", "safety_message", "error"]
    story: str | None
    message: str | None
    trace_path: str | None
