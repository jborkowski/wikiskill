# skill-evolve artifacts

Conventions used by this pack. Paths are relative to the **wikiskill** repo root unless the user names another checkout.

## Naming

| Artifact | Pattern | Example |
| --- | --- | --- |
| Baseline next-stage | `docs/evaluations/<skill>-next-stage.{md,json}` | `to-spec-next-stage.md` |
| Post-patch retrospective | `docs/evaluations/<skill>-<baseline>-retrospective.{md,json}` | `to-spec-0.2.0-retrospective.md` |
| Lesson | `docs/lessons/<skill>/YYYY-MM-DD-<slug>.md` | `docs/lessons/to-spec/2026-09-25-template-and-seams.md` |
| Run dir | `eval/.runs/<skill>-v<ver>/` or `eval/.runs/<skill>-v<ver>-retrospective/` | `eval/.runs/to-spec-v0.2.0-retrospective/` |

`<skill>` matches the skill directory / frontmatter `name`.

## Brief header (Applied)

When a recommended version is shipped, prepend:

```markdown
> **Applied:** `skills/<skill>` bumped to `<ver>` from this brief (<one-line what changed>).
> Fresh-corpus acceptance checks below remain open until a new injected run.
```

Chain briefs: the retrospective that recommended `N+1` gets the Applied note when `N+1` lands; the earlier next-stage brief may cross-link that Applied.

## Lesson template

```markdown
# <skill> lessons (<short theme>)

Retrospective notes from scoring agent sessions against `<skill>`.
Raw transcripts stay local.

## Corpus

- Source: via `WIKISKILL_SESSIONS_DIR` / `--sessions-dir` (not committed).
- Scanned N sessions; **M in-scope**.
- Baseline skill version: `x.y.z`. Brief: `docs/evaluations/…`.

## Facts observed

1. **…** (gap or count; cite run ids / gap keys).

## Judgments

- …

## Skill direction

- Atomic change to try: …
```

## Fact vs judgment (quick test)

- If you can point at a field in `observed_outcome`, a gap count, or a tool command in evidence → **fact**.
- If two reviewers could disagree without new data → **judgment**.

## Eval commands (copy/paste)

```bash
export WIKISKILL_SESSIONS_DIR="$HOME/.pi/agent/sessions/<project-key>/"

uv run eval score-sessions --skill <name> --out eval/.runs/<label>
uv run eval next-stage --runs-dir eval/.runs/<label> \
  --out docs/evaluations/<skill>-next-stage.md \
  --baseline-version <b> --recommended-version <n>
```

Supported `--skill` values are whatever `wikiskill_eval` registers (see `eval/README.md` / `score_sessions.py`). Extending the loop to a new skill usually means adding `eval/src/wikiskill_eval/tasks/<skill>.py` first.
