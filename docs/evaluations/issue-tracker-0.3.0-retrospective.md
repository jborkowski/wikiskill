# Next-stage evaluation: `issue-tracker`

Baseline scored version: `0.3.0`. Recommended next version: `0.4.0`.

Runs analyzed: **7** (evidence + CLM evaluations).

## Behavioral gap counts

| Gap | Count |
| --- | ---: |
| `zero_search` | 7 |
| `create_without_related_gate` | 0 |
| `create_without_remote_check` | 0 |
| `create_without_label_signal` | 0 |
| `multi_create_without_deps` | 0 |
| `clm_failed_or_insufficient` | 5 |
| `clm_helped_but_failed` | 2 |

## Per-run signals

| run | outcome | helped | evid | creates | lists | views | searches | labels | deps | remote | related_gate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `01a0d772` | failed | 0.862 | 1.01 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | n/a-no-create |
| `01a0d77f` | partially_succeeded | 0.687 | 1.02 | 2 | 2 | 1 | 0 | 2 | 1 | 1 | yes |
| `01a0d7ad` | failed | 0.048 | 2.07 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | n/a-no-create |
| `01a0d826` | insufficient_evidence | 0.070 | 2.84 | 2 | 2 | 2 | 0 | 2 | 1 | 1 | yes |
| `01a0d852` | insufficient_evidence | 0.462 | 2.90 | 2 | 1 | 2 | 0 | 2 | 3 | 1 | yes |
| `01a0d87a` | failed | 0.869 | 1.00 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a-no-create |
| `01a0d87c` | succeeded | 0.053 | 2.17 | 0 | 1 | 5 | 0 | 0 | 0 | 0 | n/a-no-create |

## Priorities for next skill stage

1. Working-on-issue related discovery: when already on #N, search/list for blockers, duplicates, and parallel work before editing or spawning children.
2. Hard gate before publish: refuse gh issue create until related_gate=yes (list and/or search) and candidates are named in the draft body.
3. Remote confirmation: require git remote -v (or equivalent) before any write.
4. Triage label checklist: map every create/edit to triage-labels.md roles and record the applied label in the run summary.
5. Dependency pairing: when creating 2+ related tickets, set blocked_by edges (or explicit Blocked by lines) in the same operation.

## Acceptance checks for the next stage

- [ ] On a fresh agent corpus with issue-tracker@0.4.0 injected, searches+lists > 0 on every create run.
- [ ] related_gate_before_create=yes for 100% of create runs.
- [ ] remote_checks >= 1 on every write run.
- [ ] CLM outcome succeeded|partially_succeeded share rises vs 0.3.0 baseline on matched tasks.
- [ ] Human spot-check: drafts name candidate related issues before publish.
