"""Load skill markdown from the wikiskill pack (or an explicit path)."""

from __future__ import annotations

from pathlib import Path


def repo_root_from(start: Path | None = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / "skills").is_dir() and (candidate / "eval").is_dir():
            return candidate
    raise FileNotFoundError("wikiskill repo root not found (need skills/ and eval/)")


def skill_md_path(skill_name: str, *, repo_root: Path | None = None) -> Path:
    root = repo_root or repo_root_from()
    path = root / "skills" / skill_name / "SKILL.md"
    if not path.is_file():
        raise FileNotFoundError(f"skill not found: {path}")
    return path


def read_skill_text(skill_name: str, *, repo_root: Path | None = None) -> str:
    return skill_md_path(skill_name, repo_root=repo_root).read_text(encoding="utf-8")


def truncate_skill_text(text: str, *, max_chars: int = 4000) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n…[skill text truncated]"
