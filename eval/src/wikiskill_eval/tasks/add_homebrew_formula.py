"""add-homebrew-formula skill: session filter + RunEvidence construction."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wikiskill_eval.excerpt import build_observed_outcome
from wikiskill_eval.tasks.common import bind_evidence_builders

if TYPE_CHECKING:
    from wikiskill_eval.ingest.pi import PiSession

SKILL_NAME = "add-homebrew-formula"
SKILL_VERSION = "2.1.0"

_TASK_FRAME = """Evaluate whether the pinned add-homebrew-formula skill helped on this agent run.

Judge these behaviors specifically (skill 2.1.0):
1. Detect the project shape (build system, binary name, version, daemon mode,
   GitHub owner/repo, private vs public remote) before generating anything.
2. Generate Formula/<name>.rb using the dual-source pattern: local packed
   tarball preferred, git fallback; for private repos the git URL must be SSH
   (git@github.com:...git), never https.
3. Load only the references/ files the detected project needs (progressive
   disclosure), not every language pattern file.
4. Add/merge Makefile targets (tap, pack, install, uninstall; service targets
   only when a service block exists) without clobbering existing targets.
5. Generate files only: never run make install / brew install automatically;
   hand the user the manual validation checklist instead.
6. Handle private repos correctly: SSH tap URLs, HOMEBREW_NO_INSTALL_FROM_API=1,
   --build-from-source; local tarball path preferred when network access to the
   repo is unavailable (e.g. CI).

Note: scoring may be retrospective (historical transcript; SkillRef version labels the
skill text under evaluation, which may not have been injected in the original run).

User task:
{user_task}
"""

_NAME_RE = re.compile(
    rf"(?:^|[\s/`]){re.escape(SKILL_NAME)}\b|(?:^|\s)(?:homebrew\s+formula|brew\s+(?:tap|install|formula)|make\s+this\s+brew)",
    re.IGNORECASE,
)
_BREW_CMD_RE = re.compile(
    r"brew\s+(?:tap-new|tap|install|reinstall|audit|style|info|test)\b|"
    r"make\s+(?:tap|pack|install|uninstall|start|stop|restart|status|logs)\b",
    re.IGNORECASE,
)
_FORMULA_PATH_RE = re.compile(r"Formula/[A-Za-z0-9._-]+\.rb\b")
_FORBIDDEN_RUN_RE = re.compile(
    r"(?:^|[\s;&])(?:make\s+install|brew\s+(?:install|reinstall))\b",
    re.IGNORECASE,
)
_SSH_URL_RE = re.compile(r"git@[\w.-]+:[\w./-]+\.git")


def session_in_scope(session: PiSession) -> bool:
    """True when the session invoked or loaded the add-homebrew-formula skill."""
    if SKILL_NAME in session.skill_mentions:
        return True
    for text in session.user_texts:
        if _NAME_RE.search(text) or f'<skill name="{SKILL_NAME}"' in text:
            return True
    for call in session.tool_calls:
        for key in ("path", "pattern", "command"):
            value = call.arguments.get(key)
            if isinstance(value, str) and (
                SKILL_NAME in value or _FORMULA_PATH_RE.search(value)
            ):
                return True
    return False


def build_homebrew_outcome(session: PiSession) -> str:
    """Behavioral signals for add-homebrew-formula next-stage aggregation."""
    base = build_observed_outcome(session)
    transcript = "\n".join([*session.assistant_texts, *session.user_texts])
    commands = [
        str(call.arguments.get("command", ""))
        for call in session.tool_calls
        if call.name.lower() in {"bash", "shell", "run_terminal_cmd"}
    ]
    all_cmds = "\n".join(commands)

    wrote_formula = any(_FORMULA_PATH_RE.search(c) or _FORMULA_PATH_RE.search(str(v)) for c in commands for v in c.split()) or bool(
        _FORMULA_PATH_RE.search(
            "\n".join(
                str(call.arguments.get("path", ""))
                for call in session.tool_calls
            )
        )
    )
    touched_makefile = any("Makefile" in c or "makefile" in c for c in commands)
    used_brew_or_make = bool(_BREW_CMD_RE.search(all_cmds))
    mentions_ssh = bool(_SSH_URL_RE.search(transcript) or _SSH_URL_RE.search(all_cmds))
    mentions_no_api = "HOMEBREW_NO_INSTALL_FROM_API" in transcript or "HOMEBREW_NO_INSTALL_FROM_API" in all_cmds
    ran_install_forbidden = bool(_FORBIDDEN_RUN_RE.search(all_cmds))

    extra = [
        f"wrote_formula={str(wrote_formula).lower()}",
        f"touched_makefile={str(touched_makefile).lower()}",
        f"used_brew_or_make={str(used_brew_or_make).lower()}",
        f"mentions_ssh_git_url={str(mentions_ssh).lower()}",
        f"mentions_no_install_from_api={str(mentions_no_api).lower()}",
        f"ran_install_automatically={str(ran_install_forbidden).lower()}",
    ]
    return base + "; " + "; ".join(extra)


skill_ref, to_run_evidence, evidence_from_sessions = bind_evidence_builders(
    skill_name=SKILL_NAME,
    default_version=SKILL_VERSION,
    task_frame=_TASK_FRAME,
    in_scope=session_in_scope,
    observed_outcome=build_homebrew_outcome,
)
