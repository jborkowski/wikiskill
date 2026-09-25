"""Evaluation pipeline: evidence in → persisted EvaluationRecord out.

Grow batching, storage, and version comparison here — not in shell wrappers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from wikiskill_eval.client import EvalClient

if TYPE_CHECKING:
    from wikiskill_eval.client import EvalConfig
    from wikiskill_eval.types import EvaluationRecord, RunEvidence


class Evaluator:
    """Owns CLM contact + rubric application for skill-run evaluation."""

    def __init__(self, config: EvalConfig | None = None, client: EvalClient | None = None) -> None:
        if client is not None and config is not None:
            raise ValueError("pass config or client, not both")
        self._client = client or EvalClient(config)

    @property
    def client(self) -> EvalClient:
        return self._client

    def healthy(self) -> bool:
        return self._client.health()

    def evaluate(self, evidence: RunEvidence) -> EvaluationRecord:
        """Score one run; returns a record ready to persist."""
        return self._client.evaluate_run(evidence)

    def evaluate_many(self, evidence: list[RunEvidence]) -> list[EvaluationRecord]:
        """Sequential batch; replace with concurrency / queue later if needed."""
        return [self.evaluate(item) for item in evidence]


def evaluate_one(evidence: RunEvidence, client: EvalClient | None = None) -> EvaluationRecord:
    """Convenience for a single evaluation."""
    return Evaluator(client=client).evaluate(evidence)
