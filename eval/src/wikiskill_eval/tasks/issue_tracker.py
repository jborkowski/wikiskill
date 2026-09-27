"""Issue-tracker skill: session filter + RunEvidence construction."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wikiskill_eval.tasks.common import bind_evidence_builders

if TYPE_CHECKING:
    from wikiskill_eval.ingest.pi import PiSession
    from wikiskill_eval.next_stage import NextStageBrief, RunSignalRow

SKILL_NAME = "issue-tracker"
SKILL_VERSION = "0.6.0"

_TASK_FRAME = """Evaluate whether the pinned issue-tracker skill helped on this agent run.

Judge these behaviors specifically (skill 0.6.0 — generic per-repo expectations):
1. Bootstrap: confirm git remote / gh can see Issues before writes.
2. Resolve triage via role → Repo label from triage-labels.md (do not invent foreign labels).
3. Related-issue discovery before create/claim: list + preferably search; name candidates.
4. While already working on #N: re-run discovery for the change theme before children/edits.
5. Respect draft-vs-publish authorization.
6. When creating 2+ related tickets, set blocked_by (or Blocked by lines) in the same op.
7. Keep specs/design/tickets on GitHub Issues — do not write local docs/design (or similar) substitutes.

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

SIGNAL_TABLE_HEADER = (
    "| run | outcome | helped | density | evid | creates | lists | views | searches | "
    "labels | deps | remote | related_gate |\n"
    "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |"
)


def render_signal_row(row: RunSignalRow) -> str:
    from wikiskill_eval.next_stage import row_markdown_clm_cells

    cells = [
        *row_markdown_clm_cells(row),
        str(row.creates),
        str(row.lists),
        str(row.views),
        str(row.searches),
        str(row.labels),
        str(row.deps),
        str(row.remote_checks),
        row.related_gate_before_create,
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
        "zero_search": 0,
        "create_without_related_gate": 0,
        "create_without_remote_check": 0,
        "create_without_label_signal": 0,
        "multi_create_without_deps": 0,
        "clm_failed_or_insufficient": 0,
        "clm_helped_but_failed": 0,
    }
    for row in rows:
        if row.searches == 0:
            gaps["zero_search"] += 1
        if row.creates > 0 and row.related_gate_before_create == "no":
            gaps["create_without_related_gate"] += 1
        if row.creates > 0 and row.remote_checks == 0:
            gaps["create_without_remote_check"] += 1
        if row.creates > 0 and row.labels == 0:
            gaps["create_without_label_signal"] += 1
        if row.creates > 1 and row.deps == 0:
            gaps["multi_create_without_deps"] += 1
    add_clm_gaps(gaps, rows)

    priorities = [
        "Working-on-issue related discovery: when already on #N, search/list for "
        "blockers, duplicates, and parallel work before editing or spawning children.",
        "Hard gate before publish: refuse gh issue create until related_gate=yes "
        "(list and/or search) and candidates are named in the draft body.",
        "Remote confirmation: require git remote -v (or equivalent) before any write.",
        "Triage label checklist: map every create/edit to triage-labels.md roles and "
        "record the applied label in the run summary.",
        "Dependency pairing: when creating 2+ related tickets, set blocked_by edges "
        "(or explicit Blocked by lines) in the same operation.",
    ]
    acceptance = [
        f"On a fresh agent corpus with issue-tracker@{recommended_version} injected, "
        "searches+lists > 0 on every create run.",
        "related_gate_before_create=yes for 100% of create runs.",
        "remote_checks >= 1 on every write run.",
        "CLM outcome succeeded|partially_succeeded share rises vs "
        f"{baseline_version} baseline on matched tasks.",
        "Human spot-check: drafts name candidate related issues before publish.",
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
