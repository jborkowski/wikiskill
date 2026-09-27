---
name: implement
description: Implement one GitHub Issue at a time — tests, review, gates, commit. Never mirror tickets to disk.
disable-model-invocation: true
metadata:
  version: "0.3.0"
---

Resolve the ticket with gh issue view via issue-tracker. Never write issue mirrors under .scratch, docs/design, or issue-*.md.

If issue-tracker is missing, run npx skills add jborkowski/wikiskill --skill issue-tracker.

Do one ticket at a time. Finish implement, test, review, fix, and commit on N before N+1.

Confirm OPEN with blockers done; obey acceptance criteria; prefer TDD; run the repo’s real checks; review the diff; fix the same slice or stop with repro; commit mentioning #n. Do not push, merge, or close unless the user asks.
