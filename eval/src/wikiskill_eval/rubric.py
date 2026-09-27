"""Fixed experimental rubric for skill-run evaluation via CLM System One."""

from __future__ import annotations

from typing import TYPE_CHECKING

from wikiskill_eval.types import OutcomeLabel

if TYPE_CHECKING:
    from clm import Choice, Noul, Score

RUBRIC_VERSION = "skill-run-v0.2"

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

# Low → high: under-specified … dense/clear … padded slop (sweet spot is mid-high, not max).
SKILL_DENSITY_CRITERIA: list[str] = [
    "Under-specified: missing the concrete actions the agent must take",
    "Thin: a few useful points but gaps force improvisation",
    "Dense and clear: short lines that point the agent at exact next actions",
    "Padded slop: verbose filler / ceremony that dilutes or distracts from the actions",
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
        "skill_density": Score(
            instructions=(
                "Judge the pinned skill text's density for an agent. Prefer short, "
                "action-pointing lines over padded ceremony. High score is NOT better: "
                "the top bucket is slop that distracts. Mid-high (dense and clear) is the "
                "sweet spot. Use skill text in the state when present; else infer from "
                "how the agent followed or ignored procedure."
            ),
            criteria=list(SKILL_DENSITY_CRITERIA),
        ),
        "evidence_quality": Score(
            instructions="How complete and usable is the provided evidence for this judgment?",
            criteria=list(EVIDENCE_CRITERIA),
        ),
    }


def build_skill_text_questions() -> dict[str, Choice | Noul | Score]:
    """Rubric for scoring skill markdown alone (no run transcript)."""
    from clm import Noul, Score

    return {
        "skill_density": Score(
            instructions=(
                "Score this skill document for agent use. Prefer short imperative lines "
                "that name exact actions (paths, tools, gates). Penalize padded slop "
                "(restated process, motivational filler, redundant templates) and "
                "under-specification (no clear next action)."
            ),
            criteria=list(SKILL_DENSITY_CRITERIA),
        ),
        "action_pointing": Noul(
            instructions=(
                "Do the lines mostly point the agent at concrete do-this steps "
                "(write path X, call tool Y, stop after Z) rather than vague guidance?"
            ),
            criteria={
                "true": "Mostly concrete action pointers",
                "false": "Mostly vague, ceremonial, or missing actions",
            },
        ),
        "slop_risk": Noul(
            instructions=(
                "Would this text likely disturb or over-constrain an agent with filler "
                "that crowds out the few lines that matter?"
            ),
            criteria={
                "true": "High slop risk — filler likely distracts",
                "false": "Low slop risk — text stays on the actionable spine",
            },
        ),
    }
