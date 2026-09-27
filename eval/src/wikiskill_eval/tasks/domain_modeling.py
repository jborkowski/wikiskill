"""domain-modeling skill: session filter + RunEvidence construction."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wikiskill_eval.excerpt import build_observed_outcome
from wikiskill_eval.tasks.common import bind_evidence_builders

if TYPE_CHECKING:
    from wikiskill_eval.ingest.pi import PiSession
    from wikiskill_eval.next_stage import NextStageBrief, RunSignalRow

SKILL_NAME = "domain-modeling"
SKILL_VERSION = "0.1.0"

_TASK_FRAME = """Evaluate whether the pinned domain-modeling skill helped on this agent run.

Judge these behaviors specifically (skill 0.1.0):
1. Active model work: challenge glossary conflicts, sharpen fuzzy terms, invent edge-case
   scenarios, cross-check claims against code — not merely reading CONTEXT.md for vocab.
2. Update CONTEXT.md inline when a term resolves (glossary only; no implementation details);
   create lazily; follow CONTEXT-FORMAT.md.
3. Offer ADRs only when hard-to-reverse AND surprising AND real trade-off; follow
   ADR-FORMAT.md; create docs/adr/ lazily.
4. Respect single-context (root CONTEXT.md) vs multi-context (CONTEXT-MAP.md) layouts.

Note: scoring may be retrospective (historical transcript; SkillRef version labels the
skill text under evaluation, which may not have been injected in the original run).

User task:
{user_task}
"""

_NAME_RE = re.compile(rf"(?:^|[\s/`]){re.escape(SKILL_NAME)}\b", re.IGNORECASE)


def session_in_scope(session: PiSession) -> bool:
    """True when the session invoked or loaded the domain-modeling skill."""
    if SKILL_NAME in session.skill_mentions:
        return True
    for text in session.user_texts:
        if _NAME_RE.search(text) or f'<skill name="{SKILL_NAME}"' in text:
            return True
        if re.search(r"\b(CONTEXT\.md|domain model|ADR)\b", text, re.I):
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


def _write_paths(session: PiSession) -> list[str]:
    paths: list[str] = []
    for call in session.tool_calls:
        name = (call.name or "").lower()
        if name not in {"write", "create_file", "strreplace", "applypatch", "editnotebook"}:
            continue
        path = call.arguments.get("path") or call.arguments.get("file_path")
        if isinstance(path, str) and path.strip():
            paths.append(path)
    return paths


def build_domain_modeling_outcome(session: PiSession) -> str:
    """Behavioral signals for domain-modeling next-stage aggregation."""
    base = build_observed_outcome(session)
    assistant = "\n".join(session.assistant_texts)
    paths = _write_paths(session)

    challenged = bool(
        re.search(
            r"\b(glossary defines|do you mean|which is (?:it|right)|conflict(?:s|ing)? with)\b",
            assistant,
            re.I,
        )
    )
    scenario = bool(
        re.search(r"\b(scenario|edge case|what if|suppose)\b", assistant, re.I)
    )
    code_check = bool(
        re.search(r"\b(your code|code (?:says|agrees|cancels)|contradict)\b", assistant, re.I)
    )
    context_writes = sum(1 for p in paths if p.endswith("CONTEXT.md") or p.endswith("CONTEXT-MAP.md"))
    adr_writes = sum(1 for p in paths if "/adr/" in p.replace("\\", "/") or re.search(r"docs/adr/", p))
    impl_in_context = bool(
        re.search(
            r"\b(CONTEXT\.md).{0,80}\b(postgres|typescript|react|kubernetes|s3 bucket)\b",
            assistant,
            re.I,
        )
    )
    adr_bar = bool(
        re.search(r"\b(hard to reverse|surprising|trade-?off)\b", assistant, re.I)
    )

    extra = [
        f"challenged_terms={str(challenged).lower()}",
        f"edge_scenarios={str(scenario).lower()}",
        f"code_crosscheck={str(code_check).lower()}",
        f"context_writes={context_writes}",
        f"adr_writes={adr_writes}",
        f"impl_leak_in_context={str(impl_in_context).lower()}",
        f"adr_bar_mentioned={str(adr_bar).lower()}",
    ]
    return base + "; " + "; ".join(extra)


skill_ref, to_run_evidence, evidence_from_sessions = bind_evidence_builders(
    skill_name=SKILL_NAME,
    default_version=SKILL_VERSION,
    task_frame=_TASK_FRAME,
    in_scope=session_in_scope,
    observed_outcome=build_domain_modeling_outcome,
)

SIGNAL_TABLE_HEADER = (
    "| run | outcome | helped | density | evid | challenge | scenarios | code | "
    "ctx_writes | adr_writes | impl_leak | adr_bar |\n"
    "| --- | --- | ---: | ---: | ---: | --- | --- | --- | ---: | ---: | --- | --- |"
)


def render_signal_row(row: RunSignalRow) -> str:
    from wikiskill_eval.next_stage import row_markdown_clm_cells

    cells = [
        *row_markdown_clm_cells(row),
        str(row.challenged_terms).lower(),
        str(row.edge_scenarios).lower(),
        str(row.code_crosscheck).lower(),
        str(row.context_writes),
        str(row.adr_writes),
        str(row.impl_leak_in_context).lower(),
        str(row.adr_bar_mentioned).lower(),
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
        "no_challenge_or_sharpen": 0,
        "impl_leak_in_context": 0,
        "adr_without_bar": 0,
        "clm_failed_or_insufficient": 0,
        "clm_helped_but_failed": 0,
    }
    for row in rows:
        if not row.challenged_terms and not row.edge_scenarios:
            gaps["no_challenge_or_sharpen"] += 1
        if row.impl_leak_in_context:
            gaps["impl_leak_in_context"] += 1
        if row.adr_writes > 0 and not row.adr_bar_mentioned:
            gaps["adr_without_bar"] += 1
    add_clm_gaps(gaps, rows)

    priorities = [
        "Keep CONTEXT.md a glossary only — no implementation details.",
        "Update CONTEXT.md inline when terms resolve; create lazily.",
        "Offer ADRs only when hard-to-reverse, surprising, and a real trade-off.",
        "Challenge conflicts, sharpen fuzzy terms, and cross-check claims against code.",
    ]
    acceptance = [
        "impl_leak_in_context=false on >= 95% of in-scope runs.",
        "adr_without_bar=0 when adr_writes > 0.",
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
