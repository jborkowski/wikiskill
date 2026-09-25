"""Typed WikiSkill evaluation library (CLM-backed)."""

from wikiskill_eval.client import EvalClient, EvalConfig
from wikiskill_eval.commit_msg import (
    evaluate_commit_msg,
    verify_commit_msg,
)
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
    StrictModel,
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
    "StrictModel",
    "evaluate_commit_msg",
    "evaluate_one",
    "verify_commit_msg",
]

__version__ = "0.1.0"
