"""Aggregate scored skill runs into a next-stage evaluation brief."""

from __future__ import annotations

import contextlib
import json
import re
from typing import TYPE_CHECKING

from wikiskill_eval.tasks.registry import get_skill
from wikiskill_eval.types import StrictModel

if TYPE_CHECKING:
    from pathlib import Path


class RunSignalRow(StrictModel):
    run_id: str
    outcome: str | None = None
    skill_helped: float | None = None
    evidence_quality: float | None = None
    creates: int = 0
    lists: int = 0
    views: int = 0
    searches: int = 0
    labels: int = 0
    deps: int = 0
    remote_checks: int = 0
    related_gate_before_create: str = "unknown"
    # to-spec extras (0 when absent)
    spec_sections_hit: int = 0
    spec_sections_total: int = 6
    interviewed: bool = False
    seams_checked: bool = False
    used_issue_tracker: bool = False
    published_creates: int = 0
    ready_for_agent_label: bool = False


class NextStageBrief(StrictModel):
    skill: str
    baseline_version: str
    runs_analyzed: int
    gap_counts: dict[str, int]
    recommended_version: str
    priorities: list[str]
    acceptance_checks: list[str]


_KV_RE = re.compile(r"([a-z0-9_]+)=([^;]+)")

_GENERIC_SIGNAL_HEADER = "| run | outcome | helped | evid |\n| --- | --- | ---: | ---: |"


def parse_outcome_signals(observed_outcome: str) -> dict[str, str]:
    return {m.group(1): m.group(2).strip() for m in _KV_RE.finditer(observed_outcome)}


def _int(raw: str | None, default: int = 0) -> int:
    if raw is None:
        return default
    # allow "3/6" style — take numerator
    if "/" in raw:
        raw = raw.split("/", 1)[0]
    try:
        return int(raw)
    except ValueError:
        return default


def _bool(raw: str | None, default: bool = False) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y"}


def load_run_rows(runs_dir: Path) -> list[RunSignalRow]:
    """Load paired evidence + evaluation JSON from a score-sessions out dir."""
    evidence_dir = runs_dir / "evidence"
    eval_dir = runs_dir / "evaluations"
    rows: list[RunSignalRow] = []
    if not evidence_dir.is_dir():
        raise FileNotFoundError(f"missing evidence dir: {evidence_dir}")
    for path in sorted(evidence_dir.glob("*.json")):
        evidence = json.loads(path.read_text(encoding="utf-8"))
        signals = parse_outcome_signals(str(evidence.get("observed_outcome", "")))
        outcome = None
        helped = None
        evid = None
        eval_path = eval_dir / path.name
        if eval_path.is_file():
            record = json.loads(eval_path.read_text(encoding="utf-8"))
            scores = record.get("scores") or {}
            outcome = (scores.get("outcome") or {}).get("choice")
            helped_raw = (scores.get("skill_helped") or {}).get("noul")
            evid_raw = (scores.get("evidence_quality") or {}).get("score")
            helped = float(helped_raw) if helped_raw is not None else None
            evid = float(evid_raw) if evid_raw is not None else None
        sections_raw = signals.get("spec_sections", "0/6")
        hit, total = 0, 6
        if "/" in sections_raw:
            left, right = sections_raw.split("/", 1)
            hit, total = _int(left), _int(right, 6)
        rows.append(
            RunSignalRow(
                run_id=str(evidence.get("run_id", path.stem)),
                outcome=str(outcome) if outcome else None,
                skill_helped=helped,
                evidence_quality=evid,
                creates=_int(signals.get("creates")),
                lists=_int(signals.get("lists")),
                views=_int(signals.get("views")),
                searches=_int(signals.get("searches")),
                labels=_int(signals.get("labels")),
                deps=_int(signals.get("deps")),
                remote_checks=_int(signals.get("remote_checks")),
                related_gate_before_create=signals.get("related_gate_before_create", "unknown"),
                spec_sections_hit=hit,
                spec_sections_total=total,
                interviewed=_bool(signals.get("interviewed")),
                seams_checked=_bool(signals.get("seams_checked")),
                used_issue_tracker=_bool(signals.get("used_issue_tracker")),
                published_creates=_int(signals.get("published_creates")),
                ready_for_agent_label=_bool(signals.get("ready_for_agent_label")),
            )
        )
    return rows


def add_clm_gaps(gaps: dict[str, int], rows: list[RunSignalRow]) -> None:
    """Shared CLM outcome tallies used by every skill brief."""
    for row in rows:
        if row.outcome in {"failed", "insufficient_evidence"}:
            gaps["clm_failed_or_insufficient"] += 1
        if row.outcome == "failed" and row.skill_helped is not None and row.skill_helped >= 0.5:
            gaps["clm_helped_but_failed"] += 1


def row_markdown_clm_cells(row: RunSignalRow) -> list[str]:
    """Shared leading cells: run id, outcome, helped, evidence."""
    helped = f"{row.skill_helped:.3f}" if row.skill_helped is not None else "—"
    evid = f"{row.evidence_quality:.2f}" if row.evidence_quality is not None else "—"
    return [
        f"`{row.run_id[:8]}`",
        row.outcome or "—",
        helped,
        evid,
    ]


def _generic_brief(
    rows: list[RunSignalRow],
    *,
    skill: str,
    baseline_version: str,
    recommended_version: str,
) -> NextStageBrief:
    gaps: dict[str, int] = {
        "clm_failed_or_insufficient": 0,
        "clm_helped_but_failed": 0,
    }
    add_clm_gaps(gaps, rows)
    return NextStageBrief(
        skill=skill,
        baseline_version=baseline_version,
        runs_analyzed=len(rows),
        gap_counts=gaps,
        recommended_version=recommended_version,
        priorities=[
            f"Define skill-specific behavioral signals in "
            f"`eval/src/wikiskill_eval/tasks/` for `{skill}`.",
            "Replace this generic CLM-only brief with gap counts tied to the skill procedure.",
            f"Re-score a fresh corpus with `{skill}@{recommended_version}` injected and "
            "compare CLM outcome share vs baseline.",
        ],
        acceptance_checks=[
            f"Task module for `{skill}` exposes custom `build_next_stage_brief` "
            "(not the generic stub).",
            "CLM outcome succeeded|partially_succeeded share rises vs "
            f"{baseline_version} on matched tasks.",
            "Human spot-check: sample failed/insufficient runs against the skill text.",
        ],
    )


def _generic_signal_row(row: RunSignalRow) -> str:
    return "| " + " | ".join(row_markdown_clm_cells(row)) + " |"


def build_next_stage_brief(
    rows: list[RunSignalRow],
    *,
    skill: str = "issue-tracker",
    baseline_version: str = "0.2.0",
    recommended_version: str = "0.3.0",
) -> NextStageBrief:
    task = get_skill(skill)
    if task.build_next_stage_brief is not None:
        return task.build_next_stage_brief(
            rows,
            baseline_version=baseline_version,
            recommended_version=recommended_version,
        )
    return _generic_brief(
        rows,
        skill=skill,
        baseline_version=baseline_version,
        recommended_version=recommended_version,
    )


def render_next_stage_markdown(brief: NextStageBrief, rows: list[RunSignalRow]) -> str:
    lines = [
        f"# Next-stage evaluation: `{brief.skill}`",
        "",
        f"Baseline scored version: `{brief.baseline_version}`. "
        f"Recommended next version: `{brief.recommended_version}`.",
        "",
        f"Runs analyzed: **{brief.runs_analyzed}** (evidence + CLM evaluations).",
        "",
        "## Behavioral gap counts",
        "",
        "| Gap | Count |",
        "| --- | ---: |",
    ]
    lines.extend(f"| `{key}` | {value} |" for key, value in brief.gap_counts.items())
    lines.extend(["", "## Per-run signals", ""])

    task = get_skill(brief.skill)
    header = task.signal_table_header or _GENERIC_SIGNAL_HEADER
    render = task.render_signal_row or _generic_signal_row
    lines.extend(header.splitlines())
    lines.extend(render(row) for row in rows)
    lines.extend(["", "## Priorities for next skill stage", ""])
    lines.extend(f"{i}. {item}" for i, item in enumerate(brief.priorities, 1))
    lines.extend(["", "## Acceptance checks for the next stage", ""])
    lines.extend(f"- [ ] {item}" for item in brief.acceptance_checks)
    lines.append("")
    return "\n".join(lines)


def write_next_stage_report(
    runs_dir: Path,
    out_md: Path,
    *,
    skill: str | None = None,
    baseline_version: str = "0.2.0",
    recommended_version: str = "0.3.0",
) -> NextStageBrief:
    """Write markdown + JSON brief. Explicit ``skill`` wins; else use manifest."""
    rows = load_run_rows(runs_dir)
    resolved = skill
    if resolved is None:
        manifest_path = runs_dir / "manifest.json"
        if manifest_path.is_file():
            with contextlib.suppress(json.JSONDecodeError):
                resolved = str(
                    json.loads(manifest_path.read_text(encoding="utf-8")).get("skill") or ""
                )
        resolved = resolved or "issue-tracker"
    # Validate against registry (raises ValueError if unknown)
    _ = get_skill(resolved)
    brief = build_next_stage_brief(
        rows,
        skill=resolved,
        baseline_version=baseline_version,
        recommended_version=recommended_version,
    )
    out_md.parent.mkdir(parents=True, exist_ok=True)
    _ = out_md.write_text(render_next_stage_markdown(brief, rows), encoding="utf-8")
    brief_path = out_md.with_suffix(".json")
    _ = brief_path.write_text(brief.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return brief
