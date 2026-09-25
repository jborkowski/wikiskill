# Issue-tracker lessons (from Pi session eval)

Retrospective notes from scoring historical Pi agent sessions against
`issue-tracker@0.1.0` with the CLM skill-run rubric. Raw transcripts stay local;
only patterns are recorded here.

## Corpus

- Source: Pi session JSONL passed via `WIKISKILL_SESSIONS_DIR` / `--sessions-dir`
  (not committed).
- Scanned 14 sessions; 7 in-scope (skill load and/or `gh issue` / dependency usage).

## Patterns observed

1. **Almost no `gh search`.** Agents rely on `gh issue list` / `gh issue view` when
   they look at all. Keyword / cross-repo search for duplicates is missing.
2. **Create without a prior related-issue pass.** Several runs call `gh issue create`
   (or prepare creates) without a dedicated duplicate/related scan for the proposed
   title/topic first.
3. **List is used, but not as a gate.** When `gh issue list` appears, it is often for
   wayfinding or parenting, not an explicit “candidates considered, none duplicate”
   step before publish.
4. **Skill helps tooling more than judgment.** CLM often ranked `skill_helped` high
   even when `outcome` was `failed` / sparse — the skill documents `gh` mechanics
   well, but under-specifies discovery discipline.
5. **Evidence quality varies.** Long sessions truncated to gh-centric excerpts still
   leave gaps; treat CLM scores as experimental signals, not calibrated truth.

## Stratified sample (qualitative)

- Failures / gaps: sessions that created or migrated tracker content without search;
  skill-authoring sessions where tracker writes were secondary.
- Partial success: sessions that listed/viewed issues and created children with
  labels/dependencies, but still no systematic related-issue check.

## Proposed skill change

Add an explicit **Related-issue discovery** procedure before create/claim:

- `gh issue list` (open) plus `gh search issues` (or title-keyword query) in the
  current repo.
- Record candidate related/duplicate numbers in the draft or comment.
- Only then `gh issue create` when publication is authorized.

Ship as `issue-tracker@0.2.0`. Re-score the same historical evidence retrospectively
(same transcripts; new `SkillRef.version` only) until fresh agent runs with the
patched skill are available.

## Retrospective re-score (`0.2.0`)

Re-ran CLM on the same 7 sessions with `SkillRef.version=0.2.0` and a slightly
stronger task frame. Outcomes shifted noisily (expected: skill body is not in the
historical transcript). Treat this as a baseline label, not proof that `0.2.0`
improved live agent behavior — collect new runs with the patched skill injected
for a real comparison.
