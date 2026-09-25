"""Fixed experimental rubric for skill-run evaluation via CLM System One."""

from __future__ import annotations

from typing import TYPE_CHECKING

from wikiskill_eval.types import OutcomeLabel

if TYPE_CHECKING:
    from clm import Choice, Noul, Score

RUBRIC_VERSION = "skill-run-v0.1"

OUTCOME_CRITERIA: dict[str, str] = {
    OutcomeLabel.SUCCEEDED.value: (
        "The run completed the task successfully and the pinned skill clearly contributed."
    ),
    OutcomeLabel.PARTIALLY_SUCCEEDED.value: (
        "The run made meaningful progress or partly solved the task with the skill."
    ),
    OutcomeLabel.FAILED.value: (
        "The run failed to complete the task or the skill did not help in a useful way."
    ),
    OutcomeLabel.INSUFFICIENT_EVIDENCE.value: (
        "The provided excerpt is too incomplete to judge skill contribution."
    ),
}

EVIDENCE_CRITERIA: list[str] = [
    "Missing or unusable evidence",
    "Sparse evidence; hard to judge",
    "Adequate evidence for a rough judgment",
    "Rich, concrete evidence of skill use and outcome",
]


def build_questions() -> dict[str, Choice | Noul | Score]:
    """Return CLM typed questions for the default skill-run rubric."""
    from clm import Choice, Noul, Score

    return {
        "outcome": Choice(
            instructions=(
                "Given the task, pinned skill version, actions/tool results, and observed "
                "outcome, which label best describes this skill run?"
            ),
            criteria=dict(OUTCOME_CRITERIA),
        ),
        "skill_helped": Noul(
            instructions=(
                "Did using this skill version materially help complete the task "
                "(versus solving it without the skill)?"
            ),
            criteria={
                "true": "Skill use clearly helped",
                "false": "Skill use did not help, or help is unclear",
            },
        ),
        "evidence_quality": Score(
            instructions="How complete and usable is the provided evidence for this judgment?",
            criteria=list(EVIDENCE_CRITERIA),
        ),
    }
