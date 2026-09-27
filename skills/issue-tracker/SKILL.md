---
name: issue-tracker
description: Safe GitHub Issues read/write via gh — labels, related-issue discovery, blockers. Specs stay on GitHub.
metadata:
  version: "0.6.0"
---

Map triage roles through triage-labels.md. Confirm with pwd, git remote -v, and gh issue list --limit 1; stop if Issues or gh fail.

Search open issues by keywords before create or claim. Put candidates or none-found in the body.

Keep drafts in chat. Specs stay on GitHub Issues, not docs/design, *spec*.md, or .scratch.

Create with ready-for-agent, Parent: #source on children, and blocked_by or Blocked by: #n. Re-list before retry.
