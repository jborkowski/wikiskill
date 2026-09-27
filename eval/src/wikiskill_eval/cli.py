"""Program entry: ``uv run eval <command>``.

Commands:
  run             — smoke: invoice System One (department=billing)
  commit-msg      — hard gate: CLM judges commit message (reject slop / weak density)
  score-sessions  — Pi sessions → RunEvidence / EvaluationRecord under out dir
  next-stage      — aggregate scored runs → next skill-stage evaluation brief
  density-probe   — skill density vs slop + cursor-agent --yolo line ablation
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from wikiskill_eval import EvalClient, EvalConfig
from wikiskill_eval.commit_msg import evaluate_commit_msg, verify_commit_msg
from wikiskill_eval.density_probe import prepare_density_probe
from wikiskill_eval.next_stage import write_next_stage_report
from wikiskill_eval.pipeline import Evaluator
from wikiskill_eval.runtime import EvalRuntime
from wikiskill_eval.score_sessions import resolve_sessions_dir, score_sessions
from wikiskill_eval.tasks.registry import skill_names


def verify_invoice_demo(response: object) -> None:
    """Predicate: CLM ranks billing for the classic double-charge invoice state."""
    answers = getattr(response, "answers", None)
    if not isinstance(answers, dict) or "department" not in answers:
        raise AssertionError("missing department answer")
    dept = answers["department"]
    choice = str(getattr(dept, "choice", ""))
    probs = dict(getattr(dept, "probabilities", {}) or {})
    billing = float(probs.get("billing", 0.0))
    if choice != "billing":
        raise AssertionError(f"expected department=billing, got {choice!r} probs={probs}")
    if billing < 0.5:
        raise AssertionError(f"expected billing prob >= 0.5, got {billing} probs={probs}")


def _client(runtime: EvalRuntime) -> EvalClient:
    client = EvalClient(EvalConfig(base_url=runtime.clm_base_url))
    if not client.health():
        raise RuntimeError(f"clm-serve unhealthy at {runtime.clm_base_url}")
    return client


def cmd_run() -> int:
    with EvalRuntime() as runtime:
        client = _client(runtime)
        from clm import Choice, Noul, Score

        response = client.system_one(
            state="Customer: my invoice was charged twice and nobody answers the phone!",
            questions={
                "urgency": Noul(instructions="Is this urgent?"),
                "department": Choice(
                    instructions="Which team should handle this?",
                    criteria={
                        "billing": "Charges, invoices, refunds",
                        "technical": "Bugs and outages",
                    },
                ),
                "frustration": Score(
                    instructions="How frustrated is the customer?",
                    criteria=["Calm", "Frustrated", "Very angry"],
                ),
            },
        )
        try:
            verify_invoice_demo(response)
        except AssertionError as e:
            print(f"FAIL: {e}", file=sys.stderr)
            return 1

        probs = dict(response.answers["department"].probabilities)
        print(f"PASS: department=billing billing_prob={probs['billing']:.4f}")
        return 0


def _print_commit_scores(response: object, *, stream: object = sys.stdout) -> None:
    answers = getattr(response, "answers", {})
    quality = answers["quality"]
    qprobs = dict(quality.probabilities)
    print(
        f"format={float(answers['format'].noul):.4f} "
        f"quality={quality.choice} ({qprobs.get(quality.choice, 0.0):.4f}) "
        f"not_slop={float(answers['not_slop'].noul):.4f}",
        file=stream,  # type: ignore[arg-type]
    )


def cmd_commit_msg(message: str) -> int:
    """Hard gate: PASS/FAIL. Fails closed if CLM cannot start."""
    text = message.strip()
    if not text:
        print("FAIL: empty commit message", file=sys.stderr)
        return 1

    try:
        with EvalRuntime() as runtime:
            client = _client(runtime)
            response = evaluate_commit_msg(client, text)
    except (ValueError, RuntimeError, TimeoutError, OSError) as e:
        print(f"FAIL: commit-msg CLM unavailable ({e})", file=sys.stderr)
        return 1

    try:
        verify_commit_msg(response)
    except AssertionError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        _print_commit_scores(response, stream=sys.stderr)
        return 1

    print("PASS: ", end="")
    _print_commit_scores(response)
    return 0


def cmd_score_sessions(argv: list[str]) -> int:
    """Score Pi sessions for a skill (path via flag or WIKISKILL_SESSIONS_DIR)."""
    skills = skill_names()
    parser = argparse.ArgumentParser(
        prog="eval score-sessions",
        description=(
            "Ingest Pi agent session JSONL and score skill runs with CLM "
            f"({(' | '.join(skills)) or 'no skills registered'}). "
            "Pass --sessions-dir or set WIKISKILL_SESSIONS_DIR "
            "(e.g. $HOME/.pi/agent/sessions/<project-key>/). "
            "Do not commit raw transcripts."
        ),
    )
    parser.add_argument(
        "--sessions-dir",
        default=None,
        help="Directory of Pi *.jsonl sessions (or WIKISKILL_SESSIONS_DIR)",
    )
    parser.add_argument(
        "--skill",
        default="issue-tracker",
        choices=skills,
        help="Skill to evaluate (default: issue-tracker)",
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Skill version label for SkillRef (default: skill module constant)",
    )
    parser.add_argument(
        "--out",
        default="eval/.runs",
        help="Output directory for evidence/evaluations (default: eval/.runs)",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=8000,
        help="Truncation budget for RunEvidence state text",
    )
    parser.add_argument(
        "--evidence-only",
        action="store_true",
        help="Write RunEvidence JSON only; skip CLM scoring",
    )
    args = parser.parse_args(argv)

    try:
        sessions_dir = resolve_sessions_dir(args.sessions_dir)
    except (ValueError, FileNotFoundError) as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 2

    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        # Prefer repo-root-relative when invoked via uv from workspace root
        out_dir = Path.cwd() / out_dir

    try:
        if args.evidence_only:
            result = score_sessions(
                sessions_dir=sessions_dir,
                out_dir=out_dir,
                skill=args.skill,
                version=args.version,
                max_chars=args.max_chars,
                evidence_only=True,
            )
        else:
            with EvalRuntime() as runtime:
                client = _client(runtime)
                result = score_sessions(
                    sessions_dir=sessions_dir,
                    out_dir=out_dir,
                    skill=args.skill,
                    version=args.version,
                    max_chars=args.max_chars,
                    evidence_only=False,
                    evaluator=Evaluator(client=client),
                )
    except (ValueError, RuntimeError, TimeoutError, OSError, FileNotFoundError) as e:
        print(f"FAIL: score-sessions ({e})", file=sys.stderr)
        return 1

    print(
        f"PASS: skill={result.skill}@{result.version} "
        f"scanned={result.sessions_scanned} in_scope={result.in_scope} "
        f"scored={result.scored} out={result.out_dir}"
    )
    return 0


def cmd_next_stage(argv: list[str]) -> int:
    """Build next-stage evaluation markdown/JSON from a score-sessions out dir."""
    skills = skill_names()
    parser = argparse.ArgumentParser(
        prog="eval next-stage",
        description=(
            "Aggregate RunEvidence + EvaluationRecords into a next-stage "
            "skill evaluation brief (priorities + acceptance checks)."
        ),
    )
    parser.add_argument(
        "--runs-dir",
        required=True,
        help="Directory produced by score-sessions (contains evidence/ and evaluations/)",
    )
    parser.add_argument(
        "--skill",
        default=None,
        choices=skills,
        help="Skill brief to generate (default: read from runs-dir/manifest.json)",
    )
    parser.add_argument(
        "--out",
        default="docs/evaluations/issue-tracker-next-stage.md",
        help="Markdown report path (JSON written beside it)",
    )
    parser.add_argument("--baseline-version", default="0.2.0")
    parser.add_argument("--recommended-version", default="0.3.0")
    args = parser.parse_args(argv)

    runs_dir = Path(str(args.runs_dir))
    if not runs_dir.is_absolute():
        runs_dir = Path.cwd() / runs_dir
    out_md = Path(str(args.out))
    if not out_md.is_absolute():
        out_md = Path.cwd() / out_md

    try:
        brief = write_next_stage_report(
            runs_dir,
            out_md,
            skill=str(args.skill) if args.skill else None,
            baseline_version=str(args.baseline_version),
            recommended_version=str(args.recommended_version),
        )
    except (OSError, ValueError, FileNotFoundError) as e:
        print(f"FAIL: next-stage ({e})", file=sys.stderr)
        return 1

    print(
        f"PASS: next-stage skill={brief.skill} "
        f"baseline={brief.baseline_version} → {brief.recommended_version} "
        f"runs={brief.runs_analyzed} out={out_md}"
    )
    return 0


def cmd_density_probe(argv: list[str]) -> int:
    """CLM-score skill text + write cursor-agent density ablation bundle."""
    skills = skill_names()
    # Also allow skills that exist on disk but lack an eval task yet
    parser = argparse.ArgumentParser(
        prog="eval density-probe",
        description=(
            "Score skill markdown density (dense/clear vs padded slop) and prepare "
            "a cursor-agent --yolo line-ablation probe (only_*/drop_*/atoms_only)."
        ),
    )
    parser.add_argument("--skill", required=True, help="Skill directory name")
    parser.add_argument(
        "--prompt",
        required=True,
        help="Task prompt for cursor-agent variants (what the next agent should do)",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output dir (default: eval/.runs/density-<skill>-<id>/)",
    )
    parser.add_argument(
        "--no-score-text",
        action="store_true",
        help="Skip CLM skill-text scoring (plan + run.sh only)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run cursor-agent --yolo --print for selected variants (default: as_is, atoms_only)",
    )
    parser.add_argument(
        "--execute-variants",
        default=None,
        help="Comma-separated variant names to execute (requires --execute)",
    )
    parser.add_argument(
        "--agent-bin",
        default="cursor-agent",
        help="Agent binary (default: cursor-agent)",
    )
    args = parser.parse_args(argv)
    if args.skill not in skills:
        # soft warning — density probe only needs skills/<name>/SKILL.md
        print(
            f"note: {args.skill!r} not in eval task registry {skills}; "
            "continuing with skills/<name>/SKILL.md",
            file=sys.stderr,
        )

    out = Path(args.out) if args.out else None
    if out is not None and not out.is_absolute():
        out = Path.cwd() / out
    execute_variants = (
        [v.strip() for v in args.execute_variants.split(",") if v.strip()]
        if args.execute_variants
        else None
    )

    try:
        if args.no_score_text:
            result = prepare_density_probe(
                skill_name=str(args.skill),
                user_task=str(args.prompt),
                out_dir=out,
                score_text=False,
                execute=bool(args.execute),
                execute_variants=execute_variants,
                agent_bin=str(args.agent_bin),
            )
        else:
            with EvalRuntime() as runtime:
                client = _client(runtime)
                result = prepare_density_probe(
                    skill_name=str(args.skill),
                    user_task=str(args.prompt),
                    out_dir=out,
                    client=client,
                    score_text=True,
                    execute=bool(args.execute),
                    execute_variants=execute_variants,
                    agent_bin=str(args.agent_bin),
                )
    except (ValueError, RuntimeError, TimeoutError, OSError, FileNotFoundError) as e:
        print(f"FAIL: density-probe ({e})", file=sys.stderr)
        return 1

    scores = result.text_scores
    score_bit = ""
    if scores is not None:
        score_bit = (
            f" density={scores.skill_density:.3f} ({scores.skill_density_label}) "
            f"action_pointing={scores.action_pointing:.3f} "
            f"slop_risk={scores.slop_risk:.3f}"
        )
    print(
        f"PASS: density-probe skill={result.skill} atoms={result.atom_count} "
        f"variants={len(result.variants)} out={result.out_dir}{score_bit}"
    )
    print(f"  run: {result.run_script}")
    print(
        "  read: plan.json + atoms.json; compare logs/ after "
        "`bash run.sh` or --execute"
    )
    if result.executed:
        print(f"  executed: {', '.join(result.executed)}")
    return 0


def main() -> None:
    argv = sys.argv[1:]
    usage = (
        "usage: uv run eval run | uv run eval commit-msg <message|-> | "
        "uv run eval score-sessions [options] | uv run eval next-stage [options] | "
        "uv run eval density-probe [options]\n"
        "  run             hard smoke (invoice → billing)\n"
        "  commit-msg      hard gate: reject slop / weak commit messages (exit 1 on FAIL)\n"
        "  score-sessions  Pi sessions → evidence/evaluations "
        "(--sessions-dir or WIKISKILL_SESSIONS_DIR)\n"
        "  next-stage      aggregate scored runs → next skill-stage evaluation brief\n"
        "  density-probe   skill density vs slop + cursor-agent --yolo line ablation"
    )
    if not argv or argv[0] in {"-h", "--help"}:
        print(usage)
        raise SystemExit(0 if argv else 2)

    cmd = argv[0]
    if cmd == "run":
        raise SystemExit(cmd_run())

    if cmd == "commit-msg":
        rest = argv[1:]
        if not rest:
            print(usage, file=sys.stderr)
            raise SystemExit(2)
        message = sys.stdin.read() if rest[0] in {"-", "--"} else " ".join(rest)
        raise SystemExit(cmd_commit_msg(message))

    if cmd == "score-sessions":
        raise SystemExit(cmd_score_sessions(argv[1:]))

    if cmd == "next-stage":
        raise SystemExit(cmd_next_stage(argv[1:]))

    if cmd == "density-probe":
        raise SystemExit(cmd_density_probe(argv[1:]))

    print(f"unknown command: {cmd!r}\n{usage}", file=sys.stderr)
    raise SystemExit(2)


if __name__ == "__main__":
    main()
