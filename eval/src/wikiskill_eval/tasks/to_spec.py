"""to-spec skill: session filter + RunEvidence construction."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wikiskill_eval.excerpt import build_observed_outcome
from wikiskill_eval.tasks.common import bind_evidence_builders

if TYPE_CHECKING:
    from wikiskill_eval.ingest.pi import PiSession
    from wikiskill_eval.next_stage import NextStageBrief, RunSignalRow

SKILL_NAME = "to-spec"
SKILL_VERSION = "0.5.0"

_TASK_FRAME = """Evaluate whether the pinned to-spec skill helped on this agent run.

Judge these behaviors specifically (skill 0.5.0 — generic per-repo expectations):
1. No interview: synthesize from conversation; put gaps in Further Notes — do not grill.
2. Explore the current repo / domain docs when present; no hard-coded project paths.
3. Seams checkpoint: propose test seams and get user confirmation before Implementation/Testing Decisions or publish.
4. Spec body covers all six core template sections before publish.
5. Publish only via sibling issue-tracker using role→Repo label (ready-for-agent role);
   install from jborkowski/wikiskill if missing — do not invent another tracker setup.
6. Do not write local design/spec markdown (docs/design, etc.); draft in chat / issue body only.
7. Do not include brittle file paths/snippets in Implementation Decisions (prototype exception only).

Note: scoring may be retrospective (historical transcript; SkillRef version labels the
skill text under evaluation, which may not have been injected in the original run).

User task:
{user_task}
"""

_SPEC_SECTION_RE = re.compile(
    r"^#{1,3}\s*(Problem Statement|Solution|User Stories|Implementation Decisions|"
    r"Testing Decisions|Out of Scope|Further Notes)\b",
    re.IGNORECASE | re.MULTILINE,
)
_TO_SPEC_RE = re.compile(r"(?:^|[\s/`])to-spec\b", re.IGNORECASE)


def session_in_scope(session: PiSession) -> bool:
    """True when the session invoked or loaded the to-spec skill."""
    if "to-spec" in session.skill_mentions:
        return True
    for text in session.user_texts:
        if _TO_SPEC_RE.search(text) or '<skill name="to-spec"' in text:
            return True
    for call in session.tool_calls:
        path = call.arguments.get("path")
        if isinstance(path, str) and "to-spec" in path:
            return True
        pattern = call.arguments.get("pattern")
        if isinstance(pattern, str) and "to-spec" in pattern:
            return True
        cmd = call.arguments.get("command")
        if isinstance(cmd, str) and "to-spec" in cmd:
            return True
    return False


def build_to_spec_outcome(session: PiSession) -> str:
    """Behavioral signals for to-spec next-stage aggregation (plus base gh outcome)."""
    base = build_observed_outcome(session)
    assistant = "\n".join(session.assistant_texts)
    sections = {m.group(1).lower() for m in _SPEC_SECTION_RE.finditer(assistant)}
    required = {
        "problem statement",
        "solution",
        "user stories",
        "implementation decisions",
        "testing decisions",
        "out of scope",
    }
    section_hits = sum(1 for s in required if s in sections)
    interviewed = bool(
        re.search(
            r"\b(could you clarify|a few questions|before I (?:write|draft)|"
            r"I need to ask|interview)\b",
            assistant,
            re.I,
        )
    )
    seams_check = bool(re.search(r"\bseams?\b", assistant, re.I)) and bool(
        re.search(r"\b(match|expect|confirm|agree)\b", assistant, re.I)
    )
    used_issue_tracker = "issue-tracker" in session.skill_mentions or any(
        isinstance(c.arguments.get("path"), str) and "issue-tracker" in str(c.arguments.get("path"))
        for c in session.tool_calls
    )
    published = sum(1 for c in session.gh_commands if re.search(r"gh\s+issue\s+create", c, re.I))
    ready_label = bool(re.search(r"ready-for-agent", assistant + "\n".join(session.gh_commands)))

    extra = [
        f"spec_sections={section_hits}/{len(required)}",
        f"interviewed={str(interviewed).lower()}",
        f"seams_checked={str(seams_check).lower()}",
        f"used_issue_tracker={str(used_issue_tracker).lower()}",
        f"published_creates={published}",
        f"ready_for_agent_label={str(ready_label).lower()}",
    ]
    return base + "; " + "; ".join(extra)


def _enrich_spec_actions(session: PiSession, actions: str, max_chars: int) -> str:
    """Prefer keeping template-ish assistant text in excerpt when present."""
    if not session.assistant_texts or "Problem Statement" not in "\n".join(session.assistant_texts):
        return actions
    spec_bits = []
    for text in session.assistant_texts:
        if _SPEC_SECTION_RE.search(text):
            snippet = text.strip()
            if len(snippet) > 2500:
                snippet = snippet[:2500] + "…"
            spec_bits.append(snippet)
    if not spec_bits:
        return actions
    actions = actions + "\n\nSpec draft excerpts:\n" + "\n---\n".join(spec_bits[:3])
    if max_chars and len(actions) > max_chars:
        return actions[:max_chars] + "\n…[truncated]"
    return actions


skill_ref, to_run_evidence, evidence_from_sessions = bind_evidence_builders(
    skill_name=SKILL_NAME,
    default_version=SKILL_VERSION,
    task_frame=_TASK_FRAME,
    in_scope=session_in_scope,
    observed_outcome=build_to_spec_outcome,
    enrich_actions=_enrich_spec_actions,
)

SIGNAL_TABLE_HEADER = (
    "| run | outcome | helped | density | evid | sections | interviewed | seams | "
    "issue_tracker | creates | ready_label |\n"
    "| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- | ---: | --- |"
)


def render_signal_row(row: RunSignalRow) -> str:
    from wikiskill_eval.next_stage import row_markdown_clm_cells

    cells = [
        *row_markdown_clm_cells(row),
        f"{row.spec_sections_hit}/{row.spec_sections_total}",
        str(row.interviewed).lower(),
        str(row.seams_checked).lower(),
        str(row.used_issue_tracker).lower(),
        str(row.published_creates),
        str(row.ready_for_agent_label).lower(),
    ]
    return "| " + " | ".join(cells) + " |"


def build_next_stage_brief(
    rows: list[RunSignalRow],
    *,
    baseline_version: str,
    recommended_version: str,
) -> NextStageBrief:
    from wikiskill_eval.next_stage import NextStageBrief, add_clm_gaps

    gaps: dict[str, int] = {
        "incomplete_spec_sections": 0,
        "interviewed_user": 0,
        "no_seams_check": 0,
        "publish_without_issue_tracker": 0,
        "publish_without_ready_label": 0,
        "clm_failed_or_insufficient": 0,
        "clm_helped_but_failed": 0,
    }
    for row in rows:
        if row.spec_sections_hit < row.spec_sections_total:
            gaps["incomplete_spec_sections"] += 1
        if row.interviewed:
            gaps["interviewed_user"] += 1
        if not row.seams_checked:
            gaps["no_seams_check"] += 1
        if row.published_creates > 0 and not row.used_issue_tracker:
            gaps["publish_without_issue_tracker"] += 1
        if row.published_creates > 0 and not row.ready_for_agent_label:
            gaps["publish_without_ready_label"] += 1
    add_clm_gaps(gaps, rows)

    priorities = [
        "Mandate full template coverage before publish (all six core sections present).",
        "Keep no-interview rule explicit; if context is insufficient, say what is missing "
        "in Further Notes instead of grilling.",
        "Require a short seams proposal + user confirmation checkpoint before drafting "
        "Implementation/Testing Decisions.",
        "Always load/follow sibling issue-tracker for publish (authz, related-issue gate, "
        "ready-for-agent); install from jborkowski/wikiskill if missing.",
        "When publishing, include ready-for-agent and name related-issue candidates in "
        "the issue body per issue-tracker hard publish gate.",
    ]
    acceptance = [
        f"Fresh corpus with to-spec@{recommended_version}: spec_sections == 6/6 on "
        "every successful publish run.",
        "interviewed=false on >= 90% of in-scope runs.",
        "seams_checked=true before publish on every create run.",
        "used_issue_tracker=true whenever published_creates > 0.",
        f"CLM succeeded|partially_succeeded share rises vs {baseline_version} on matched tasks.",
    ]
    return NextStageBrief(
        skill=SKILL_NAME,
        baseline_version=baseline_version,
        runs_analyzed=len(rows),
        gap_counts=gaps,
        recommended_version=recommended_version,
        priorities=priorities,
        acceptance_checks=acceptance,
    )
