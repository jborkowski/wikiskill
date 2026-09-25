"""Well-typed evaluation client over ``clm.CLMClient``."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Any

from wikiskill_eval.rubric import RUBRIC_VERSION, OUTCOME_CRITERIA, build_questions
from wikiskill_eval.types import (
    ChoiceResult,
    EvaluationRecord,
    NoulResult,
    RubricScores,
    RunEvidence,
    ScoreResult,
)


@dataclass(frozen=True)
class EvalConfig:
    """Connection settings for a running ``clm-serve`` instance."""

    base_url: str = "http://127.0.0.1:8700"
    api_key: str | None = None
    model: str = "clm-latest"
    timeout: float = 300.0
    temperature: float | None = None
    checkpoint_note: str | None = None

    @classmethod
    def from_env(cls) -> EvalConfig:
        return cls(
            base_url=os.environ.get("CLM_BASE_URL", "http://127.0.0.1:8700"),
            api_key=os.environ.get("CLM_API_KEY"),
            model=os.environ.get("CLM_MODEL", "clm-latest"),
            timeout=float(os.environ.get("CLM_TIMEOUT", "300")),
            temperature=(
                float(os.environ["CLM_TEMPERATURE"])
                if "CLM_TEMPERATURE" in os.environ
                else None
            ),
            checkpoint_note=os.environ.get("CLM_CHECKPOINT_NOTE"),
        )


def _require_clm() -> Any:
    try:
        import clm  # noqa: F401
        from clm import CLMClient, Choice, Noul, Score
    except ImportError as e:
        raise ImportError(
            "contrastive-lm is not installed. On macOS (no vLLM):\n"
            "  uv pip install contrastive-lm --no-deps\n"
            "Then ensure torch, fastapi, uvicorn, numpy, and requests are present "
            "(they are project dependencies)."
        ) from e
    return CLMClient, Choice, Noul, Score


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
        CLMClient, _, _, _ = _require_clm()
        self.config = config or EvalConfig.from_env()
        self._client = CLMClient(
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
            evaluator_model=response.model,
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
