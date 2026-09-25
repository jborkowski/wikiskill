# Next-stage evaluation: `to-spec`

> **Applied:** `skills/to-spec` bumped to `0.3.0` from this brief (fully generic: role→label via
> issue-tracker; no project-specific setup commands or paths). Fresh-corpus acceptance checks
> below remain open until a new injected run. Lessons: `docs/lessons/to-spec/`.

Baseline scored version: `0.2.0`. Recommended next version: `0.3.0`.

Runs analyzed: **6** (evidence + CLM evaluations).

## Behavioral gap counts

| Gap | Count |
| --- | ---: |
| `incomplete_spec_sections` | 6 |
| `interviewed_user` | 1 |
| `no_seams_check` | 6 |
| `publish_without_issue_tracker` | 0 |
| `publish_without_ready_label` | 1 |
| `clm_failed_or_insufficient` | 5 |
| `clm_helped_but_failed` | 1 |

## Per-run signals

| run | outcome | helped | evid | sections | interviewed | seams | issue_tracker | creates | ready_label |
| --- | --- | ---: | ---: | ---: | --- | --- | --- | ---: | --- |
| `01a0d772` | failed | 0.762 | 1.01 | 0/6 | false | false | true | 0 | true |
| `01a0d77f` | partially_succeeded | 0.764 | 1.01 | 0/6 | true | false | true | 2 | true |
| `01a0d7a9` | insufficient_evidence | 0.437 | 1.90 | 0/6 | false | false | false | 0 | false |
| `01a0d7ad` | failed | 0.170 | 2.86 | 0/6 | false | false | true | 0 | false |
| `01a0d852` | insufficient_evidence | 0.605 | 2.43 | 0/6 | false | false | true | 2 | false |
| `01a0d87c` | failed | 0.137 | 1.33 | 0/6 | false | false | true | 0 | true |

## Priorities for next skill stage

1. Mandate full template coverage before publish (all six core sections present).
2. Keep no-interview rule explicit; if context is insufficient, say what is missing in Further Notes instead of grilling.
3. Require a short seams proposal + user confirmation checkpoint before drafting Implementation/Testing Decisions.
4. Always load/follow sibling issue-tracker for publish (authz, related-issue gate, ready-for-agent); install from jborkowski/wikiskill if missing.
5. When publishing, include ready-for-agent and name related-issue candidates in the issue body per issue-tracker hard publish gate.

## Acceptance checks for the next stage

- [ ] Fresh corpus with to-spec@0.3.0: spec_sections == 6/6 on every successful publish run.
- [ ] interviewed=false on >= 90% of in-scope runs.
- [ ] seams_checked=true before publish on every create run.
- [ ] used_issue_tracker=true whenever published_creates > 0.
- [ ] CLM succeeded|partially_succeeded share rises vs 0.2.0 on matched tasks.
