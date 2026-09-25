"""Pydantic models for skill-run evidence and CLM evaluation records.

Stores relative candidate scores as experimental judgments — not calibrated
probabilities that a skill is "good". See docs/evaluation-notes.md.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class OutcomeLabel(StrEnum):
    """Fixed rubric candidates for rough skill-run scoring."""

    SUCCEEDED = "succeeded"
    PARTIALLY_SUCCEEDED = "partially_succeeded"
    FAILED = "failed"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class SkillRef(BaseModel):
    """Pinned skill version used during a run."""

    name: str
    version: str
    content_digest: str | None = None


class RunEvidence(BaseModel):
    """Evidence package sent to the evaluator (excerpts + metadata)."""

    run_id: str
    task: str
    skill: SkillRef
    actions_excerpt: str = Field(
        description="Selected actions / tool results; omit full transcript here."
    )
    observed_outcome: str
    omitted_note: str | None = Field(
        default=None,
        description="What was truncated or omitted from the full transcript.",
    )
    max_chars: int | None = Field(
        default=None,
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


class NoulResult(BaseModel):
    type: Literal["noul"] = "noul"
    noul: float
    probabilities: dict[str, float]


class ChoiceResult(BaseModel):
    type: Literal["choice"] = "choice"
    choice: str
    confidence: float
    probabilities: dict[str, float]


class ScoreResult(BaseModel):
    type: Literal["score"] = "score"
    score: float
    confidence: float
    probabilities: dict[str, float]
    legend: dict[str, Any] = Field(default_factory=dict)


class RubricScores(BaseModel):
    """Typed answers from the default skill-run rubric."""

    outcome: ChoiceResult
    skill_helped: NoulResult
    evidence_quality: ScoreResult


class EvaluationRecord(BaseModel):
    """Persisted evaluation: provenance + raw scores + human/task checks later."""

    evaluation_id: str
    run_id: str
    skill: SkillRef
    evaluator_model: str
    evaluator_checkpoint: str | None = None
    rubric_version: str
    candidate_set: list[str]
    state_text: str
    state_ref: str | None = None
    preprocessing: dict[str, Any] = Field(default_factory=dict)
    scores: RubricScores
    raw_answers: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float | None = None
    human_label: OutcomeLabel | None = None
    task_check_passed: bool | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("candidate_set")
    @classmethod
    def _nonempty_candidates(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("candidate_set must not be empty")
        return v
