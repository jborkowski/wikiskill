# to-spec lessons (from Pi session eval)

Retrospective notes from scoring historical Pi agent sessions against
`to-spec` with the CLM skill-run rubric. Raw transcripts stay local.

## Corpus

- Source: Pi session JSONL via `WIKISKILL_SESSIONS_DIR` / `--sessions-dir` (not committed).
- Scanned 14 sessions; **6 in-scope** (to-spec skill load / path / invocation signals).

## Patterns observed

1. **Spec template almost never completed in-session** (`spec_sections` 0/6 on all 6 runs).
   Agents talked about specs or published tickets without emitting the six core headings.
2. **No seams checkpoint** (6/6). Seam discussion and explicit user confirmation before
   Implementation/Testing Decisions is missing.
3. **Publish label gaps.** One create run lacked a clear `ready-for-agent` signal in the
   excerpt; issue-tracker usage when publishing was otherwise usually present.
4. **CLM often failed / insufficient** while sometimes still ranking `skill_helped` mid —
   treat scores as experimental; behavioral gaps above are the actionable signal.

## Skill direction

- Hard **publish gate**: all six core sections present before `gh issue create`.
- Required **seams checkpoint** with user confirmation.
- Explicit **no-interview** + Further Notes for gaps.
- **issue-tracker only** for publish (install from `jborkowski/wikiskill` when missing).

See `docs/evaluations/to-spec-next-stage.md` for gap table and acceptance checks.
