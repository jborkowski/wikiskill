"""Typed WikiSkill evaluation library (CLM-backed)."""

from wikiskill_eval.client import EvalClient, EvalConfig
from wikiskill_eval.pipeline import Evaluator, evaluate_one
from wikiskill_eval.types import (
    ChoiceResult,
    EvaluationRecord,
    NoulResult,
    OutcomeLabel,
    RubricScores,
    RunEvidence,
    ScoreResult,
    SkillRef,
)

__all__ = [
    "ChoiceResult",
    "EvalClient",
    "EvalConfig",
    "EvaluationRecord",
    "Evaluator",
    "NoulResult",
    "OutcomeLabel",
    "RubricScores",
    "RunEvidence",
    "ScoreResult",
    "SkillRef",
    "evaluate_one",
]

__version__ = "0.1.0"
