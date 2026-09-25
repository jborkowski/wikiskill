---
name: skill-evolve
description: "Evaluate a skill from agent session transcripts, write next-stage/retrospective briefs, distill reusable facts into lessons, patch the skill, and dogfood the change — the WikiSkill loop for this pack."
disable-model-invocation: true
metadata:
  version: "0.1.0"
---

# Skill Evolve

Skill version: `0.1.0`

Run the **evaluate → distill → patch → dogfood → re-score** loop for any skill in this pack (including this one). Keep **traces**, **lessons**, and **skill versions** separate: transcripts stay local/immutable evidence; lessons hold distilled facts; skills hold the active procedure.

## When to use

- User asks to evaluate a skill, score sessions, write a retrospective / next-stage brief, or improve a skill from runs.
- After shipping a skill change and wanting evidence it helped.
- Dogfooding: “try the skill itself” on a real task, then fold findings back.

## Dependencies

- **Eval CLI** in this repo (`uv run eval …`) — see `eval/README.md`.
- Target skill under `skills/<name>/` (or an installed copy the user names).
- Optional sibling **`issue-tracker`** only if you publish tickets about the evolution work.

Never commit raw transcripts or absolute home session paths. Pass the corpus at runtime:

`WIKISKILL_SESSIONS_DIR` or `--sessions-dir`.

## Artifacts (do not invent new trees)

| Kind | Path | Commit? |
| --- | --- | --- |
| Scored runs | `eval/.runs/<label>/` (`evidence/`, `evaluations/`, `manifest.json`) | No (gitignored) |
| Next-stage / retrospective brief | `docs/evaluations/<skill>-….md` (+ `.json` beside it) | Yes |
| Distilled lessons | `docs/lessons/<skill>/YYYY-MM-DD-<slug>.md` | Yes |
| Active skill | `skills/<skill>/SKILL.md` (+ siblings) | Yes |

Templates and naming rules: `references/artifacts.md`.

## Process

### 1. Pin the evaluation

Record before scoring:

1. **Skill name** and **baseline version** (from `metadata.version` / changelog).
2. **Recommended next version** (semver bump you intend if the brief’s priorities land).
3. **Corpus**: sessions dir (env/flag only), harness (Pi / other), date.
4. **Out dir** under `eval/.runs/` (e.g. `eval/.runs/to-spec-v0.2.0`).

If the skill has no eval task module yet, say so; run evidence collection only for supported skills (`issue-tracker`, `to-spec`, …) or extend `wikiskill_eval.tasks` first.

### 2. Score sessions

```bash
uv run eval score-sessions --skill <name> --out eval/.runs/<label> [--sessions-dir …]
# offline signals without CLM:
uv run eval score-sessions --skill <name> --out eval/.runs/<label> --evidence-only
```

Read `manifest.json` (counts, run ids — no session path). Spot-check a **stratified sample**: prefer failures / gap-heavy runs, plus a few successes (cap ~8 runs for deep read, WikiSkill-style).

### 3. Next-stage brief (and retrospectives)

```bash
uv run eval next-stage --runs-dir eval/.runs/<label> \
  --out docs/evaluations/<skill>-next-stage.md \
  --baseline-version <baseline> --recommended-version <next>
```

After a skill patch, re-score (often retrospective on the same corpus with the new `SkillRef` version label) and write a **retrospective** brief:

`docs/evaluations/<skill>-<baseline>-retrospective.md`

with `--baseline-version` = the version just applied, `--recommended-version` = the following candidate.

**Finding existing retrospectives:** search `docs/evaluations/` and `docs/lessons/<skill>/` before inventing parallel notes. Prefer updating **Applied** notes on the brief that recommended a bump over rewriting history.

### 4. Distill knowledge (facts first)

Write or extend `docs/lessons/<skill>/YYYY-MM-DD-<slug>.md`.

Separate sharply:

| Layer | Allowed content |
| --- | --- |
| **Facts** | Countable / citable: command presence, section hits, gate yes/no, run ids, gap table numbers |
| **Judgments** | “skill under-specified X”, “CLM noisy here” — label as judgment |
| **Skill direction** | Concrete procedure changes to try next (atomic) |

Rules:

1. Prefer **behavioral gaps** from next-stage tables over CLM alone. CLM `outcome` / `skill_helped` are experimental signals.
2. Every pattern cites **evidence** (run id prefix and/or gap key + count).
3. Do not paste transcript bodies into git; quote short tool/command snippets only when needed.
4. One lesson file = one theme (or one eval pass). Link the brief path.

### 5. Propose one atomic skill patch

Read the lesson + brief priorities. Change **one** coherent concern in `skills/<skill>/` (procedure, gate, wording). Bump `metadata.version` and changelog.

Add an **Applied** note atop the brief that recommended this version (what changed; that fresh-corpus acceptance may still be open).

Do **not** mark acceptance checkboxes `[x]` unless a **fresh** corpus with the new version **injected** actually meets them. Retrospective re-labels alone are not acceptance.

### 6. Dogfood — try itself

Required before calling the loop done:

1. **Invoke the patched skill** on a real user task in this session (or a clearly scoped dry-run the user authorizes) — not only re-read the markdown.
2. Note where the skill helped, blocked, or was ambiguous (facts: which steps you followed / skipped).
3. If dogfooding **`skill-evolve` itself**, use this same process on another skill or on a prior brief — the procedure under test is this file.

Optional: open a small ticket via `issue-tracker` for follow-ups; otherwise keep findings in the lesson.

### 7. Re-score and close the loop

1. Score again (retrospective and/or fresh sessions).
2. Emit retrospective brief; compare gap counts to baseline.
3. Update lesson with delta (facts).
4. If gaps worsened or dogfood failed, **rollback** the skill text (or ship a fix version) and keep the lesson — wiki retained, skill reverted (WikiSkill separation).

## Output checklist (every run of this skill)

- [ ] Pinned skill / versions / out dir stated to the user
- [ ] Score or reuse existing `eval/.runs/…` (no committed session paths)
- [ ] Brief under `docs/evaluations/` (next-stage and/or retrospective)
- [ ] Lesson under `docs/lessons/<skill>/` with facts vs judgments
- [ ] At most one atomic skill patch + version bump + Applied note (or explicit “no patch”)
- [ ] Dogfood attempt recorded (what was tried)
- [ ] Acceptance boxes only if fresh injected corpus warrants it

## Anti-patterns

- Treating CLM scores as calibrated truth or as acceptance by themselves
- Committing Pi/Cursor transcripts or `WIKISKILL_SESSIONS_DIR` absolute paths
- Silent version jumps without Applied notes on the recommending brief
- Scope-creeping multiple unrelated skill edits in one “evolution”
- Claiming dogfood when you only edited markdown
- Inventing wayfinder / third-party skill setups — stay in this pack (`jborkowski/wikiskill`)

## Changelog

- `0.1.0` — Initial loop: score → brief → distill → patch → dogfood → re-score; artifact paths for this repo.
