"""Shared helpers for skill-specific RunEvidence builders."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from wikiskill_eval.excerpt import build_actions_excerpt, build_observed_outcome
from wikiskill_eval.types import RunEvidence, SkillRef

if TYPE_CHECKING:
    from wikiskill_eval.ingest.pi import PiSession

OutcomeBuilder = Callable[["PiSession"], str]
ActionsBuilder = Callable[["PiSession", str, int], str]
InScope = Callable[["PiSession"], bool]


def make_skill_ref(
    name: str,
    *,
    version: str,
    content_digest: str | None = None,
) -> SkillRef:
    return SkillRef(name=name, version=version, content_digest=content_digest)


def make_run_evidence(
    session: PiSession,
    *,
    skill_name: str,
    version: str,
    task_frame: str,
    max_chars: int = 8000,
    content_digest: str | None = None,
    observed_outcome: OutcomeBuilder | None = None,
    enrich_actions: ActionsBuilder | None = None,
) -> RunEvidence:
    """Build evaluator evidence for one in-scope Pi session."""
    actions, omitted = build_actions_excerpt(session, max_chars=max_chars)
    if enrich_actions is not None:
        actions = enrich_actions(session, actions, max_chars)
    outcome_fn = observed_outcome or build_observed_outcome
    return RunEvidence(
        run_id=session.session_id,
        task=task_frame.format(user_task=session.first_user_task),
        skill=make_skill_ref(skill_name, version=version, content_digest=content_digest),
        actions_excerpt=actions,
        observed_outcome=outcome_fn(session),
        omitted_note=omitted,
        max_chars=max_chars,
    )


def bind_evidence_builders(
    *,
    skill_name: str,
    default_version: str,
    task_frame: str,
    in_scope: InScope,
    observed_outcome: OutcomeBuilder | None = None,
    enrich_actions: ActionsBuilder | None = None,
) -> tuple[
    Callable[..., SkillRef],
    Callable[..., RunEvidence],
    Callable[..., list[RunEvidence]],
]:
    """Return ``skill_ref`` / ``to_run_evidence`` / ``evidence_from_sessions`` for one skill."""

    def skill_ref(*, version: str = default_version, content_digest: str | None = None) -> SkillRef:
        return make_skill_ref(skill_name, version=version, content_digest=content_digest)

    def to_run_evidence(
        session: PiSession,
        *,
        version: str = default_version,
        max_chars: int = 8000,
        content_digest: str | None = None,
    ) -> RunEvidence:
        return make_run_evidence(
            session,
            skill_name=skill_name,
            version=version,
            task_frame=task_frame,
            max_chars=max_chars,
            content_digest=content_digest,
            observed_outcome=observed_outcome,
            enrich_actions=enrich_actions,
        )

    def evidence_from_sessions(
        sessions: list[PiSession],
        *,
        version: str = default_version,
        max_chars: int = 8000,
    ) -> list[RunEvidence]:
        return [
            to_run_evidence(s, version=version, max_chars=max_chars)
            for s in sessions
            if in_scope(s)
        ]

    return skill_ref, to_run_evidence, evidence_from_sessions
