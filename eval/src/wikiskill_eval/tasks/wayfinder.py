"""wayfinder skill: session filter + RunEvidence construction."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wikiskill_eval.excerpt import build_observed_outcome
from wikiskill_eval.tasks.common import bind_evidence_builders

if TYPE_CHECKING:
    from wikiskill_eval.ingest.pi import PiSession
    from wikiskill_eval.next_stage import NextStageBrief, RunSignalRow

SKILL_NAME = "wayfinder"
SKILL_VERSION = "0.1.0"

_TASK_FRAME = """Evaluate whether the pinned wayfinder skill helped on this agent run.

Judge these behaviors specifically (skill 0.1.0):
1. Plan, don't do: chart/resolve decision tickets; do not deliver the destination unless
   Notes override. Hand off when the pull is to just do the work.
2. Refer by name: human-facing narration and Decisions-so-far use ticket titles (with
   links), never bare ids/numbers/slugs.
3. Map is a single issue labelled wayfinder:map (index, not store); tickets are children
   with ## Question bodies and wayfinder:<type> labels (research|prototype|grilling|task).
4. Tracker-specific ops via the provided tracker doc's "Wayfinding operations"; if no
   tracker, tell the user to run /setup-matt-pocock-skills (else local-markdown default).
5. Chart mode: name destination via grilling+domain-modeling; breadth-first frontier;
   create map then tickets then wire blockers; fire research subagents; stop without
   hand-resolving. Skip the map if no fog.
6. Work mode: load map only; claim (assign) one frontier ticket before work; resolve with
   resolution comment + close + Decisions-so-far pointer; graduate fog / rule out of
   scope as needed. Never resolve more than one ticket per session (research excepted).

Note: scoring may be retrospective (historical transcript; SkillRef version labels the
skill text under evaluation, which may not have been injected in the original run).

User task:
{user_task}
"""

_NAME_RE = re.compile(rf"(?:^|[\s/`]){re.escape(SKILL_NAME)}\b", re.IGNORECASE)
_MAP_SECTIONS = re.compile(
    r"^#{1,3}\s*(Destination|Notes|Decisions so far|Not yet specified|Out of scope)\b",
    re.IGNORECASE | re.MULTILINE,
)
_BARE_ID_WALL = re.compile(r"(?:#\d+\s*[,;]\s*){2,}#\d+")


def session_in_scope(session: PiSession) -> bool:
    """True when the session invoked or loaded the wayfinder skill."""
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


def build_wayfinder_outcome(session: PiSession) -> str:
    """Behavioral signals for wayfinder next-stage aggregation."""
    base = build_observed_outcome(session)
    assistant = "\n".join(session.assistant_texts)
    combined = assistant + "\n" + "\n".join(session.gh_commands)

    map_sections = {m.group(1).lower() for m in _MAP_SECTIONS.finditer(assistant)}
    required = {
        "destination",
        "notes",
        "decisions so far",
        "not yet specified",
        "out of scope",
    }
    section_hits = sum(1 for s in required if s in map_sections)

    has_map_label = bool(re.search(r"wayfinder:map", combined, re.I))
    has_type_label = bool(
        re.search(r"wayfinder:(research|prototype|grilling|task)", combined, re.I)
    )
    claimed = bool(re.search(r"\b(assign|assignee|claim(?:ed|ing)?)\b", combined, re.I))
    resolution_comment = bool(
        re.search(r"\b(resolution comment|decisions so far)\b", assistant, re.I)
    )
    one_ticket = not bool(
        re.search(
            r"\b(resolv(?:e|ed|ing)\s+(?:two|three|\d+)\s+tickets?|"
            r"clos(?:e|ed|ing)\s+(?:two|three|\d+)\s+(?:tickets?|issues?))\b",
            assistant,
            re.I,
        )
    )
    bare_id_wall = bool(_BARE_ID_WALL.search(assistant))
    grilled = bool(re.search(r"\bgrilling\b", assistant, re.I)) and bool(
        re.search(r"\bdomain-?modeling\b", assistant, re.I)
    )
    plan_not_do = not bool(
        re.search(
            r"\b(implement(?:ed|ing)? the destination|ship(?:ped|ping) the feature|"
            r"merged the PR for the destination)\b",
            assistant,
            re.I,
        )
    )

    extra = [
        f"map_sections={section_hits}/{len(required)}",
        f"has_map_label={str(has_map_label).lower()}",
        f"has_type_label={str(has_type_label).lower()}",
        f"claimed_before_work={str(claimed).lower()}",
        f"resolution_recorded={str(resolution_comment).lower()}",
        f"one_ticket_per_session={str(one_ticket).lower()}",
        f"bare_id_wall={str(bare_id_wall).lower()}",
        f"grilling_and_domain={str(grilled).lower()}",
        f"plan_not_do={str(plan_not_do).lower()}",
    ]
    return base + "; " + "; ".join(extra)


skill_ref, to_run_evidence, evidence_from_sessions = bind_evidence_builders(
    skill_name=SKILL_NAME,
    default_version=SKILL_VERSION,
    task_frame=_TASK_FRAME,
    in_scope=session_in_scope,
    observed_outcome=build_wayfinder_outcome,
)

SIGNAL_TABLE_HEADER = (
    "| run | outcome | helped | density | evid | map_secs | map_label | type_label | "
    "claimed | resolved | one_ticket | bare_ids | grill+dm | plan_not_do |\n"
    "| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- | --- | --- | --- |"
)


def render_signal_row(row: RunSignalRow) -> str:
    from wikiskill_eval.next_stage import row_markdown_clm_cells

    cells = [
        *row_markdown_clm_cells(row),
        f"{row.map_sections_hit}/{row.map_sections_total}",
        str(row.has_map_label).lower(),
        str(row.has_type_label).lower(),
        str(row.claimed_before_work).lower(),
        str(row.resolution_recorded).lower(),
        str(row.one_ticket_per_session).lower(),
        str(row.bare_id_wall).lower(),
        str(row.grilling_and_domain).lower(),
        str(row.plan_not_do).lower(),
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
        "incomplete_map_sections": 0,
        "missing_map_label": 0,
        "missing_type_label": 0,
        "unclaimed_work": 0,
        "bare_id_walls": 0,
        "multi_ticket_session": 0,
        "did_not_plan": 0,
        "clm_failed_or_insufficient": 0,
        "clm_helped_but_failed": 0,
    }
    for row in rows:
        if row.map_sections_hit and row.map_sections_hit < row.map_sections_total:
            gaps["incomplete_map_sections"] += 1
        if row.published_creates > 0 and not row.has_map_label:
            gaps["missing_map_label"] += 1
        if row.published_creates > 0 and not row.has_type_label:
            gaps["missing_type_label"] += 1
        if row.resolution_recorded and not row.claimed_before_work:
            gaps["unclaimed_work"] += 1
        if row.bare_id_wall:
            gaps["bare_id_walls"] += 1
        if not row.one_ticket_per_session:
            gaps["multi_ticket_session"] += 1
        if not row.plan_not_do:
            gaps["did_not_plan"] += 1
    add_clm_gaps(gaps, rows)

    priorities = [
        "Keep plan-don't-do default: decisions and map clarity, not destination delivery.",
        "Refer to maps/tickets by title+link in human-facing text; ban bare-id walls.",
        "Require wayfinder:map on the map issue and wayfinder:<type> on every ticket.",
        "Claim (assign) before work; one non-research ticket per session; record via "
        "resolution comment + close + Decisions-so-far pointer.",
        "Chart vs work modes: chart stops without hand-resolve; work loads map only and "
        "graduates fog / out-of-scope correctly.",
    ]
    acceptance = [
        "bare_id_wall=false on >= 95% of in-scope runs.",
        "one_ticket_per_session=true on non-research resolve runs.",
        "has_map_label=true whenever a map is created.",
        "plan_not_do=true unless Notes explicitly override.",
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
