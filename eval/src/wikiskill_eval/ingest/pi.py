"""Parse Pi agent session JSONL into structured session records.

Pi sessions are append-only JSONL with ``type`` events. Messages use roles
``user`` / ``assistant`` / ``toolResult`` and assistant ``toolCall`` content parts.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from pydantic import Field

from wikiskill_eval.types import StrictModel

if TYPE_CHECKING:
    from pathlib import Path

_ISSUE_NUM_RE = re.compile(r"(?:^|[\s#/])(?:issues?/)?(\d{1,6})\b")
_GH_ISSUE_RE = re.compile(
    r"\bgh\s+(?:issue|search|pr|api)\b[^\n]{0,200}",
    re.IGNORECASE,
)


class ToolCallEvent(StrictModel):
    """One assistant tool invocation (and optional result text)."""

    call_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    arguments: dict[str, object] = Field(default_factory=dict)
    result_text: str | None = None
    is_error: bool = False
    timestamp: str | None = None


class PiSession(StrictModel):
    """Normalized Pi session suitable for excerpting and skill filters."""

    session_id: str = Field(min_length=1)
    source_path: str = Field(min_length=1)
    cwd: str | None = None
    started_at: str | None = None
    user_texts: list[str] = Field(default_factory=list)
    assistant_texts: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCallEvent] = Field(default_factory=list)
    skill_mentions: list[str] = Field(default_factory=list)
    issue_numbers: list[int] = Field(default_factory=list)
    gh_commands: list[str] = Field(default_factory=list)

    @property
    def first_user_task(self) -> str:
        """Best-effort primary user task (skips skill-injection dumps when possible)."""
        for text in self.user_texts:
            stripped = text.strip()
            if not stripped:
                continue
            if stripped.startswith("<skill "):
                continue
            return stripped
        return self.user_texts[0].strip() if self.user_texts else "(no user message)"


def _text_parts(content: object) -> list[str]:
    if not isinstance(content, list):
        return [str(content)] if content else []
    out: list[str] = []
    for part in content:
        if not isinstance(part, dict):
            continue
        if part.get("type") == "text" and isinstance(part.get("text"), str):
            out.append(part["text"])
    return out


def _skill_names_from_text(text: str) -> list[str]:
    return re.findall(r'<skill\s+name="([^"]+)"', text)


def _issue_numbers_from_text(text: str) -> list[int]:
    found: list[int] = []
    for match in _ISSUE_NUM_RE.finditer(text):
        try:
            n = int(match.group(1))
        except ValueError:
            continue
        if n not in found:
            found.append(n)
    return found


def load_pi_session(path: Path) -> PiSession:
    """Load one ``*.jsonl`` Pi session file."""
    session_id = path.stem
    cwd: str | None = None
    started_at: str | None = None
    user_texts: list[str] = []
    assistant_texts: list[str] = []
    tool_calls: list[ToolCallEvent] = []
    calls_by_id: dict[str, ToolCallEvent] = {}
    skill_mentions: list[str] = []
    issue_numbers: list[int] = []
    gh_commands: list[str] = []

    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue

            etype = event.get("type")
            if etype == "session":
                sid = event.get("id")
                if isinstance(sid, str) and sid:
                    session_id = sid
                raw_cwd = event.get("cwd")
                cwd = raw_cwd if isinstance(raw_cwd, str) else cwd
                ts = event.get("timestamp")
                started_at = ts if isinstance(ts, str) else started_at
                continue

            if etype != "message":
                continue

            message = event.get("message")
            if not isinstance(message, dict):
                continue
            role = message.get("role")
            content = message.get("content")
            timestamp = message.get("timestamp")
            ts = timestamp if isinstance(timestamp, str) else None

            if role == "user":
                for text in _text_parts(content):
                    user_texts.append(text)
                    for name in _skill_names_from_text(text):
                        if name not in skill_mentions:
                            skill_mentions.append(name)
                    for n in _issue_numbers_from_text(text):
                        if n not in issue_numbers:
                            issue_numbers.append(n)
                continue

            if role == "assistant":
                if isinstance(content, list):
                    for part in content:
                        if not isinstance(part, dict):
                            continue
                        ptype = part.get("type")
                        if ptype == "text" and isinstance(part.get("text"), str):
                            assistant_texts.append(part["text"])
                        elif ptype == "toolCall":
                            call_id = part.get("id")
                            name = part.get("name")
                            if not isinstance(call_id, str) or not isinstance(name, str):
                                continue
                            args_raw = part.get("arguments")
                            args: dict[str, object] = (
                                dict(args_raw) if isinstance(args_raw, dict) else {}
                            )
                            evt = ToolCallEvent(
                                call_id=call_id,
                                name=name,
                                arguments=args,
                                timestamp=ts,
                            )
                            tool_calls.append(evt)
                            calls_by_id[call_id] = evt
                            cmd = args.get("command")
                            if isinstance(cmd, str):
                                gh_commands.extend(
                                    m.group(0).strip() for m in _GH_ISSUE_RE.finditer(cmd)
                                )
                                for n in _issue_numbers_from_text(cmd):
                                    if n not in issue_numbers:
                                        issue_numbers.append(n)
                                if "issue-tracker" in cmd and "issue-tracker" not in skill_mentions:
                                    skill_mentions.append("issue-tracker")
                            path_arg = args.get("path")
                            if (
                                isinstance(path_arg, str)
                                and "issue-tracker" in path_arg
                                and "issue-tracker" not in skill_mentions
                            ):
                                skill_mentions.append("issue-tracker")
                continue

            if role == "toolResult":
                call_id = message.get("toolCallId")
                result_bits = _text_parts(content)
                result_text = "\n".join(result_bits) if result_bits else None
                is_error = bool(message.get("isError"))
                if isinstance(call_id, str) and call_id in calls_by_id:
                    existing = calls_by_id[call_id]
                    # Pydantic models are mutable unless frozen
                    existing.result_text = result_text
                    existing.is_error = is_error
                if result_text:
                    for n in _issue_numbers_from_text(result_text[:4000]):
                        if n not in issue_numbers:
                            issue_numbers.append(n)
                continue

    return PiSession(
        session_id=session_id,
        source_path=str(path),
        cwd=cwd,
        started_at=started_at,
        user_texts=user_texts,
        assistant_texts=assistant_texts,
        tool_calls=tool_calls,
        skill_mentions=skill_mentions,
        issue_numbers=issue_numbers,
        gh_commands=gh_commands,
    )


def load_pi_sessions_dir(directory: Path) -> list[PiSession]:
    """Load every ``*.jsonl`` file directly under ``directory`` (non-recursive)."""
    if not directory.is_dir():
        raise FileNotFoundError(f"sessions dir not found: {directory}")
    paths = sorted(directory.glob("*.jsonl"))
    return [load_pi_session(p) for p in paths]
