"""Score agent sessions for a pinned skill (Pi JSONL → EvaluationRecord)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from wikiskill_eval.ingest.pi import load_pi_sessions_dir
from wikiskill_eval.pipeline import Evaluator
from wikiskill_eval.tasks import issue_tracker
from wikiskill_eval.types import EvaluationRecord, RunEvidence, StrictModel


class ScoreSessionsResult(StrictModel):
    """Summary of a score-sessions run."""

    sessions_scanned: int
    in_scope: int
    scored: int
    out_dir: str
    skill: str
    version: str


def resolve_sessions_dir(sessions_dir: str | None) -> Path:
    """Resolve sessions directory from CLI arg or ``WIKISKILL_SESSIONS_DIR``."""
    raw = sessions_dir or os.environ.get("WIKISKILL_SESSIONS_DIR")
    if not raw or not raw.strip():
        msg = (
            "sessions dir required: pass --sessions-dir or set WIKISKILL_SESSIONS_DIR "
            "(e.g. $HOME/.pi/agent/sessions/<project-key>/)"
        )
        raise ValueError(msg)
    path = Path(raw).expanduser().resolve()
    if not path.is_dir():
        raise FileNotFoundError(f"sessions dir not found: {path}")
    return path


def build_evidence_for_skill(
    sessions_dir: Path,
    *,
    skill: str = "issue-tracker",
    version: str | None = None,
    max_chars: int = 8000,
) -> list[RunEvidence]:
    """Load Pi sessions and build RunEvidence for the requested skill."""
    sessions = load_pi_sessions_dir(sessions_dir)
    if skill != "issue-tracker":
        raise ValueError(f"unsupported skill: {skill!r}")
    ver = version or issue_tracker.SKILL_VERSION
    return issue_tracker.evidence_from_sessions(sessions, version=ver, max_chars=max_chars)


def write_json(path: Path, model: StrictModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(model.model_dump_json(indent=2) + "\n", encoding="utf-8")


def score_sessions(
    *,
    sessions_dir: Path,
    out_dir: Path,
    skill: str = "issue-tracker",
    version: str | None = None,
    max_chars: int = 8000,
    evidence_only: bool = False,
    evaluator: Evaluator | None = None,
) -> ScoreSessionsResult:
    """Ingest sessions, optionally score with CLM, write JSON under ``out_dir``."""
    sessions = load_pi_sessions_dir(sessions_dir)
    evidence = build_evidence_for_skill(
        sessions_dir,
        skill=skill,
        version=version,
        max_chars=max_chars,
    )
    ver = version or (issue_tracker.SKILL_VERSION if skill == "issue-tracker" else "0.0.0")
    out_dir.mkdir(parents=True, exist_ok=True)

    evidence_dir = out_dir / "evidence"
    records_dir = out_dir / "evaluations"
    for item in evidence:
        write_json(evidence_dir / f"{item.run_id}.json", item)

    scored = 0
    if not evidence_only:
        ev = evaluator or Evaluator()
        if not ev.healthy():
            raise RuntimeError(
                "CLM evaluator unhealthy; start stack via EvalRuntime or pass a live client"
            )
        records: list[EvaluationRecord] = ev.evaluate_many(evidence)
        for record in records:
            write_json(records_dir / f"{record.run_id}.json", record)
            scored += 1

    # Manifest without absolute sessions path (privacy)
    manifest = {
        "skill": skill,
        "version": ver,
        "sessions_scanned": len(sessions),
        "in_scope": len(evidence),
        "scored": scored,
        "evidence_only": evidence_only,
        "run_ids": [e.run_id for e in evidence],
    }
    _ = (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    return ScoreSessionsResult(
        sessions_scanned=len(sessions),
        in_scope=len(evidence),
        scored=scored,
        out_dir=str(out_dir),
        skill=skill,
        version=ver,
    )
