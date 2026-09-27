---
name: skill-evolve
description: Score skill runs, write briefs and lessons, patch one concern, dogfood, re-score.
disable-model-invocation: true
metadata:
  version: "0.3.0"
---

Resolve the corpus with WIKISKILL_SESSIONS_DIR or --sessions-dir. Never commit transcripts.

If eval CLI is missing, run uv sync from the repository root.

Run uv run eval score-sessions --skill name --out eval/.runs/label. Spot-check failures.

Run uv run eval next-stage into docs/evaluations; write lessons under docs/lessons/skill; patch one concern in skills/name/SKILL.md; bump metadata.version; add Applied; dogfood; re-score; rollback if worse.
