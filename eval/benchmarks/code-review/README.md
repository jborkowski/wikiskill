# Code-review pilot benchmark

Compare the initial skill, the supplied two-axis proposal, and a hybrid candidate on four isolated Git repositories. This is a small synthetic pilot, not a claim of an optimal prompt or production-level recall.

## Reproduce

1. `uv run python eval/benchmarks/code-review/test_fixtures.py` validates seeded behavior.
2. `uv run python eval/benchmarks/code-review/build_fixtures.py` prints a temporary root containing Git repos, `manifest.json` and `truth.json`.
3. With user-authorized delegation, run `compare.js` through pi-subagents as described in its opening comment; supply checkout and fixture root as args. Use fresh contexts, the same model for all five lanes, and preserve runtime artifacts.
4. Only after reviewers complete, read `truth.json` and manually annotate obligation coverage. A finding can cover multiple obligations. Count each obligation once, including overlapping axes. Count unsupported findings and optional smells separately. Do not use string matching as a correctness judge.
5. Read elapsed time and usage from workflow/session artifacts. For a two-axis variant, report maximum axis time (parallel critical path) and summed usage/cost. These exclude parent setup/aggregation and are not end-to-end latency.

Ground truth has seven seeded obligations: authorization, amount bounds, invalid-amount exception, customer disclosure, positional compatibility, validation order, and arithmetic mean. The clean case expects no findings; documented currency/branch preferences override smell heuristics. Tests verify fixture behavior, not model quality.

## Pilot result

| Variant | Obligations detected | Unsupported findings | Clean-case findings | Review critical path | Reported child cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| Initial `0.1.0` | 7/7 | 0 | 0 | 94.349 s | $0.055434 |
| Supplied two-axis proposal | 6/7 | 0 | 0 | 93.789 s | $0.0994484 |
| Hybrid candidate | 7/7 | 0 | 0 | 86.768 s | $0.101112 |

One run per variant; four cases batched per lane. Same native `delegate` role, fresh context, `openai-codex/gpt-6.1-sol` model for all five lanes. Parent manually scored against the withheld seeded obligations. Hybrid detected seven obligations in six behavior findings plus three overlapping standards findings; finding counts are not recall denominators. All variants reported zero optional smells. Supplied Spec review also discussed smells, a minor axis-boundary deviation despite separate contexts.

The supplied approach intentionally skipped Spec when no spec existed; Standards did not detect the arithmetic regression. That is a scope limitation, not noncompliance with its prompt. Hybrid continued behavior review and found it. No detection gain over the baseline was established. Separate reporting offers requirement coverage and prevents axes from masking one another, at roughly 1.8× reported child cost in this run. Runtime differences are noisy and not evidence of a speed improvement.

## Tuning decision and limits

Ship `0.2.0` using separate Standards and Spec & Behavior axes, retaining correctness review without a spec, explicit-spec precedence, immutable refs, evidence thresholds, repo-overridden optional smells, and cross-referenced duplicates. Do not globally rerank axes or infer scope creep from unspecified implementation detail. Support disclosed sequential passes when parallel delegation is unavailable/unauthorized.

`variants/` preserves the exact procedure packets used by this pilot. The supplied packet is a condensed transcription, not a byte-for-byte copy; tracker discovery and fanout were controlled by the harness. The installed `0.2.0` expands the tested hybrid packet; its full orchestration was not separately benchmarked. This pilot did not measure real PRs, multilingual repos, smell-positive cases, invalid refs, moving refs, unrelated histories, tracker lookup, parent aggregation accuracy, or repeated-run/model variance. The fixtures are deliberately simple and selected by the author. Next: held-out real diffs, positive/negative smell controls, scope-resolution tests and repeated runs before stronger claims.

Runtime receipt: `c4ed9510-70bd-4eb8-9d68-43be9769924f`. Raw reviewer outputs remain in retention-managed session artifacts, not committed transcripts. Re-run the harness to regenerate evidence; no absolute home/session paths are persisted here.
