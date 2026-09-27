---
name: to-spec
description: Publish one GitHub Issue spec via issue-tracker — chat draft only, no local mirrors.
disable-model-invocation: true
metadata:
  version: "0.5.0"
---

Resolve publication with issue-tracker. Never write issue mirrors under docs/design, *spec*.md, or .scratch.

If issue-tracker is missing, run npx skills add jborkowski/wikiskill --skill issue-tracker.

Explore the repo; confirm test seams once; stop with blocked on … when context is missing; else put gaps in Further Notes.

Fill Problem Statement, Solution, User Stories, Implementation Decisions, Testing Decisions, Out of Scope, and Further Notes in chat from references/spec-template.md; create via issue-tracker; apply ready-for-agent; name related-issue candidates or none-found; do not push, merge, or close unless the user asks.
