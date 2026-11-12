"""Pydantic types shared by every stage. Field ORDER matters: evidence/reason fields come
first so the model writes its reasoning before it commits to a verdict."""
from typing import Literal

from pydantic import BaseModel

Category = Literal["adventure", "silly", "comfort", "gentle_lesson", "cozy"]


class GateResult(BaseModel):
    reason: str
    safe: bool
    relevant: bool


class Extraction(BaseModel):
    characters: list[str]
    setting: str | None
    premise: str | None
    mood: str | None
    worry: str | None
    category: Category | None


class Premise(BaseModel):
    premise: str
    category: Category
    characters: list[str]
    setting: str


class Brainstorm(BaseModel):
    premises: list[Premise]


class StorySpec(BaseModel):
    """Variables for ONE draft."""
    category: Category
    characters: list[str]
    setting: str | None
    premise: str | None
    mood: str | None
    worry: str | None
    named_characters: bool  # True only if the USER named them (drives faithfulness skip)
    # True only if the USER named the setting. In breadth mode the brainstorm invents a setting,
    # which must not trigger the hard faithfulness check. Defaults to False (= not user-named).
    named_setting: bool = False


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
    faithfulness_premise_mood: Verdict
    category_checks: Verdict


class Evaluation(BaseModel):
    judge: JudgeResult
    word_count: int
    length_ok: bool
    hard_failures: list[str]  # dimension names, skipped dimensions removed
    soft_failures: list[str]

    @property
    def all_passed(self) -> bool:
        return not self.hard_failures and not self.soft_failures


class Comparison(BaseModel):
    reason: str
    winner: Literal["A", "B"]


class DraftVersion(BaseModel):
    round: int
    text: str
    evaluation: Evaluation
    feedback_sent: str | None


class Draft(BaseModel):
    index: int
    spec: StorySpec
    versions: list[DraftVersion]
    kept: DraftVersion


class PipelineResult(BaseModel):
    # "error" = the run stopped early (e.g. BudgetExceeded); `message` says so in plain words.
    status: Literal["story", "rejected", "safety_fallback_message", "error"]
    story: str | None
    message: str | None
    trace_path: str | None
