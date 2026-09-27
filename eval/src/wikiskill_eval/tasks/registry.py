"""Unified skill-task registry for the eval bench.

Each module under ``wikiskill_eval.tasks`` (except helpers) that exports
``SKILL_NAME``, ``SKILL_VERSION``, and ``evidence_from_sessions`` is registered
automatically. Optional exports:

- ``build_next_stage_brief(rows, *, baseline_version, recommended_version)``
- ``SIGNAL_TABLE_HEADER`` / ``render_signal_row(row)`` for next-stage markdown
"""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from types import ModuleType

    from wikiskill_eval.next_stage import NextStageBrief, RunSignalRow
    from wikiskill_eval.types import RunEvidence

EvidenceFromSessions = Callable[..., list["RunEvidence"]]
NextStageBuilder = Callable[..., "NextStageBrief"]
SignalRowRenderer = Callable[["RunSignalRow"], str]

_SKIP_MODULES = frozenset({"common", "registry"})


@dataclass(frozen=True, slots=True)
class SkillTask:
    """One skill wired into score-sessions / next-stage."""

    name: str
    version: str
    module: ModuleType
    evidence_from_sessions: EvidenceFromSessions
    build_next_stage_brief: NextStageBuilder | None = None
    signal_table_header: str | None = None
    render_signal_row: SignalRowRenderer | None = None


def _load_task_modules() -> list[ModuleType]:
    import wikiskill_eval.tasks as tasks_pkg

    modules: list[ModuleType] = []
    for info in pkgutil.iter_modules(tasks_pkg.__path__, tasks_pkg.__name__ + "."):
        short = info.name.rsplit(".", 1)[-1]
        if short in _SKIP_MODULES or info.ispkg:
            continue
        modules.append(importlib.import_module(info.name))
    return modules


def _as_skill_task(module: ModuleType) -> SkillTask | None:
    name = getattr(module, "SKILL_NAME", None)
    version = getattr(module, "SKILL_VERSION", None)
    evidence = getattr(module, "evidence_from_sessions", None)
    if not isinstance(name, str) or not name:
        return None
    if not isinstance(version, str) or not version:
        return None
    if not callable(evidence):
        return None

    brief = getattr(module, "build_next_stage_brief", None)
    header = getattr(module, "SIGNAL_TABLE_HEADER", None)
    render = getattr(module, "render_signal_row", None)
    return SkillTask(
        name=name,
        version=version,
        module=module,
        evidence_from_sessions=cast("EvidenceFromSessions", evidence),
        build_next_stage_brief=cast("NextStageBuilder", brief) if callable(brief) else None,
        signal_table_header=header if isinstance(header, str) else None,
        render_signal_row=cast("SignalRowRenderer", render) if callable(render) else None,
    )


def discover_skills() -> dict[str, SkillTask]:
    """Import task modules and return ``name → SkillTask`` (sorted by name)."""
    found: dict[str, SkillTask] = {}
    for module in _load_task_modules():
        task = _as_skill_task(module)
        if task is None:
            continue
        if task.name in found:
            raise ValueError(
                f"duplicate SKILL_NAME {task.name!r}: "
                f"{found[task.name].module.__name__} and {module.__name__}"
            )
        found[task.name] = task
    return dict(sorted(found.items()))


_registry_cache: dict[str, SkillTask] | None = None


def clear_registry_cache() -> None:
    """Drop the cached registry (tests / after bootstrap in-process)."""
    global _registry_cache
    _registry_cache = None


def registry() -> dict[str, SkillTask]:
    """Return the cached skill-task registry."""
    global _registry_cache
    if _registry_cache is None:
        _registry_cache = discover_skills()
    return _registry_cache


def skill_names() -> list[str]:
    return list(registry().keys())


def get_skill(name: str) -> SkillTask:
    tasks = registry()
    try:
        return tasks[name]
    except KeyError as e:
        supported = ", ".join(tasks) or "(none)"
        raise ValueError(f"unsupported skill: {name!r}; known: {supported}") from e


def default_version(name: str) -> str:
    return get_skill(name).version


def evidence_from_sessions_for(
    name: str,
    sessions: Sequence[Any],
    *,
    version: str | None = None,
    max_chars: int = 8000,
) -> list[Any]:
    """Build RunEvidence list for a registered skill."""
    task = get_skill(name)
    ver = version or task.version
    return task.evidence_from_sessions(list(sessions), version=ver, max_chars=max_chars)


def module_stem_for_skill(skill_name: str) -> str:
    """Map skill directory name to Python module stem (``to-spec`` → ``to_spec``)."""
    return skill_name.replace("-", "_")
