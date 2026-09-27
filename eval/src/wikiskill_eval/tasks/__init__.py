"""Task-specific filters and RunEvidence builders.

Skills register automatically: any module here that exports ``SKILL_NAME``,
``SKILL_VERSION``, and ``evidence_from_sessions`` is picked up by
``wikiskill_eval.tasks.registry``. Bootstrap new skills with
``uv run bootstrap-skill <name>``.
"""

from wikiskill_eval.tasks.registry import (
    clear_registry_cache,
    get_skill,
    registry,
    skill_names,
)

__all__ = [
    "clear_registry_cache",
    "get_skill",
    "registry",
    "skill_names",
]
