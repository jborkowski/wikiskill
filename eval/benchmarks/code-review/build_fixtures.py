"""Build isolated, deterministic Git repositories for code-review comparisons."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

CASES = [
    {
        "name": "spec-and-standards",
        "standards": "# Standards\nS1: Reject invalid amounts by raising ValueError; do not return sentinel values.\nS2: Application code must not print customer identifiers.\n",
        "spec": "# Refund spec\nR1: Only the order owner may refund an order; reject others with PermissionError.\nR2: Refund amounts must be positive and at most the order total.\nR3: Successful refunds return the amount and emit no customer identifiers.\n",
        "before": "def refund(order, actor_id, amount):\n    raise NotImplementedError\n",
        "after": "def refund(order, actor_id, amount):\n    if amount < 0:\n        return None\n    print(order['customer_id'])\n    return amount\n",
        "truth": [
            "missing owner authorization",
            "zero and over-total amounts accepted",
            "invalid amount returns sentinel",
            "customer identifier printed",
        ],
    },
    {
        "name": "clean-with-overrides",
        "standards": "# Standards\nS1: Use string currency codes at API boundaries; do not introduce currency wrapper types.\nS2: Two explicit currency branches are preferred to polymorphism here.\nS3: Formatting is enforced by tooling; omit formatting review comments.\n",
        "spec": "# Conversion spec\nR1: Support USD and EUR with factors 1 and 2 respectively.\nR2: Reject other currencies with ValueError.\nR3: Zero is a valid amount.\n",
        "before": "def convert(amount, currency):\n    raise NotImplementedError\n",
        "after": "def convert(amount, currency):\n    if currency == 'USD':\n        return amount\n    if currency == 'EUR':\n        return amount * 2\n    raise ValueError('unsupported currency')\n",
        "truth": [],
    },
    {
        "name": "context-and-scope",
        "standards": "# Standards\nS1: Validate configuration before opening external connections.\n",
        "spec": "# Client spec\nR1: Add an optional timeout argument, default 30 seconds.\nR2: Preserve existing callers that pass endpoint then token positionally.\nR3: Reject non-positive timeouts before opening a connection.\n",
        "before": "def connect(endpoint, token):\n    return open_connection(endpoint, token)\n\ndef open_connection(endpoint, token):\n    return {'endpoint': endpoint, 'token': token}\n",
        "after": "def connect(endpoint, timeout=30, token=None):\n    connection = open_connection(endpoint, token)\n    if timeout <= 0:\n        raise ValueError('timeout must be positive')\n    return connection\n\ndef open_connection(endpoint, token):\n    return {'endpoint': endpoint, 'token': token}\n",
        "caller": "from app import connect\n\ndef existing_client():\n    return connect('https://example.invalid', 'secret-token')\n",
        "truth": ["positional compatibility broken", "connection opened before timeout validation"],
    },
    {
        "name": "no-spec-correctness",
        "standards": "# Standards\nS1: No additional documented conventions.\n",
        "spec": None,
        "before": "def average(values):\n    return sum(values) / len(values)\n",
        "after": "def average(values):\n    count = len(values)\n    return sum(values) / (count - 1)\n",
        "truth": ["wrong average denominator including division by zero for singleton"],
    },
]


def git(root: Path, *args: str) -> str:
    # Fixed Git operations and local fixture data only; no shell or user commands.
    return subprocess.check_output(  # noqa: S603
        ["git", "-C", str(root), *args],  # noqa: S607
        text=True,
    ).strip()


def main() -> None:
    root = Path(tempfile.mkdtemp(prefix="code-review-benchmark-"))
    manifest = []
    truth = {}
    for case in CASES:
        repo = root / case["name"]
        repo.mkdir()
        git(repo, "init", "-q")
        git(repo, "config", "user.name", "Benchmark")
        git(repo, "config", "user.email", "benchmark@example.invalid")
        (repo / "CODING_STANDARDS.md").write_text(case["standards"])
        if case["spec"] is not None:
            (repo / "SPEC.md").write_text(case["spec"])
        (repo / "app.py").write_text(case["before"])
        if "caller" in case:
            (repo / "caller.py").write_text(case["caller"])
        git(repo, "add", ".")
        git(repo, "commit", "-qm", "Initial baseline")
        base = git(repo, "rev-parse", "HEAD")
        (repo / "app.py").write_text(case["after"])
        git(repo, "add", ".")
        git(repo, "commit", "-qm", "Implement requested behavior")
        manifest.append(
            {
                "name": case["name"],
                "repo": str(repo),
                "base": base,
                "head": git(repo, "rev-parse", "HEAD"),
                "spec": "SPEC.md" if case["spec"] else None,
            }
        )
        truth[case["name"]] = case["truth"]
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (root / "truth.json").write_text(json.dumps(truth, indent=2) + "\n")
    print(root)  # noqa: T201 — CLI output is the fixture manifest location


if __name__ == "__main__":
    main()
