"""Pydantic schemas for skill-run evidence and CLM evaluation records (Zod-like).

Stores relative candidate scores as experimental judgments — not calibrated
probabilities that a skill is "good". See docs/evaluation-notes.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class StrictModel(BaseModel):
    """Base for Zod-like schemas: forbid extras, coerce carefully, validate assignment."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        validate_assignment=True,
        str_strip_whitespace=True,
        frozen=False,
    )


class OutcomeLabel(StrEnum):
    """Fixed rubric candidates for rough skill-run scoring."""

    SUCCEEDED = "succeeded"
    PARTIALLY_SUCCEEDED = "partially_succeeded"
    FAILED = "failed"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class SkillRef(StrictModel):
    """Pinned skill version used during a run."""

    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    content_digest: str | None = None


class RunEvidence(StrictModel):
    """Evidence package sent to the evaluator (excerpts + metadata)."""

    run_id: str = Field(min_length=1)
    task: str = Field(min_length=1)
    skill: SkillRef
    actions_excerpt: str = Field(
        min_length=1,
        description="Selected actions / tool results; omit full transcript here.",
    )
    observed_outcome: str = Field(min_length=1)
    omitted_note: str | None = Field(
        default=None,
        description="What was truncated or omitted from the full transcript.",
    )
    max_chars: int | None = Field(
        default=None,
        gt=0,
        description="Truncation budget applied when building the CLM state text.",
    )

    def to_state(self) -> str:
        """Serialize evidence into the CLM state string."""
        parts = [
            f"Task: {self.task}",
            f"Skill: {self.skill.name}@{self.skill.version}",
            f"Actions / tool results:\n{self.actions_excerpt}",
            f"Observed outcome: {self.observed_outcome}",
        ]
        if self.omitted_note:
            parts.append(f"Omitted content: {self.omitted_note}")
        text = "\n\n".join(parts)
        if self.max_chars is not None and len(text) > self.max_chars:
            return text[: self.max_chars] + "\n…[truncated]"
        return text


class NoulResult(StrictModel):
    type: Literal["noul"] = "noul"
    noul: float = Field(ge=0.0, le=1.0)
    probabilities: dict[str, float]

    @model_validator(mode="after")
    def _probs_sum_near_one(self) -> Self:
        if self.probabilities:
            total = sum(self.probabilities.values())
            if abs(total - 1.0) > 0.05:
                raise ValueError(f"noul probabilities should sum ~1, got {total}")
        return self


class ChoiceResult(StrictModel):
    type: Literal["choice"] = "choice"
    choice: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    probabilities: dict[str, float]

    @model_validator(mode="after")
    def _choice_in_probs(self) -> Self:
        if self.probabilities and self.choice not in self.probabilities:
            raise ValueError(f"choice {self.choice!r} missing from probabilities")
        return self


class ScoreResult(StrictModel):
    type: Literal["score"] = "score"
    score: float
    confidence: float = Field(ge=0.0, le=1.0)
    probabilities: dict[str, float]
    legend: dict[str, Any] = Field(default_factory=dict)


class RubricScores(StrictModel):
    """Typed answers from the default skill-run rubric."""

    outcome: ChoiceResult
    skill_helped: NoulResult
    evidence_quality: ScoreResult


class EvaluationRecord(StrictModel):
    """Persisted evaluation: provenance + raw scores + human/task checks later."""

    evaluation_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    skill: SkillRef
    evaluator_model: str = Field(min_length=1)
    evaluator_checkpoint: str | None = None
    rubric_version: str = Field(min_length=1)
    candidate_set: list[str] = Field(min_length=1)
    state_text: str = Field(min_length=1)
    state_ref: str | None = None
    preprocessing: dict[str, Any] = Field(default_factory=dict)
    scores: RubricScores
    raw_answers: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float | None = Field(default=None, ge=0.0)
    human_label: OutcomeLabel | None = None
    task_check_passed: bool | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("candidate_set")
    @classmethod
    def _nonempty_candidate_strings(cls, v: list[str]) -> list[str]:
        if any(not c.strip() for c in v):
            raise ValueError("candidate_set entries must be non-empty")
        return v
