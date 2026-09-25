"""Aggregate scored skill runs into a next-stage evaluation brief."""

from __future__ import annotations

import contextlib
import json
import re
from typing import TYPE_CHECKING

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


def _add_clm_gaps(gaps: dict[str, int], rows: list[RunSignalRow]) -> None:
    """Shared CLM outcome tallies used by every skill brief."""
    for row in rows:
        if row.outcome in {"failed", "insufficient_evidence"}:
            gaps["clm_failed_or_insufficient"] += 1
        if row.outcome == "failed" and row.skill_helped is not None and row.skill_helped >= 0.5:
            gaps["clm_helped_but_failed"] += 1


def _row_markdown_clm_cells(row: RunSignalRow) -> list[str]:
    """Shared leading cells: run id, outcome, helped, evidence."""
    helped = f"{row.skill_helped:.3f}" if row.skill_helped is not None else "—"
    evid = f"{row.evidence_quality:.2f}" if row.evidence_quality is not None else "—"
    return [
        f"`{row.run_id[:8]}`",
        row.outcome or "—",
        helped,
        evid,
    ]


def _issue_tracker_brief(
    rows: list[RunSignalRow],
    *,
    baseline_version: str,
    recommended_version: str,
) -> NextStageBrief:
    gaps: dict[str, int] = {
        "zero_search": 0,
        "create_without_related_gate": 0,
        "create_without_remote_check": 0,
        "create_without_label_signal": 0,
        "multi_create_without_deps": 0,
        "clm_failed_or_insufficient": 0,
        "clm_helped_but_failed": 0,
    }
    for row in rows:
        if row.searches == 0:
            gaps["zero_search"] += 1
        if row.creates > 0 and row.related_gate_before_create == "no":
            gaps["create_without_related_gate"] += 1
        if row.creates > 0 and row.remote_checks == 0:
            gaps["create_without_remote_check"] += 1
        if row.creates > 0 and row.labels == 0:
            gaps["create_without_label_signal"] += 1
        if row.creates > 1 and row.deps == 0:
            gaps["multi_create_without_deps"] += 1
    _add_clm_gaps(gaps, rows)

    priorities = [
        "Working-on-issue related discovery: when already on #N, search/list for "
        "blockers, duplicates, and parallel work before editing or spawning children.",
        "Hard gate before publish: refuse gh issue create until related_gate=yes "
        "(list and/or search) and candidates are named in the draft body.",
        "Remote confirmation: require git remote -v (or equivalent) before any write.",
        "Triage label checklist: map every create/edit to triage-labels.md roles and "
        "record the applied label in the run summary.",
        "Dependency pairing: when creating 2+ related tickets, set blocked_by edges "
        "(or explicit Blocked by lines) in the same operation.",
    ]
    acceptance = [
        f"On a fresh agent corpus with issue-tracker@{recommended_version} injected, "
        "searches+lists > 0 on every create run.",
        "related_gate_before_create=yes for 100% of create runs.",
        "remote_checks >= 1 on every write run.",
        "CLM outcome succeeded|partially_succeeded share rises vs "
        f"{baseline_version} baseline on matched tasks.",
        "Human spot-check: drafts name candidate related issues before publish.",
    ]
    return NextStageBrief(
        skill="issue-tracker",
        baseline_version=baseline_version,
        runs_analyzed=len(rows),
        gap_counts=gaps,
        recommended_version=recommended_version,
        priorities=priorities,
        acceptance_checks=acceptance,
    )


def _to_spec_brief(
    rows: list[RunSignalRow],
    *,
    baseline_version: str,
    recommended_version: str,
) -> NextStageBrief:
    gaps: dict[str, int] = {
        "incomplete_spec_sections": 0,
        "interviewed_user": 0,
        "no_seams_check": 0,
        "publish_without_issue_tracker": 0,
        "publish_without_ready_label": 0,
        "clm_failed_or_insufficient": 0,
        "clm_helped_but_failed": 0,
    }
    for row in rows:
        if row.spec_sections_hit < row.spec_sections_total:
            gaps["incomplete_spec_sections"] += 1
        if row.interviewed:
            gaps["interviewed_user"] += 1
        if not row.seams_checked:
            gaps["no_seams_check"] += 1
        if row.published_creates > 0 and not row.used_issue_tracker:
            gaps["publish_without_issue_tracker"] += 1
        if row.published_creates > 0 and not row.ready_for_agent_label:
            gaps["publish_without_ready_label"] += 1
    _add_clm_gaps(gaps, rows)

    priorities = [
        "Mandate full template coverage before publish (all six core sections present).",
        "Keep no-interview rule explicit; if context is insufficient, say what is missing "
        "in Further Notes instead of grilling.",
        "Require a short seams proposal + user confirmation checkpoint before drafting "
        "Implementation/Testing Decisions.",
        "Always load/follow sibling issue-tracker for publish (authz, related-issue gate, "
        "ready-for-agent); install from jborkowski/wikiskill if missing.",
        "When publishing, include ready-for-agent and name related-issue candidates in "
        "the issue body per issue-tracker hard publish gate.",
    ]
    acceptance = [
        f"Fresh corpus with to-spec@{recommended_version}: spec_sections == 6/6 on "
        "every successful publish run.",
        "interviewed=false on >= 90% of in-scope runs.",
        "seams_checked=true before publish on every create run.",
        "used_issue_tracker=true whenever published_creates > 0.",
        f"CLM succeeded|partially_succeeded share rises vs {baseline_version} on matched tasks.",
    ]
    return NextStageBrief(
        skill="to-spec",
        baseline_version=baseline_version,
        runs_analyzed=len(rows),
        gap_counts=gaps,
        recommended_version=recommended_version,
        priorities=priorities,
        acceptance_checks=acceptance,
    )


def build_next_stage_brief(
    rows: list[RunSignalRow],
    *,
    skill: str = "issue-tracker",
    baseline_version: str = "0.2.0",
    recommended_version: str = "0.3.0",
) -> NextStageBrief:
    if skill == "to-spec":
        return _to_spec_brief(
            rows,
            baseline_version=baseline_version,
            recommended_version=recommended_version,
        )
    if skill == "issue-tracker":
        return _issue_tracker_brief(
            rows,
            baseline_version=baseline_version,
            recommended_version=recommended_version,
        )
    raise ValueError(f"unsupported skill for next-stage: {skill!r}")


def _row_markdown_issue_tracker(row: RunSignalRow) -> str:
    cells = [
        *_row_markdown_clm_cells(row),
        str(row.creates),
        str(row.lists),
        str(row.views),
        str(row.searches),
        str(row.labels),
        str(row.deps),
        str(row.remote_checks),
        row.related_gate_before_create,
    ]
    return "| " + " | ".join(cells) + " |"


def _row_markdown_to_spec(row: RunSignalRow) -> str:
    cells = [
        *_row_markdown_clm_cells(row),
        f"{row.spec_sections_hit}/{row.spec_sections_total}",
        str(row.interviewed).lower(),
        str(row.seams_checked).lower(),
        str(row.used_issue_tracker).lower(),
        str(row.published_creates),
        str(row.ready_for_agent_label).lower(),
    ]
    return "| " + " | ".join(cells) + " |"


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
    if brief.skill == "to-spec":
        lines.extend(
            [
                "| run | outcome | helped | evid | sections | interviewed | seams | "
                "issue_tracker | creates | ready_label |",
                "| --- | --- | ---: | ---: | ---: | --- | --- | --- | ---: | --- |",
            ]
        )
        lines.extend(_row_markdown_to_spec(row) for row in rows)
    else:
        lines.extend(
            [
                "| run | outcome | helped | evid | creates | lists | views | searches | "
                "labels | deps | remote | related_gate |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        lines.extend(_row_markdown_issue_tracker(row) for row in rows)
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
