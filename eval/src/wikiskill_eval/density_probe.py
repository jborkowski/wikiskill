"""Skill density probe: CLM text score + cursor-agent line ablation plan.

Finds the sweet spot between under-specified skills and padded slop by:
1. Scoring the skill markdown alone (density / action-pointing / slop risk).
2. Splitting the body into instruction atoms (lines that point at actions).
3. Writing variants + a ``run.sh`` that drives ``cursor-agent --yolo --print``.

Artifacts land under ``eval/.runs/density-<skill>/`` (gitignored).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from pydantic import Field

from wikiskill_eval.client import EvalClient
from wikiskill_eval.rubric import SKILL_DENSITY_CRITERIA, build_skill_text_questions
from wikiskill_eval.skill_io import read_skill_text, repo_root_from, skill_md_path
from wikiskill_eval.types import StrictModel

_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
_ATOM_RE = re.compile(
    r"^(?:"
    r"[-*]\s+"  # bullets
    r"|\d+[.)]\s+"  # numbered
    r"|#{1,3}\s+"  # headings kept as atoms when imperative-ish
    r")"
    r"(.+)$"
)


@dataclass(frozen=True, slots=True)
class InstructionAtom:
    index: int
    line: str
    kind: str  # bullet | numbered | heading | bare


class DensityTextScores(StrictModel):
    skill: str
    skill_density: float
    skill_density_label: str
    action_pointing: float
    slop_risk: float
    legend: list[str]
    raw: dict[str, Any]


class DensityProbeResult(StrictModel):
    skill: str
    out_dir: str
    atom_count: int
    variants: list[str]
    text_scores: DensityTextScores | None = None
    run_script: str
    executed: list[str] = Field(default_factory=list)


def split_frontmatter(text: str) -> tuple[str, str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return "", text
    return match.group(0), text[match.end() :]


def extract_atoms(body: str) -> list[InstructionAtom]:
    """Pull imperative-ish lines: bullets, numbered steps, short bare imperatives."""
    atoms: list[InstructionAtom] = []
    for raw in body.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        m = _ATOM_RE.match(line.strip())
        if m:
            kind = (
                "heading"
                if line.lstrip().startswith("#")
                else ("numbered" if re.match(r"^\d", line.lstrip()) else "bullet")
            )
            content = m.group(1).strip() if m.lastindex else line.strip()
            # skip pure section titles with no verb-ish content unless short command
            atoms.append(InstructionAtom(index=len(atoms), line=content, kind=kind))
            continue
        # bare imperative: starts with Verb and is short
        stripped = line.strip()
        if (
            re.match(r"^[A-Z][a-z]+(?:\s|$)", stripped)
            and len(stripped) < 200
            and not stripped.endswith(":")
        ):
            atoms.append(InstructionAtom(index=len(atoms), line=stripped, kind="bare"))
    return atoms


def _variant_skill(frontmatter: str, body_lines: list[str]) -> str:
    body = "\n".join(body_lines).strip() + "\n"
    return f"{frontmatter}{body}" if frontmatter else body


def build_variants(skill_text: str, atoms: list[InstructionAtom]) -> dict[str, str]:
    frontmatter, _body = split_frontmatter(skill_text)
    variants: dict[str, str] = {
        "as_is": skill_text if skill_text.endswith("\n") else skill_text + "\n",
        "atoms_only": _variant_skill(
            frontmatter,
            [f"{i + 1}. {a.line}" for i, a in enumerate(atoms)]
            or ["1. (no instruction atoms extracted)"],
        ),
    }
    # single-atom: which line alone points the agent
    for atom in atoms:
        key = f"only_{atom.index:02d}"
        variants[key] = _variant_skill(
            frontmatter,
            [
                "Follow ONLY this instruction from the skill:",
                f"1. {atom.line}",
            ],
        )
    # leave-one-out: which line's absence disturbs
    if len(atoms) >= 2:
        for atom in atoms:
            kept = [a for a in atoms if a.index != atom.index]
            key = f"drop_{atom.index:02d}"
            variants[key] = _variant_skill(
                frontmatter,
                [f"{i + 1}. {a.line}" for i, a in enumerate(kept)],
            )
    return variants


def score_skill_text(client: EvalClient, skill_name: str, skill_text: str) -> DensityTextScores:
    state = f"Skill name: {skill_name}\n\nSkill document:\n{skill_text}"
    response = client.system_one(state, questions=build_skill_text_questions())
    answers = response.answers
    density = answers["skill_density"]
    score_val = float(density.score)
    # Map score onto legend buckets (CLM Score returns continuous + legend)
    legend = list(SKILL_DENSITY_CRITERIA)
    # Approximate label from nearest criterion index
    label_idx = min(max(round(score_val), 0), len(legend) - 1)
    # CLM scores are often 0..n-1 or 1..n — clamp via probabilities if present
    probs = dict(getattr(density, "probabilities", {}) or {})
    label = legend[label_idx]
    if probs:
        # pick max-prob key if keys look like indices or criterion snippets
        best_key = max(probs, key=lambda k: float(probs[k]))
        for i, crit in enumerate(legend):
            if str(i) == str(best_key) or crit.startswith(str(best_key)):
                label = crit
                break
    return DensityTextScores(
        skill=skill_name,
        skill_density=score_val,
        skill_density_label=label,
        action_pointing=float(answers["action_pointing"].noul),
        slop_risk=float(answers["slop_risk"].noul),
        legend=legend,
        raw={
            "skill_density": {
                "score": score_val,
                "probabilities": probs,
            },
            "action_pointing": float(answers["action_pointing"].noul),
            "slop_risk": float(answers["slop_risk"].noul),
        },
    )


def _agent_prompt(skill_body: str, user_task: str) -> str:
    return (
        "You are running a density probe. Follow the skill below EXACTLY. "
        "Do not invent extra process. Complete the task, then stop.\n\n"
        "===== SKILL (variant under test) =====\n"
        f"{skill_body.strip()}\n"
        "===== END SKILL =====\n\n"
        f"Task: {user_task}\n"
    )


def write_probe_bundle(
    *,
    skill_name: str,
    user_task: str,
    out_dir: Path,
    variants: dict[str, str],
    atoms: list[InstructionAtom],
    text_scores: DensityTextScores | None,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    variants_dir = out_dir / "variants"
    prompts_dir = out_dir / "prompts"
    logs_dir = out_dir / "logs"
    for d in (variants_dir, prompts_dir, logs_dir):
        d.mkdir(exist_ok=True)

    for name, text in variants.items():
        (variants_dir / f"{name}.md").write_text(text, encoding="utf-8")
        (prompts_dir / f"{name}.txt").write_text(
            _agent_prompt(text, user_task), encoding="utf-8"
        )

    atoms_path = out_dir / "atoms.json"
    atoms_path.write_text(
        json.dumps([asdict(a) for a in atoms], indent=2) + "\n",
        encoding="utf-8",
    )
    if text_scores is not None:
        (out_dir / "text_scores.json").write_text(
            text_scores.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )

    plan = {
        "skill": skill_name,
        "task": user_task,
        "atoms": [asdict(a) for a in atoms],
        "variants": list(variants.keys()),
        "sweet_spot_note": (
            "Compare logs/: only_* shows which single line drives action; "
            "drop_* shows which line's absence disturbs behavior; "
            "atoms_only vs as_is shows dense spine vs full document slop."
        ),
        "text_scores": text_scores.model_dump() if text_scores else None,
    }
    (out_dir / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

    run_sh = out_dir / "run.sh"
    # Workspace = out_dir/workspaces/<variant> — empty sandbox, not the pack repo
    script = """#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
AGENT="${CURSOR_AGENT:-cursor-agent}"
if ! command -v "$AGENT" >/dev/null 2>&1; then
  echo "FAIL: cursor-agent not found (set CURSOR_AGENT=...)" >&2
  exit 1
fi
mkdir -p "$ROOT/logs" "$ROOT/workspaces"
for prompt in "$ROOT"/prompts/*.txt; do
  name="$(basename "$prompt" .txt)"
  ws="$ROOT/workspaces/$name"
  mkdir -p "$ws"
  echo "=== probe variant=$name ==="
  "$AGENT" --yolo --print --trust --workspace "$ws" "$(cat "$prompt")" \\
    | tee "$ROOT/logs/$name.txt"
done
echo "PASS: logs under $ROOT/logs — compare only_* vs drop_* vs as_is/atoms_only"
"""
    run_sh.write_text(script, encoding="utf-8")
    run_sh.chmod(0o755)
    return run_sh


def run_cursor_agent_variant(
    *,
    prompt_path: Path,
    workspace: Path,
    log_path: Path,
    agent_bin: str = "cursor-agent",
) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    prompt = prompt_path.read_text(encoding="utf-8")
    cmd = [
        agent_bin,
        "--yolo",
        "--print",
        "--trust",
        "--workspace",
        str(workspace),
        prompt,  # positional prompt (cursor-agent has no --prompt flag)
    ]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.run(
            cmd,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
        )
    if proc.returncode != 0:
        raise RuntimeError(
            f"cursor-agent failed for {prompt_path.name} (exit {proc.returncode}); "
            f"see {log_path}"
        )


def prepare_density_probe(
    *,
    skill_name: str,
    user_task: str,
    out_dir: Path | None = None,
    client: EvalClient | None = None,
    score_text: bool = True,
    execute: bool = False,
    execute_variants: list[str] | None = None,
    agent_bin: str = "cursor-agent",
    repo_root: Path | None = None,
) -> DensityProbeResult:
    root = repo_root or repo_root_from()
    _ = skill_md_path(skill_name, repo_root=root)
    skill_text = read_skill_text(skill_name, repo_root=root)
    atoms = extract_atoms(split_frontmatter(skill_text)[1])
    variants = build_variants(skill_text, atoms)

    dest = out_dir or (root / "eval" / ".runs" / f"density-{skill_name}-{uuid.uuid4().hex[:8]}")
    if not dest.is_absolute():
        dest = Path.cwd() / dest

    text_scores: DensityTextScores | None = None
    if score_text:
        ev = client or EvalClient()
        if not ev.health():
            raise RuntimeError("CLM unhealthy; start via EvalRuntime or pass a live client")
        text_scores = score_skill_text(ev, skill_name, skill_text)

    run_sh = write_probe_bundle(
        skill_name=skill_name,
        user_task=user_task,
        out_dir=dest,
        variants=variants,
        atoms=atoms,
        text_scores=text_scores,
    )

    executed: list[str] = []
    if execute:
        if shutil.which(agent_bin) is None:
            raise FileNotFoundError(f"agent binary not found: {agent_bin}")
        names = execute_variants or ["as_is", "atoms_only"]
        for name in names:
            prompt = dest / "prompts" / f"{name}.txt"
            if not prompt.is_file():
                raise FileNotFoundError(f"missing variant prompt: {prompt}")
            run_cursor_agent_variant(
                prompt_path=prompt,
                workspace=dest / "workspaces" / name,
                log_path=dest / "logs" / f"{name}.txt",
                agent_bin=agent_bin,
            )
            executed.append(name)

    return DensityProbeResult(
        skill=skill_name,
        out_dir=str(dest),
        atom_count=len(atoms),
        variants=list(variants.keys()),
        text_scores=text_scores,
        run_script=str(run_sh),
        executed=executed,
    )

