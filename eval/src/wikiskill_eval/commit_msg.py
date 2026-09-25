"""Pre-commit CLM judge for commit messages (dense vs slop; Conventional Commits).

No regex. System One scores format + density; ``verify_commit_msg`` is a hard gate.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from wikiskill_eval.client import EvalClient

COMMIT_MSG_RUBRIC_VERSION = "commit-msg-v0.8"

FORMAT_PASS_MIN = 0.5
DENSE_LABEL = "dense_informative"
MIN_QUALITY_PROB = 0.5
MIN_NOT_SLOP = 0.5


def build_commit_msg_questions() -> dict[str, Any]:
    from clm import Choice, Noul

    return {
        "format": Noul(
            instructions=(
                "True only if the first line begins with a Conventional Commit type and a "
                "colon (feat: fix: chore: docs: refactor: test: perf: ci: build: style: "
                "revert:) or the same with a scope like feat(eval):. "
                "False for plain English with no such prefix."
            ),
            criteria={
                "true": "type: or type(scope): at the start",
                "false": "no type: prefix",
            },
        ),
        "quality": Choice(
            instructions=(
                "How informative is this commit message for a code reviewer? "
                "Reject vague AI/generic slop."
            ),
            criteria={
                "dense_informative": (
                    "Concrete subject: names the change and why; useful to a reviewer."
                ),
                "adequate": "Understandable but thin; missing concrete why/what.",
                "slop": (
                    "Vague filler (fix stuff, updates, improve code, wip, empty AI phrasing)."
                ),
            },
        ),
        "not_slop": Noul(
            instructions="Is the wording informative and specific, not vague AI/generic slop?",
            criteria={"true": "Informative and specific", "false": "Vague slop"},
        ),
    }


def verify_commit_msg(response: object) -> None:
    """Hard gate: conventional-ish format + dense_informative + not_slop."""
    answers = getattr(response, "answers", None)
    if not isinstance(answers, dict):
        raise AssertionError("missing answers")

    fmt = answers.get("format")
    quality = answers.get("quality")
    not_slop = answers.get("not_slop")
    if fmt is None or quality is None or not_slop is None:
        raise AssertionError("missing format, quality, or not_slop")

    format_noul = float(getattr(fmt, "noul", 0.0))
    choice = str(getattr(quality, "choice", ""))
    qprobs = dict(getattr(quality, "probabilities", {}) or {})
    qprob = float(qprobs.get(DENSE_LABEL, 0.0))
    noul = float(getattr(not_slop, "noul", 0.0))

    if format_noul < FORMAT_PASS_MIN:
        raise AssertionError(f"format(conventional)={format_noul} < {FORMAT_PASS_MIN}")
    if choice == "slop":
        raise AssertionError(f"quality=slop probs={qprobs}")
    if choice != DENSE_LABEL:
        raise AssertionError(f"quality={choice!r} (want {DENSE_LABEL}) probs={qprobs}")
    if qprob < MIN_QUALITY_PROB:
        raise AssertionError(f"{DENSE_LABEL} prob {qprob} < {MIN_QUALITY_PROB}")
    if noul < MIN_NOT_SLOP:
        raise AssertionError(f"not_slop={noul} < {MIN_NOT_SLOP}")


def evaluate_commit_msg(client: EvalClient, message: str) -> Any:
    text = message.strip()
    if not text:
        raise ValueError("empty commit message")
    return client.system_one(
        state=f"Commit message:\n{text}",
        questions=build_commit_msg_questions(),
    )
