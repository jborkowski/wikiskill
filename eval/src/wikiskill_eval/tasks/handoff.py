"""handoff skill: session filter + RunEvidence construction."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from wikiskill_eval.excerpt import build_observed_outcome
from wikiskill_eval.tasks.common import bind_evidence_builders

if TYPE_CHECKING:
    from wikiskill_eval.ingest.pi import PiSession
    from wikiskill_eval.next_stage import NextStageBrief, RunSignalRow

SKILL_NAME = "handoff"
SKILL_VERSION = "0.1.0"

_TASK_FRAME = """Evaluate whether the pinned handoff skill helped on this agent run.

Judge these behaviors specifically (skill 0.1.0):
1. Write a handoff document so a fresh agent can continue; include Goal, Done so far,
   Current state, Artifacts (refs only), Suggested skills, Next actions, Resume cue.
2. Save under the OS temp directory — never the workspace (.scratch, docs/, project root).
3. If the user passed arguments, treat them as next-session focus and tailor the doc.
4. Do not duplicate specs/plans/ADRs/issues/commits/diffs — reference by path or URL.
5. Redact secrets, API keys, passwords, and PII.
6. Include a Suggested skills section naming skills the next agent should load via Skill.
7. After writing, report the absolute path and stop unless the user asks to continue.

Note: scoring may be retrospective (historical transcript; SkillRef version labels the
skill text under evaluation, which may not have been injected in the original run).

User task:
{user_task}
"""

_NAME_RE = re.compile(rf"(?:^|[\s/`]){re.escape(SKILL_NAME)}\b", re.IGNORECASE)
_SECTION_RE = re.compile(
    r"^#{1,3}\s*(Next session focus|Goal|Context|Done so far|Current state|"
    r"Decisions(?:\s*&\s*constraints)?|Open questions|Artifacts|"
    r"Suggested skills|Next actions|Resume cue)\b",
    re.IGNORECASE | re.MULTILINE,
)
_WRITE_TOOLS = frozenset(
    {
        "write",
        "create_file",
        "editnotebook",
        "strreplace",
        "search_replace",
        "edit",
    }
)
_TEMP_HINT_RE = re.compile(
    r"(?:^|[/\\])(?:tmp|temp|tmpdir)(?:[/\\]|$)|[/\\]var[/\\]folders[/\\]|"
    r"AppData[/\\]Local[/\\]Temp",
    re.IGNORECASE,
)
_WORKSPACE_HINT_RE = re.compile(
    r"(?:^|[/\\])(?:\.scratch|docs[/\\]|skills[/\\])",
    re.IGNORECASE,
)


def session_in_scope(session: PiSession) -> bool:
    """True when the session invoked or loaded the handoff skill."""
    if SKILL_NAME in session.skill_mentions:
        return True
    for text in session.user_texts:
        if _NAME_RE.search(text) or f'<skill name="{SKILL_NAME}"' in text:
            return True
        if re.search(r"\bhand[\s-]*off\b|\bhandover\b", text, re.I):
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
        if call.name.lower() not in _WRITE_TOOLS:
            cmd = call.arguments.get("command")
            if isinstance(cmd, str) and call.name.lower() in {"bash", "shell", "run_terminal_cmd"}:
                paths.extend(
                    match.group(1)
                    for match in re.finditer(
                        r"(?:(?:>>?|tee(?:\s+-a)?)\s+)([^\s;|&]+\.md)",
                        cmd,
                        re.I,
                    )
                )
            continue
        path = call.arguments.get("path")
        if isinstance(path, str) and path.strip():
            paths.append(path)
    return paths


def _is_temp_path(path: str) -> bool:
    expanded = str(Path(path).expanduser())
    if _TEMP_HINT_RE.search(expanded):
        return True
    # Detect common OS temp roots without embedding a literal /tmp path string.
    lower = expanded.lower().replace("\\", "/")
    parts = [p for p in lower.split("/") if p]
    return "tmp" in parts or "temp" in parts or "tmpdir" in parts


def _is_workspace_path(path: str) -> bool:
    if _is_temp_path(path):
        return False
    if _WORKSPACE_HINT_RE.search(path):
        return True
    # Relative paths are treated as workspace writes
    return not Path(path).is_absolute() and not path.startswith(("~",))


def build_handoff_outcome(session: PiSession) -> str:
    """Behavioral signals for handoff next-stage aggregation."""
    base = build_observed_outcome(session)
    assistant = "\n".join(session.assistant_texts)
    sections = {m.group(1).lower() for m in _SECTION_RE.finditer(assistant)}
    normalized = {("decisions" if s.startswith("decisions") else s) for s in sections}
    required = {
        "goal",
        "done so far",
        "current state",
        "suggested skills",
        "next actions",
        "resume cue",
    }
    section_hits = sum(1 for s in required if s in normalized)

    write_paths = _write_paths(session)
    wrote_temp = any(_is_temp_path(p) for p in write_paths)
    wrote_workspace = any(_is_workspace_path(p) for p in write_paths)
    has_suggested = "suggested skills" in normalized or bool(
        re.search(r"\bsuggested skills\b", assistant, re.I)
    )
    has_resume_cue = "resume cue" in normalized or bool(
        re.search(r"\bresume cue\b", assistant, re.I)
    )
    continued_after = False
    for i, text in enumerate(session.assistant_texts):
        if _SECTION_RE.search(text) and "suggested skills" in text.lower():
            continued_after = i < len(session.assistant_texts) - 1
            break

    extra = [
        f"handoff_sections={section_hits}/{len(required)}",
        f"wrote_temp={str(wrote_temp).lower()}",
        f"wrote_workspace={str(wrote_workspace).lower()}",
        f"has_suggested_skills={str(has_suggested).lower()}",
        f"has_resume_cue={str(has_resume_cue).lower()}",
        f"continued_after_handoff={str(continued_after).lower()}",
    ]
    return base + "; " + "; ".join(extra)


skill_ref, to_run_evidence, evidence_from_sessions = bind_evidence_builders(
    skill_name=SKILL_NAME,
    default_version=SKILL_VERSION,
    task_frame=_TASK_FRAME,
    in_scope=session_in_scope,
    observed_outcome=build_handoff_outcome,
)

SIGNAL_TABLE_HEADER = (
    "| run | outcome | helped | evid | sections | temp | workspace | "
    "suggested | resume | continued |\n"
    "| --- | --- | ---: | ---: | ---: | --- | --- | --- | --- | --- |"
)


def render_signal_row(row: RunSignalRow) -> str:
    from wikiskill_eval.next_stage import row_markdown_clm_cells

    cells = [
        *row_markdown_clm_cells(row),
        f"{row.handoff_sections_hit}/{row.handoff_sections_total}",
        str(row.wrote_temp).lower(),
        str(row.wrote_workspace).lower(),
        str(row.has_suggested_skills).lower(),
        str(row.has_resume_cue).lower(),
        str(row.continued_after_handoff).lower(),
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
        "incomplete_handoff_sections": 0,
        "missing_temp_write": 0,
        "wrote_workspace": 0,
        "missing_suggested_skills": 0,
        "missing_resume_cue": 0,
        "continued_after_handoff": 0,
        "clm_failed_or_insufficient": 0,
        "clm_helped_but_failed": 0,
    }
    for row in rows:
        if row.handoff_sections_hit < row.handoff_sections_total:
            gaps["incomplete_handoff_sections"] += 1
        if not row.wrote_temp:
            gaps["missing_temp_write"] += 1
        if row.wrote_workspace:
            gaps["wrote_workspace"] += 1
        if not row.has_suggested_skills:
            gaps["missing_suggested_skills"] += 1
        if not row.has_resume_cue:
            gaps["missing_resume_cue"] += 1
        if row.continued_after_handoff:
            gaps["continued_after_handoff"] += 1
    add_clm_gaps(gaps, rows)

    return NextStageBrief(
        skill=SKILL_NAME,
        baseline_version=baseline_version,
        runs_analyzed=len(rows),
        gap_counts=gaps,
        recommended_version=recommended_version,
        priorities=[
            "Always write the handoff under the OS temp directory; refuse workspace paths.",
            "Require Suggested skills (Skill tool names) tailored to next-session focus.",
            "Reference specs/plans/ADRs/issues/commits/diffs by path or URL — never paste bodies.",
            "Redact secrets/PII; stop after reporting the absolute handoff path.",
        ],
        acceptance_checks=[
            f"Fresh corpus with handoff@{recommended_version}: wrote_temp=true and "
            "wrote_workspace=false on every successful run.",
            "handoff_sections covers Goal, Suggested skills, Next actions, Resume cue.",
            "continued_after_handoff=false on >= 90% of in-scope runs.",
            f"CLM succeeded|partially_succeeded share rises vs {baseline_version} "
            "on matched tasks.",
        ],
    )
