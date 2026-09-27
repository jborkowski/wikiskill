"""grilling skill: session filter + RunEvidence construction."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wikiskill_eval.excerpt import build_observed_outcome
from wikiskill_eval.tasks.common import bind_evidence_builders

if TYPE_CHECKING:
    from wikiskill_eval.ingest.pi import PiSession
    from wikiskill_eval.next_stage import NextStageBrief, RunSignalRow

SKILL_NAME = "grilling"
SKILL_VERSION = "0.1.0"

_TASK_FRAME = """Evaluate whether the pinned grilling skill helped on this agent run.

Judge these behaviors specifically (skill 0.1.0):
1. Map the topic as a design tree; work in rounds over the frontier (questions whose
   prerequisites are settled). Ask the whole frontier in one round, then wait.
2. Format each question as Qn + title + body + recommended answer (➡️), separated by ---.
3. Never ask the user for look-up-able facts; dispatch a sub-agent. Don't block the rest
   of the frontier on that exploration.
4. Decisions stay with the user; wait for answers before the next round.
5. Stop when the frontier is empty; do not act until the user confirms shared understanding.

Note: scoring may be retrospective (historical transcript; SkillRef version labels the
skill text under evaluation, which may not have been injected in the original run).

User task:
{user_task}
"""

_NAME_RE = re.compile(rf"(?:^|[\s/`]){re.escape(SKILL_NAME)}\b", re.IGNORECASE)
_Q_RE = re.compile(r"❓\s*\*\*Q\d+\*\*", re.IGNORECASE)
_REC_RE = re.compile(r"➡️")


def session_in_scope(session: PiSession) -> bool:
    """True when the session invoked or loaded the grilling skill."""
    if SKILL_NAME in session.skill_mentions:
        return True
    for text in session.user_texts:
        if _NAME_RE.search(text) or f'<skill name="{SKILL_NAME}"' in text:
            return True
        if re.search(r"\bgrill(?:ing|ed|s)?\b", text, re.I):
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


def build_grilling_outcome(session: PiSession) -> str:
    """Behavioral signals for grilling next-stage aggregation."""
    base = build_observed_outcome(session)
    assistant = "\n".join(session.assistant_texts)

    q_count = len(_Q_RE.findall(assistant))
    rec_count = len(_REC_RE.findall(assistant))
    frontier_lang = bool(re.search(r"\b(frontier|design tree|round)\b", assistant, re.I))
    waited = bool(
        re.search(
            r"\b(wait(?:ing)? for (?:your|the) answers?|before (?:I|we) (?:continue|proceed|act))\b",
            assistant,
            re.I,
        )
    )
    fact_lookup = bool(
        re.search(r"\b(sub-?agent|background agent|look(?:ing)? up|dispatch)\b", assistant, re.I)
    )
    acted_early = bool(
        re.search(
            r"\b(I(?:'| ha)?ve (?:started|begun) implement|creating the (?:PR|map|tickets?) now)\b",
            assistant,
            re.I,
        )
    )

    extra = [
        f"question_count={q_count}",
        f"recommendation_count={rec_count}",
        f"frontier_language={str(frontier_lang).lower()}",
        f"waited_for_answers={str(waited).lower()}",
        f"fact_subagent={str(fact_lookup).lower()}",
        f"acted_before_confirm={str(acted_early).lower()}",
    ]
    return base + "; " + "; ".join(extra)


skill_ref, to_run_evidence, evidence_from_sessions = bind_evidence_builders(
    skill_name=SKILL_NAME,
    default_version=SKILL_VERSION,
    task_frame=_TASK_FRAME,
    in_scope=session_in_scope,
    observed_outcome=build_grilling_outcome,
)

SIGNAL_TABLE_HEADER = (
    "| run | outcome | helped | density | evid | qs | recs | frontier | waited | "
    "fact_agent | acted_early |\n"
    "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |"
)


def render_signal_row(row: RunSignalRow) -> str:
    from wikiskill_eval.next_stage import row_markdown_clm_cells

    cells = [
        *row_markdown_clm_cells(row),
        str(row.question_count),
        str(row.recommendation_count),
        str(row.frontier_language).lower(),
        str(row.waited_for_answers).lower(),
        str(row.fact_subagent).lower(),
        str(row.acted_before_confirm).lower(),
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
        "no_questions": 0,
        "missing_recommendations": 0,
        "no_frontier_language": 0,
        "did_not_wait": 0,
        "acted_before_confirm": 0,
        "clm_failed_or_insufficient": 0,
        "clm_helped_but_failed": 0,
    }
    for row in rows:
        if row.question_count < 1:
            gaps["no_questions"] += 1
        if row.question_count > 0 and row.recommendation_count < row.question_count:
            gaps["missing_recommendations"] += 1
        if not row.frontier_language:
            gaps["no_frontier_language"] += 1
        if row.question_count > 0 and not row.waited_for_answers:
            gaps["did_not_wait"] += 1
        if row.acted_before_confirm:
            gaps["acted_before_confirm"] += 1
    add_clm_gaps(gaps, rows)

    priorities = [
        "Ask the whole settled frontier in one round; wait before the next.",
        "Every question needs a recommended answer (➡️).",
        "Look up facts via sub-agent; never put look-up-able facts on the user.",
        "Do not act until the frontier is empty and the user confirms shared understanding.",
    ]
    acceptance = [
        "question_count >= 1 on every in-scope grill run.",
        "recommendation_count >= question_count on those runs.",
        "acted_before_confirm=false on >= 95% of runs.",
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
