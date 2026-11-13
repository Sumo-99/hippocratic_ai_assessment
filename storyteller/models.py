"""Pydantic types shared by every stage. Field ORDER matters: evidence/reason fields come
first so the model writes its reasoning before it commits to a verdict."""
from typing import Literal

from pydantic import BaseModel

# The story type: which category prompt the writer gets and which checks the judge adds.
Category = Literal["adventure", "silly", "comfort", "cozy"]


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
    premise: str | None  # what the story is about, in the request's words (a worry goes here)
    listener: str | None  # who the story is for ("daughter", "6 year old"); not a character
    category: Category | None  # None = no category: the writer gets the base prompt alone


class Verdict(BaseModel):
    """One rubric dimension as recorded. passed is None when the dimension was skipped:
    it did not apply to this request, so it was never sent to the judge."""
    evidence: str
    passed: bool | None
    fix: str | None


class JudgedVerdict(Verdict):
    """What the judge LLM fills in for a dimension it was asked about: always a real verdict."""
    passed: bool


class JudgeResult(BaseModel):
    """Every dimension, as recorded. The judge LLM gets a narrower schema built from this one
    (judge._reply_schema) holding only the dimensions that apply to the request."""
    safety: Verdict
    wind_down: Verdict
    faithfulness_named: Verdict
    consistency: Verdict
    age_language: Verdict
    story_arc: Verdict
    engagement: Verdict
    faithfulness_premise: Verdict
    category_checks: Verdict


class StoryOption(BaseModel):
    """One model-made story idea for a request with no premise (storyteller/options.py)."""
    characters: str
    setting: str
    situation: str


class StoryOptions(BaseModel):
    options: list[StoryOption]


# ---- types only our code uses ------------------------------------------------------------

class StorySpec(Extraction):
    """What the writer and judge work from: the extraction, plus the idea picked when the
    request had no premise. Only the writer sees the idea: the judge checks faithfulness to
    what the parent asked for, never to an idea the model made up."""
    idea: StoryOption | None = None


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
