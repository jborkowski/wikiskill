"""research skill: session filter + RunEvidence construction."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wikiskill_eval.excerpt import build_observed_outcome
from wikiskill_eval.tasks.common import bind_evidence_builders

if TYPE_CHECKING:
    from wikiskill_eval.ingest.pi import PiSession
    from wikiskill_eval.next_stage import NextStageBrief, RunSignalRow

SKILL_NAME = "research"
SKILL_VERSION = "0.2.1"

_TASK_FRAME = """Evaluate whether the pinned research skill helped on this agent run.

Judge these behaviors specifically (skill 0.2.1):
1. Delegate reading to a background agent so the parent session can keep working.
2. If command -v px succeeds, may use px research/search --out to accelerate discovery
   (leads only); still verify every kept claim against the primary source that owns it.
   No hardcoded home/machine paths; no install/login/credential prompts unless asked.
3. Investigate against primary sources (official docs, source code, specs, first-party
   APIs) — not secondary write-ups; every claim traced to the source that owns it.
4. Write findings to a single Markdown file with citations for each claim.
5. Save under an existing repo notes convention when present; otherwise pick a sensible
   path and tell the user where. Fall back to direct reading if px is missing/fails.

Note: scoring may be retrospective (historical transcript; SkillRef version labels the
skill text under evaluation, which may not have been injected in the original run).

User task:
{user_task}
"""

_NAME_RE = re.compile(rf"(?:^|[\s/`]){re.escape(SKILL_NAME)}\b", re.IGNORECASE)
_CITATION_RE = re.compile(
    r"(https?://\S+|\[.+?\]\(.+?\)|\bsource:\b|\bcited?\b)",
    re.IGNORECASE,
)


def session_in_scope(session: PiSession) -> bool:
    """True when the session invoked or loaded the research skill."""
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


def build_research_outcome(session: PiSession) -> str:
    """Behavioral signals for research next-stage aggregation."""
    base = build_observed_outcome(session)
    assistant = "\n".join(session.assistant_texts)

    background = bool(
        re.search(
            r"\b(background agent|subagent|Task tool|run_in_background)\b",
            assistant,
            re.I,
        )
    )
    used_px = any(
        isinstance(c.arguments.get("command"), str)
        and re.search(r"\bpx\s+(research|search)\b", str(c.arguments.get("command")), re.I)
        for c in session.tool_calls
    ) or bool(re.search(r"\bpx\s+(research|search)\b", assistant, re.I))
    primary = bool(
        re.search(
            r"\b(primary sources?|official docs?|first-party|source code|spec(?:ification)?s?)\b",
            assistant,
            re.I,
        )
    )
    md_writes = 0
    for call in session.tool_calls:
        name = (call.name or "").lower()
        if name not in {"write", "create_file", "editnotebook", "strreplace", "applypatch"}:
            continue
        path = call.arguments.get("path") or call.arguments.get("file_path") or ""
        if isinstance(path, str) and path.endswith((".md", ".markdown")):
            md_writes += 1
    cited = bool(_CITATION_RE.search(assistant))
    said_where = bool(
        re.search(
            r"\b(saved (?:to|at|under)|wrote (?:to|at)|findings (?:at|in)|path:)\b",
            assistant,
            re.I,
        )
    )

    extra = [
        f"background_agent={str(background).lower()}",
        f"used_px={str(used_px).lower()}",
        f"primary_sources={str(primary).lower()}",
        f"markdown_writes={md_writes}",
        f"citations_present={str(cited).lower()}",
        f"reported_path={str(said_where).lower()}",
    ]
    return base + "; " + "; ".join(extra)


skill_ref, to_run_evidence, evidence_from_sessions = bind_evidence_builders(
    skill_name=SKILL_NAME,
    default_version=SKILL_VERSION,
    task_frame=_TASK_FRAME,
    in_scope=session_in_scope,
    observed_outcome=build_research_outcome,
)

SIGNAL_TABLE_HEADER = (
    "| run | outcome | helped | density | evid | background | px | primary | md_writes | "
    "citations | reported_path |\n"
    "| --- | --- | ---: | ---: | ---: | --- | --- | --- | ---: | --- | --- |"
)


def render_signal_row(row: RunSignalRow) -> str:
    from wikiskill_eval.next_stage import row_markdown_clm_cells

    cells = [
        *row_markdown_clm_cells(row),
        str(row.background_agent).lower(),
        str(row.used_px).lower(),
        str(row.primary_sources).lower(),
        str(row.markdown_writes),
        str(row.citations_present).lower(),
        str(row.reported_path).lower(),
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
        "no_background_agent": 0,
        "no_primary_sources": 0,
        "no_markdown_write": 0,
        "no_citations": 0,
        "path_unreported": 0,
        "clm_failed_or_insufficient": 0,
        "clm_helped_but_failed": 0,
    }
    for row in rows:
        if not row.background_agent:
            gaps["no_background_agent"] += 1
        if not row.primary_sources:
            gaps["no_primary_sources"] += 1
        if row.markdown_writes < 1:
            gaps["no_markdown_write"] += 1
        if not row.citations_present:
            gaps["no_citations"] += 1
        if row.markdown_writes > 0 and not row.reported_path:
            gaps["path_unreported"] += 1
    add_clm_gaps(gaps, rows)

    priorities = [
        "Always spin a background agent for the reading legwork.",
        "When px is on PATH, may use px research/search --out as a lead sheet, then verify "
        "claims against primary sources; never hardcode machine paths or prompt for login.",
        "Require primary-source investigation; ban secondary write-ups as the basis of claims.",
        "Write one Markdown findings file with per-claim citations.",
        "Match existing notes convention or pick a sensible path and report it.",
    ]
    acceptance = [
        "background_agent=true on >= 90% of in-scope runs.",
        "markdown_writes >= 1 on every successful research run.",
        "citations_present=true whenever markdown_writes >= 1.",
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
