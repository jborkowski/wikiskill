"""Bootstrap a new skill: pack files + eval task module + pack registration.

Usage::

    uv run bootstrap-skill my-skill
    uv run bootstrap-skill my-skill --description "…" --group "Spec to ship"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from wikiskill_eval.tasks.registry import clear_registry_cache, module_stem_for_skill, skill_names

_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_MAX_NAME = 64
_MAX_DESC = 1024


def repo_root_from(start: Path | None = None) -> Path:
    """Walk up from ``start`` (or cwd) until ``skills/`` + ``eval/`` are found."""
    cur = (start or Path.cwd()).resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / "skills").is_dir() and (candidate / "eval").is_dir():
            return candidate
    raise FileNotFoundError(
        "could not find wikiskill repo root (need skills/ and eval/ directories)"
    )


def validate_skill_name(name: str) -> str:
    cleaned = name.strip().lower()
    if not cleaned:
        raise ValueError("skill name is required")
    if len(cleaned) > _MAX_NAME:
        raise ValueError(f"skill name longer than {_MAX_NAME} chars")
    if not _NAME_RE.fullmatch(cleaned):
        raise ValueError(
            "skill name must be lowercase letters, numbers, hyphens "
            "(e.g. my-skill); no leading/trailing hyphen"
        )
    return cleaned


def display_name(skill_name: str) -> str:
    return " ".join(part.capitalize() for part in skill_name.split("-"))


def _skill_md(name: str, description: str, title: str) -> str:
    return f"""---
name: {name}
description: "{description}"
disable-model-invocation: true
metadata:
  version: "0.1.0"
---

# {title}

Skill version: `0.1.0`

TODO: write the procedure for **any** repository this skill targets. Keep it
generic — no hard-coded product paths.

## When to use

TODO: one or two sentences the agent can match against the user request.

## Process

1. TODO: first step
2. TODO: next step

## Changelog

- `0.1.0` — Initial `{name}` skill (bootstrapped).
"""


def _openai_yaml(title: str, short: str) -> str:
    return f"""interface:
  display_name: "{title}"
  short_description: "{short}"
policy:
  allow_implicit_invocation: false
"""


def _task_module(name: str) -> str:
    # Double braces → literal braces in the written file (except {name}).
    return f'''"""{name} skill: session filter + RunEvidence construction."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wikiskill_eval.tasks.common import bind_evidence_builders

if TYPE_CHECKING:
    from wikiskill_eval.ingest.pi import PiSession

SKILL_NAME = "{name}"
SKILL_VERSION = "0.1.0"

_TASK_FRAME = """Evaluate whether the pinned {name} skill helped on this agent run.

Judge these behaviors specifically (skill 0.1.0 — edit after writing the procedure):
1. TODO: list the behaviors this skill must exhibit.
2. Prefer following the skill text over inventing a parallel process.

Note: scoring may be retrospective (historical transcript; SkillRef version labels the
skill text under evaluation, which may not have been injected in the original run).

User task:
{{user_task}}
"""

_NAME_RE = re.compile(rf"(?:^|[\\s/`]){{re.escape(SKILL_NAME)}}\\b", re.IGNORECASE)


def session_in_scope(session: PiSession) -> bool:
    """True when the session invoked or loaded the {name} skill."""
    if SKILL_NAME in session.skill_mentions:
        return True
    for text in session.user_texts:
        if _NAME_RE.search(text) or f'<skill name="{{SKILL_NAME}}"' in text:
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


skill_ref, to_run_evidence, evidence_from_sessions = bind_evidence_builders(
    skill_name=SKILL_NAME,
    default_version=SKILL_VERSION,
    task_frame=_TASK_FRAME,
    in_scope=session_in_scope,
)

# Optional: add SIGNAL_TABLE_HEADER, render_signal_row, build_next_stage_brief
# for a custom next-stage brief. Until then, `eval next-stage` uses the generic
# CLM-only brief from wikiskill_eval.next_stage.
'''


def _update_skills_sh_json(path: Path, skill_name: str, group_title: str | None) -> str:
    if not path.is_file():
        return f"skip {path.name} (missing)"
    data = json.loads(path.read_text(encoding="utf-8"))
    groupings: list[dict[str, object]] = list(data.get("groupings") or [])

    # Already listed?
    for group in groupings:
        skills = group.get("skills")
        if isinstance(skills, list) and skill_name in skills:
            return f"unchanged {path.name} (already listed)"

    title = group_title or "Other"
    target: dict[str, object] | None = None
    for group in groupings:
        if group.get("title") == title:
            target = group
            break
    if target is None:
        target = {
            "title": title,
            "description": "Bootstrapped skills (edit grouping as needed).",
            "skills": [],
        }
        groupings.append(target)
        data["groupings"] = groupings

    skills_raw = target.get("skills")
    skills_list: list[str] = []
    if isinstance(skills_raw, list):
        skills_list = [str(item) for item in skills_raw]
    if skill_name not in skills_list:
        skills_list.append(skill_name)
    target["skills"] = skills_list
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return f"updated {path.name} → group {title!r}"


def _patch_readme_table(path: Path, skill_name: str, purpose: str) -> str:
    if not path.is_file():
        return f"skip {path.name} (missing)"
    text = path.read_text(encoding="utf-8")
    marker = "| `skill-evolve` |"
    row = f"| `{skill_name}` | {purpose} |"
    if f"| `{skill_name}` |" in text:
        return f"unchanged {path.name} (row exists)"
    if marker not in text:
        return f"skip {path.name} (pack table marker not found)"
    text = text.replace(marker, f"{row}\n{marker}", 1)
    path.write_text(text, encoding="utf-8")
    return f"updated {path.name} pack table"


def bootstrap_skill(
    name: str,
    *,
    description: str | None = None,
    group: str | None = None,
    short_description: str | None = None,
    repo_root: Path | None = None,
    force: bool = False,
) -> list[str]:
    """Create skill pack files + eval task; update skills.sh.json / README table."""
    skill = validate_skill_name(name)
    root = repo_root or repo_root_from()
    title = display_name(skill)
    desc = (description or f"TODO: what {skill} does and when to use it.").strip()
    if len(desc) > _MAX_DESC:
        raise ValueError(f"description longer than {_MAX_DESC} chars")
    short = (short_description or desc).strip()
    if len(short) > 120:
        short = short[:117] + "…"

    skill_dir = root / "skills" / skill
    task_path = (
        root / "eval" / "src" / "wikiskill_eval" / "tasks" / f"{module_stem_for_skill(skill)}.py"
    )

    notes: list[str] = []
    if skill_dir.exists() and not force:
        raise FileExistsError(f"skill directory already exists: {skill_dir}")
    if task_path.exists() and not force:
        raise FileExistsError(f"eval task already exists: {task_path}")

    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "agents").mkdir(exist_ok=True)
    (skill_dir / "SKILL.md").write_text(_skill_md(skill, desc, title), encoding="utf-8")
    notes.append(f"wrote {skill_dir.relative_to(root)}/SKILL.md")
    (skill_dir / "agents" / "openai.yaml").write_text(_openai_yaml(title, short), encoding="utf-8")
    notes.append(f"wrote {skill_dir.relative_to(root)}/agents/openai.yaml")

    task_path.parent.mkdir(parents=True, exist_ok=True)
    task_path.write_text(_task_module(skill), encoding="utf-8")
    notes.append(f"wrote {task_path.relative_to(root)}")

    notes.append(_update_skills_sh_json(root / "skills.sh.json", skill, group))
    notes.append(
        _patch_readme_table(
            root / "skills" / "README.md",
            skill,
            purpose=desc if len(desc) < 80 else short,
        )
    )

    clear_registry_cache()
    try:
        registered = skill_names()
        if skill in registered:
            notes.append(f"registered in eval bench: {', '.join(registered)}")
        else:
            notes.append(
                "warning: skill task written but not yet visible in registry "
                "(restart Python / reinstall editable package)"
            )
    except Exception as e:
        notes.append(f"warning: could not refresh registry ({e})")

    return notes


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="bootstrap-skill",
        description=(
            "Create skills/<name>/ + eval task module, register in the eval bench "
            "(auto-discovery), and update skills.sh.json / skills README."
        ),
    )
    parser.add_argument("name", help="Skill name (lowercase, hyphens; matches directory)")
    parser.add_argument(
        "--description",
        default=None,
        help="SKILL.md description (what + when); default TODO placeholder",
    )
    parser.add_argument(
        "--short-description",
        default=None,
        help="agents/openai.yaml short_description (default: truncated --description)",
    )
    parser.add_argument(
        "--group",
        default=None,
        help='skills.sh.json grouping title (default: create/use "Other")',
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Wikiskill repo root (default: discover from cwd)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing skill dir / task module",
    )
    args = parser.parse_args(argv)

    try:
        notes = bootstrap_skill(
            args.name,
            description=args.description,
            short_description=args.short_description,
            group=args.group,
            repo_root=Path(args.repo_root) if args.repo_root else None,
            force=bool(args.force),
        )
    except (ValueError, FileExistsError, FileNotFoundError, OSError) as e:
        print(f"FAIL: {e}", file=sys.stderr)
        raise SystemExit(1) from e

    print(f"PASS: bootstrapped skill={validate_skill_name(args.name)}")
    for note in notes:
        print(f"  - {note}")
    print(
        "Next: edit SKILL.md, refine session_in_scope / _TASK_FRAME in the task "
        "module, then `uv run eval score-sessions --skill "
        f"{validate_skill_name(args.name)} …`"
    )


if __name__ == "__main__":
    main()
