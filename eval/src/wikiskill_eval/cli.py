"""Program entry: ``uv run eval <command>``.

Commands:
  run          — smoke: invoice System One (department=billing)
  commit-msg   — hard gate: CLM judges commit message (reject slop / weak density)
"""

from __future__ import annotations

import sys

from wikiskill_eval import EvalClient, EvalConfig
from wikiskill_eval.commit_msg import evaluate_commit_msg, verify_commit_msg
from wikiskill_eval.runtime import EvalRuntime


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


def main() -> None:
    argv = sys.argv[1:]
    usage = (
        "usage: uv run eval run | uv run eval commit-msg <message|->\n"
        "  run         hard smoke (invoice → billing)\n"
        "  commit-msg  hard gate: reject slop / weak commit messages (exit 1 on FAIL)"
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

    print(f"unknown command: {cmd!r}\n{usage}", file=sys.stderr)
    raise SystemExit(2)


if __name__ == "__main__":
    main()
