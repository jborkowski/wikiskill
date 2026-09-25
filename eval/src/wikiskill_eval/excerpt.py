"""Build CLM-friendly excerpts from normalized agent sessions."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wikiskill_eval.ingest.pi import PiSession, ToolCallEvent


def _is_gh_related(call: ToolCallEvent) -> bool:
    if call.name != "bash":
        return False
    cmd = call.arguments.get("command")
    if not isinstance(cmd, str):
        return False
    return bool(
        re.search(
            r"\bgh\s+(issue|search|pr|api|label)\b|dependencies/blocked_by",
            cmd,
            re.IGNORECASE,
        )
    )


def _is_issue_tracker_read(call: ToolCallEvent) -> bool:
    if call.name not in {"read", "fffind", "ffgrep"}:
        return False
    path = call.arguments.get("path")
    pattern = call.arguments.get("pattern")
    blob = f"{path!s} {pattern!s}"
    return "issue-tracker" in blob


def _format_call(call: ToolCallEvent, *, result_limit: int = 400) -> str:
    args = call.arguments
    if call.name == "bash" and isinstance(args.get("command"), str):
        head = f"bash: {args['command']}"
    elif call.name == "read" and isinstance(args.get("path"), str):
        head = f"read: {args['path']}"
    else:
        head = f"{call.name}: {args}"
    lines = [head]
    if call.result_text:
        snippet = call.result_text.strip().replace("\r\n", "\n")
        if len(snippet) > result_limit:
            snippet = snippet[:result_limit] + "…"
        err = " ERROR" if call.is_error else ""
        lines.append(f"  result{err}: {snippet}")
    return "\n".join(lines)


def build_actions_excerpt(
    session: PiSession,
    *,
    max_chars: int = 8000,
    prefer_gh: bool = True,
) -> tuple[str, str | None]:
    """Return ``(actions_excerpt, omitted_note)`` from a Pi session.

    Prefer GitHub / issue-tracker tool calls; include a short final assistant text.
    """
    selected: list[ToolCallEvent] = []
    omitted_gh = 0
    omitted_other = 0

    for call in session.tool_calls:
        keep = _is_gh_related(call) or _is_issue_tracker_read(call)
        if prefer_gh and not keep:
            # Keep a small sample of non-gh context (first few only later if room)
            omitted_other += 1
            continue
        selected.append(call)

    if not selected:
        # Fall back to first N tool calls so evidence is not empty
        selected = list(session.tool_calls[:40])
        omitted_other = max(0, len(session.tool_calls) - len(selected))

    chunks: list[str] = []
    if session.gh_commands:
        unique_cmds: list[str] = []
        for cmd in session.gh_commands:
            if cmd not in unique_cmds:
                unique_cmds.append(cmd)
        chunks.append(
            "GitHub CLI commands observed:\n" + "\n".join(f"- {c}" for c in unique_cmds[:40])
        )

    if session.issue_numbers:
        nums = ", ".join(f"#{n}" for n in session.issue_numbers[:30])
        chunks.append(f"Issue numbers touched: {nums}")

    if session.skill_mentions:
        chunks.append("Skills mentioned: " + ", ".join(session.skill_mentions))

    chunks.append("Selected tool actions:")
    chunks.extend(_format_call(call) for call in selected)

    if session.assistant_texts:
        final = session.assistant_texts[-1].strip()
        if len(final) > 600:
            final = final[:600] + "…"
        chunks.append("Final assistant text:\n" + final)

    text = "\n\n".join(chunks)
    omitted_note: str | None = None
    notes: list[str] = [
        "full Pi transcript kept in local sessions dir (not committed)",
    ]
    if omitted_other:
        notes.append(f"omitted {omitted_other} non-gh tool calls from excerpt")
    if omitted_gh:
        notes.append(f"omitted {omitted_gh} additional gh calls")
    if len(text) > max_chars:
        text = text[:max_chars] + "\n…[truncated]"
        notes.append(f"truncated to max_chars={max_chars}")
    omitted_note = "; ".join(notes)
    return text, omitted_note


def build_observed_outcome(session: PiSession) -> str:
    """Heuristic outcome summary with ordered discovery/create signals."""
    creates = 0
    lists = 0
    views = 0
    searches = 0
    labels = 0
    deps = 0
    remotes = 0
    first_create_idx: int | None = None
    discovery_before_create = False
    saw_discovery = False

    for i, call in enumerate(session.tool_calls):
        if call.name != "bash":
            continue
        cmd = call.arguments.get("command")
        if not isinstance(cmd, str):
            continue
        lower = cmd.lower()
        if "git remote" in lower:
            remotes += 1
        if re.search(r"\bgh\s+search\b", lower):
            searches += 1
            saw_discovery = True
        if re.search(r"\bgh\s+issue\s+list\b", lower):
            lists += 1
            saw_discovery = True
        if re.search(r"\bgh\s+issue\s+view\b", lower):
            views += 1
        if re.search(r"\bgh\s+issue\s+create\b", lower):
            creates += 1
            if first_create_idx is None:
                first_create_idx = i
                discovery_before_create = saw_discovery
        if re.search(r"--add-label|--label\s|ready-for-agent|needs-triage|needs-info", lower):
            labels += 1
        if "blocked_by" in lower or "dependencies" in lower:
            deps += 1

    # Also count from recorded gh_commands (covers truncated arg capture)
    if creates == 0:
        creates = sum(1 for c in session.gh_commands if re.search(r"gh\s+issue\s+create", c, re.I))
    if lists == 0:
        lists = sum(1 for c in session.gh_commands if re.search(r"gh\s+issue\s+list", c, re.I))
    if views == 0:
        views = sum(1 for c in session.gh_commands if re.search(r"gh\s+issue\s+view", c, re.I))
    if searches == 0:
        searches = sum(1 for c in session.gh_commands if re.search(r"gh\s+search", c, re.I))

    if first_create_idx is None:
        related_gate = "n/a-no-create"
    elif discovery_before_create:
        related_gate = "yes"
    else:
        related_gate = "no"

    errors = sum(1 for c in session.tool_calls if c.is_error and _is_gh_related(c))

    parts = [
        f"creates={creates}",
        f"lists={lists}",
        f"views={views}",
        f"searches={searches}",
        f"labels={labels}",
        f"deps={deps}",
        f"remote_checks={remotes}",
        f"related_gate_before_create={related_gate}",
        f"gh_errors={errors}",
        f"skills={','.join(session.skill_mentions) or 'none'}",
    ]
    if session.assistant_texts:
        tail = session.assistant_texts[-1].strip().replace("\n", " ")
        if len(tail) > 300:
            tail = tail[:300] + "…"
        parts.append(f"last_assistant={tail}")
    return "; ".join(parts)
