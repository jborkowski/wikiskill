---
name: issue-tracker
description: "Use any repo's GitHub Issues safely: read issues, draft or publish tickets, apply that repo's triage labels, find related issues while working, and set blocking dependencies. Configure labels per install."
metadata:
  version: "0.4.0"
---

# Issue Tracker

Skill version: `0.4.0`

Generic skill for **any** Git repository that tracks work in **GitHub Issues** via the `gh` CLI. It does not assume a particular product, org, or label vocabulary.

## Per-repo configuration (do this once after install)

1. Edit **`triage-labels.md`** in this skill directory (or your project's installed copy): set the **Repo label** column to match labels that already exist (or that you will create) on the GitHub repo.
2. Optionally set **PRs as a request surface** in `issue-tracker-github.md` to `yes` if external PRs are triaged like issues.
3. Domain docs paths in `domain.md` are **conventions**, not requirements — if files are missing, proceed silently.

Do not hard-code another project's label names in procedures. Always resolve **role → repo label** through `triage-labels.md`.

## Bootstrap

Before first write in a repo:

1. Confirm you are in the intended clone (`pwd`, `git remote -v`).
2. Confirm Issues work: `gh issue list --limit 1` (or `gh repo view`). If Issues are disabled or `gh` cannot see the repo, stop and tell the user — this skill only supports GitHub Issues.

## Reference files

- `issue-tracker-github.md` — `gh` commands, optional PR triage.
- `triage-labels.md` — canonical **roles** ↔ this repo's **label strings**.
- `domain.md` — optional domain-doc discovery (`CONTEXT.md`, ADRs); skip quietly if absent.

## Remote confirmation (before any write)

Before creating, editing, labeling, commenting, closing, or linking issues:

1. Run `git remote -v` (or otherwise confirm the `gh` target repo).
2. If the remote is ambiguous or unexpected, stop and ask — do not write.

Reads (`gh issue view` / `list` / `search`) may proceed without this only when the user already fixed the repo context in the prompt.

## Read

- Read an issue and its discussion with `gh issue view <number> --comments`.
- A bare `#<number>` can identify either an issue or pull request; check the intended surface before acting.
- Read labels as needed with `gh issue view <number> --json labels`.

## Related-issue discovery

Before creating a new issue, claiming a ticket, or breaking work into child tickets:

1. Confirm the remote (see above) when any write may follow.
2. List open issues: `gh issue list --state open --limit 50` (add `--label` filters when relevant).
3. **Search** by keywords from the proposed title/topic (required unless the tracker has fewer than ~10 open issues and list already covers them):
   `gh search issues --repo <owner>/<repo> "<keywords>" --state open`
   Resolve `<owner>/<repo>` from `git remote -v` / `gh repo view --json nameWithOwner -q .nameWithOwner`.
4. Record candidates (numbers + one-line why related / duplicate / blocker) in the draft body **or** in your reply. Prefer linking or extending an existing issue over creating a duplicate.
5. Only after that pass, proceed to draft or (when authorized) publish.

**Hard publish gate:** do not run `gh issue create` until steps 2–4 are done and at least one of: named candidates, or an explicit “no related open issues found” statement with the list/search commands you ran.

## While working on an issue

When the session is already about `#N` (implementation, review, or breakdown):

1. `gh issue view N --comments` and read current labels.
2. Run **Related-issue discovery** for the *theme of the change* (not only the title of `#N`) so blockers, duplicates, and parallel work surface early.
3. If you find blockers or overlaps, report them before editing code or spawning children. Link with native dependencies or `Blocked by:` / `Related:` lines as appropriate.
4. Skip only when the user forbids tracker exploration or restricts you to a single issue with no children.

## Triage labels (roles, not hard-coded strings)

Speak in **roles**; apply the **Repo label** from `triage-labels.md`:

| Situation | Role (look up Repo label) |
| --- | --- |
| Fully specified AFK / agent work | `ready-for-agent` |
| Needs maintainer judgment | `needs-triage` |
| Waiting on reporter | `needs-info` |
| Needs a human implementer | `ready-for-human` |
| Will not action | `wontfix` |

If the Repo label for a role is empty or the label does not exist on the remote, say so and ask whether to create the label or use an existing substitute — do not invent another ecosystem's vocabulary.

State the **repo label string** you applied (or would apply on draft) in the summary to the user.

## Write authorization

- This skill describes the tracker; it does not grant permission to write.
- “Draft”, “prepare”, or “break down” means return text only. Do not create or modify issues, comments, labels, or relationships.
- Create or publish issues only when the user explicitly asks for publication. If that intent is materially unclear, ask one focused question before writing.
- Keep writes within the requested scope. Never edit or close a source/parent issue unless separately authorized.

## Create child tickets

When publication is authorized:

1. Pass the **hard publish gate** (Related-issue discovery + named candidates or explicit none-found).
2. Resolve the triage **Repo label** for the intended role (default role: `ready-for-agent` when fully specified). Create with:
   `gh issue create --title "..." --body "..." --label "<repo-label>"` (heredoc body).
3. Include `Parent: #<source>` in each new issue body when breaking down a parent. Do not attach GitHub sub-issue relationships to the source unless the user authorizes changing it.
4. When creating **two or more** related tickets in one operation, set blocking edges in the same operation:
   `gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-database-id>`
   Use the blocker’s numeric database `id` (`gh api repos/<owner>/<repo>/issues/<n> --jq .id`), not the `#number`. If native dependencies are unavailable, put `Blocked by: #<number>` at the top of the dependent body.
5. Do not create duplicate issues on retry: re-list issues created in this operation before repeating a failed create.

## Changelog

- `0.4.0` — Generic per-repo config: role→label resolution, bootstrap, no hard-coded foreign vocab.
- `0.3.0` — Remote confirmation; hard publish gate; while-working discovery; triage checklist; multi-create dependency pairing.
- `0.2.0` — Related-issue discovery required before create/claim.
- `0.1.0` — Initial portable issue-tracker skill.
