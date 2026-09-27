---
name: to-tickets
description: Break a plan into tracer-bullet tickets with blockers and publish via issue-tracker. Local files only if asked.
disable-model-invocation: true
metadata:
  version: "0.3.0"
---

Use issue-tracker for remote confirm, related-issue gate, write auth, and role to Repo label. If missing, install with npx skills add jborkowski/wikiskill --skill issue-tracker.

Fetch any issue or URL argument with gh issue view n --comments. Explore the repo when needed.

Split work into tracer-bullet vertical slices that are demoable alone and fit one fresh context. Give each ticket Blocked by edges. For wide refactors use expand, then migrate batches, then contract.

Quiz the user with Title, Blocked by, and What it delivers using references/ticket-templates.md. Iterate until they approve.

Publish approved tickets as GitHub Issues via issue-tracker in blocker-first order with the hard publish gate, blocked_by or Blocked by lines, and ready-for-agent. Preview in chat. Stop if Issues or gh are unavailable. Write .scratch issues files only when the user explicitly asks. Do not edit or close a parent issue unless separately authorized.
