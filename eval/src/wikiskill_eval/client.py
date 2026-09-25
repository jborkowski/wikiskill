"""Typed evaluation client over ``clm.CLMClient``."""

from __future__ import annotations

import uuid
from typing import Any, Protocol, runtime_checkable

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from wikiskill_eval.rubric import OUTCOME_CRITERIA, RUBRIC_VERSION, build_questions
from wikiskill_eval.types import (
    ChoiceResult,
    EvaluationRecord,
    NoulResult,
    RubricScores,
    RunEvidence,
    ScoreResult,
)


class EvalConfig(BaseSettings):
    """Connection settings for a running ``clm-serve`` instance (``CLM_*`` env)."""

    model_config = SettingsConfigDict(
        env_prefix="CLM_",
        env_file=None,
        extra="forbid",
        validate_assignment=True,
    )

    base_url: str = Field(default="http://127.0.0.1:8700")
    api_key: str | None = None
    model: str = Field(default="clm-latest", min_length=1)
    timeout: float = Field(default=300.0, gt=0.0)
    temperature: float | None = Field(default=None, gt=0.0, le=100.0)
    checkpoint_note: str | None = None

    @classmethod
    def from_env(cls) -> EvalConfig:
        """Load from ``CLM_*`` environment variables."""
        return cls()


@runtime_checkable
class _ClmSystemOneClient(Protocol):
    def health(self) -> bool: ...

    def system_one(
        self,
        state: Any,
        questions: dict[str, Any],
        model: str | None = None,
        temperature: float | None = None,
    ) -> Any: ...


def _require_clm() -> type[Any]:
    try:
        from clm import CLMClient
    except ImportError as e:
        raise ImportError(
            "contrastive-lm is not installed. From eval/: run `uv sync` "
            "(vllm is excluded; MLX covers the encoder on Apple Silicon)."
        ) from e
    return CLMClient


def _noul(answer: Any) -> NoulResult:
    return NoulResult(noul=float(answer.noul), probabilities=dict(answer.probabilities))


def _choice(answer: Any) -> ChoiceResult:
    return ChoiceResult(
        choice=str(answer.choice),
        confidence=float(answer.confidence),
        probabilities={str(k): float(v) for k, v in answer.probabilities.items()},
    )


def _score(answer: Any) -> ScoreResult:
    return ScoreResult(
        score=float(answer.score),
        confidence=float(answer.confidence),
        probabilities={str(k): float(v) for k, v in answer.probabilities.items()},
        legend=dict(getattr(answer, "legend", {}) or {}),
    )


def _raw_answers(answers: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, answer in answers.items():
        t = getattr(answer, "type", None)
        if t == "noul":
            out[key] = {"type": "noul", "noul": float(answer.noul)}
        elif t == "choice":
            out[key] = {
                "type": "choice",
                "choice": answer.choice,
                "confidence": float(answer.confidence),
                "probabilities": dict(answer.probabilities),
            }
        elif t == "score":
            out[key] = {
                "type": "score",
                "score": float(answer.score),
                "confidence": float(answer.confidence),
                "probabilities": dict(answer.probabilities),
                "legend": dict(getattr(answer, "legend", {}) or {}),
            }
        else:
            out[key] = {"repr": repr(answer)}
    return out


class EvalClient:
    """Orchestrates skill-run evaluation against a local ``clm-serve`` API."""

    def __init__(self, config: EvalConfig | None = None) -> None:
        clm_client_cls = _require_clm()
        self.config = config or EvalConfig.from_env()
        self._client: _ClmSystemOneClient = clm_client_cls(
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            timeout=self.config.timeout,
            model=self.config.model,
        )

    def health(self) -> bool:
        return bool(self._client.health())

    def system_one(
        self,
        state: str,
        questions: dict[str, Any] | None = None,
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> Any:
        """Thin typed pass-through to ``CLMClient.system_one``."""
        qs = questions if questions is not None else build_questions()
        return self._client.system_one(
            state=state,
            questions=qs,
            model=model or self.config.model,
            temperature=self.config.temperature if temperature is None else temperature,
        )

    def evaluate_run(self, evidence: RunEvidence) -> EvaluationRecord:
        """Score a skill run with the fixed rubric; return a persistable record."""
        state = evidence.to_state()
        response = self.system_one(state)
        answers = response.answers
        scores = RubricScores(
            outcome=_choice(answers["outcome"]),
            skill_helped=_noul(answers["skill_helped"]),
            evidence_quality=_score(answers["evidence_quality"]),
        )
        return EvaluationRecord(
            evaluation_id=str(uuid.uuid4()),
            run_id=evidence.run_id,
            skill=evidence.skill,
            evaluator_model=str(response.model),
            evaluator_checkpoint=self.config.checkpoint_note,
            rubric_version=RUBRIC_VERSION,
            candidate_set=list(OUTCOME_CRITERIA.keys()),
            state_text=state,
            preprocessing={
                "max_chars": evidence.max_chars,
                "omitted_note": evidence.omitted_note,
                "temperature": self.config.temperature,
            },
            scores=scores,
            raw_answers=_raw_answers(answers),
            latency_ms=response.latency_ms,
        )
