"""code-review skill: session filter + RunEvidence construction."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wikiskill_eval.tasks.common import bind_evidence_builders

if TYPE_CHECKING:
    from wikiskill_eval.ingest.pi import PiSession

SKILL_NAME = "code-review"
SKILL_VERSION = "0.2.0"

_TASK_FRAME = """Evaluate whether the pinned code-review skill helped on this agent run.

Judge these behaviors specifically (skill 0.2.0):
1. Pin base/head commit SHAs and merge base, reject invalid refs before fanout,
   report empty scope and excluded local changes, and inspect exact-revision context.
2. Prefer explicit spec sources and identify documented standards; distinguish
   requirements, code contracts, and optional smell heuristics with repo overrides.
3. Run authorized independent parallel Standards and Spec/Behavior reviews, or disclose
   the lack of context isolation when delegation is unavailable or unauthorized.
4. Continue correctness/security/regression review without a spec while marking spec
   coverage unknown; inspect callers and counterevidence, avoid speculative findings.
5. Preserve separate axis reports and rank only within each axis; cite precise locations,
   rule/requirement or failure evidence, consequences, and minimal fix directions.
   Cross-reference shared roots without inflating unique-defect counts.
6. Accurately disclose checks and limitations, allow no findings, and keep the working
   tree unchanged without unauthorized fixes, commits, publishing, or approval.

Note: scoring may be retrospective (historical transcript; SkillRef version labels the
skill text under evaluation, which may not have been injected in the original run).

User task:
{user_task}
"""

_NAME_RE = re.compile(rf"(?:^|[\s/`]){re.escape(SKILL_NAME)}\b", re.IGNORECASE)


def session_in_scope(session: PiSession) -> bool:
    """True when the session invoked or loaded the code-review skill."""
    if SKILL_NAME in session.skill_mentions:
        return True
    for text in session.user_texts:
        if _NAME_RE.search(text) or f'<skill name="{SKILL_NAME}"' in text:
            return True
    for call in session.tool_calls:
        path = call.arguments.get("path")
        if isinstance(path, str) and SKILL_NAME in path:
            return True
        pattern = call.arguments.get("pattern")
        if isinstance(pattern, str) and SKILL_NAME in pattern:
            return True
        cmd = call.arguments.get("command")
        if isinstance(cmd, str) and SKILL_NAME in cmd:
            return True
    return False


skill_ref, to_run_evidence, evidence_from_sessions = bind_evidence_builders(
    skill_name=SKILL_NAME,
    default_version=SKILL_VERSION,
    task_frame=_TASK_FRAME,
    in_scope=session_in_scope,
)

# next-stage uses the generic CLM-only brief.
