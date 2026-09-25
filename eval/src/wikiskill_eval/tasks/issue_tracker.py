"""Issue-tracker skill: session filter + RunEvidence construction."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wikiskill_eval.excerpt import build_actions_excerpt, build_observed_outcome
from wikiskill_eval.types import RunEvidence, SkillRef

if TYPE_CHECKING:
    from wikiskill_eval.ingest.pi import PiSession

SKILL_NAME = "issue-tracker"
SKILL_VERSION = "0.3.0"

_TASK_FRAME = """Evaluate whether the pinned issue-tracker skill helped on this agent run.

Judge these behaviors specifically (skill 0.3.0 expectations):
1. Confirm git remote before any tracker writes.
2. Read the target issue (gh issue view) before acting on it.
3. Related-issue discovery before create/claim: gh issue list AND preferably gh search;
   name candidates or explicitly state none found (hard publish gate).
4. While already working on #N: re-run discovery for the change theme before children/edits.
5. Respect draft-vs-publish authorization.
6. Apply triage labels from triage-labels.md and mention them.
7. When creating 2+ related tickets, set blocked_by (or Blocked by lines) in the same op.

Note: scoring may be retrospective (historical transcript; SkillRef version labels the
skill text under evaluation, which may not have been injected in the original run).

User task:
{user_task}
"""

_GH_SIGNAL_RE = re.compile(
    r"\bgh\s+(issue|search|pr|api)\b|dependencies/blocked_by|issue-tracker",
    re.IGNORECASE,
)


def session_in_scope(session: PiSession) -> bool:
    """True when the session used the issue-tracker skill or GitHub issue tooling."""
    if "issue-tracker" in session.skill_mentions:
        return True
    if session.gh_commands:
        return True
    for call in session.tool_calls:
        if call.name == "bash":
            cmd = call.arguments.get("command")
            if isinstance(cmd, str) and _GH_SIGNAL_RE.search(cmd):
                return True
        path = call.arguments.get("path")
        if isinstance(path, str) and "issue-tracker" in path:
            return True
    return False


def skill_ref(*, version: str = SKILL_VERSION, content_digest: str | None = None) -> SkillRef:
    return SkillRef(name=SKILL_NAME, version=version, content_digest=content_digest)


def to_run_evidence(
    session: PiSession,
    *,
    version: str = SKILL_VERSION,
    max_chars: int = 8000,
    content_digest: str | None = None,
) -> RunEvidence:
    """Build evaluator evidence for one in-scope Pi session."""
    actions, omitted = build_actions_excerpt(session, max_chars=max_chars)
    task = _TASK_FRAME.format(user_task=session.first_user_task)
    return RunEvidence(
        run_id=session.session_id,
        task=task,
        skill=skill_ref(version=version, content_digest=content_digest),
        actions_excerpt=actions,
        observed_outcome=build_observed_outcome(session),
        omitted_note=omitted,
        max_chars=max_chars,
    )


def evidence_from_sessions(
    sessions: list[PiSession],
    *,
    version: str = SKILL_VERSION,
    max_chars: int = 8000,
) -> list[RunEvidence]:
    """Filter in-scope sessions and build RunEvidence list."""
    return [
        to_run_evidence(s, version=version, max_chars=max_chars)
        for s in sessions
        if session_in_scope(s)
    ]
