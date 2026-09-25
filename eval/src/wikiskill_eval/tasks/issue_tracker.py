"""Issue-tracker skill: session filter + RunEvidence construction."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wikiskill_eval.tasks.common import bind_evidence_builders

if TYPE_CHECKING:
    from wikiskill_eval.ingest.pi import PiSession

SKILL_NAME = "issue-tracker"
SKILL_VERSION = "0.4.0"

_TASK_FRAME = """Evaluate whether the pinned issue-tracker skill helped on this agent run.

Judge these behaviors specifically (skill 0.4.0 — generic per-repo expectations):
1. Bootstrap: confirm git remote / gh can see Issues before writes.
2. Resolve triage via role → Repo label from triage-labels.md (do not invent foreign labels).
3. Related-issue discovery before create/claim: list + preferably search; name candidates.
4. While already working on #N: re-run discovery for the change theme before children/edits.
5. Respect draft-vs-publish authorization.
6. When creating 2+ related tickets, set blocked_by (or Blocked by lines) in the same op.

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


skill_ref, to_run_evidence, evidence_from_sessions = bind_evidence_builders(
    skill_name=SKILL_NAME,
    default_version=SKILL_VERSION,
    task_frame=_TASK_FRAME,
    in_scope=session_in_scope,
)
