---
name: implement
description: "Implement one ticket or approved slice from GitHub Issues (or the conversation): one-at-a-time loop of implement → tests → review → gates → fix → commit. Prefer TDD; never mirror tickets into local design/scratch files."
disable-model-invocation: true
metadata:
  version: "0.2.0"
---

# Implement

Skill version: `0.2.0`

Implement the work described by a **spec** and/or **tickets** for **whatever repository you are in**. Do not assume a hard-coded project path.

## Context sources (GitHub first)

Resolve the work from, in order:

1. Explicit ticket / issue numbers or URLs — fetch live with sibling **`issue-tracker`**: `gh issue view <n> --comments` (and parent issue when the ticket names one). **GitHub is the source of truth.**
2. A spec already published as a GitHub issue (from **`to-spec`**) — fetch the same way.
3. Otherwise, the description already in the conversation.

Do **not**:

- Dump issue/spec bodies into the working tree (`.scratch/**`, `docs/design/**`, `issue-*.md` mirrors, etc.) to “prepare” for implement or for a weaker model
- Prefer stale local copies over `gh issue view`
- Use `.scratch/**/issues/` as the ticket source unless the user **explicitly** points at those files

If `issue-tracker` is needed and missing:

`npx skills add jborkowski/wikiskill --skill issue-tracker`

## One ticket at a time

When the user gives a **list** of tickets:

1. Order by blockers (frontier first; respect `Blocked by` / native dependencies).
2. Run the **full loop below on ticket N** until done (or blocked with a clear report).
3. Only then start ticket N+1.
4. Never keep two implement slices in flight unless the user explicitly asks for parallelism.

If asked only to **prepare a subagent/workflow**, still encode this one-at-a-time rule and pass **live `gh issue view` pointers** into child tasks — do not substitute a local markdown mirror of the tickets.

## Per-ticket loop

For the single active ticket:

1. **Clarify the slice** — Confirm the ticket is the one to implement now (OPEN; blockers done). Prefer frontier tickets. Do not expand into neighboring tickets.

2. **Read the contract** — From the issue body/comments, extract and obey: scope, acceptance criteria, verification instructions, and any “agent execution contract”. Use the parent’s terminology. Implement only this ticket’s observable behavior; extend existing repo machinery rather than building a parallel framework.

3. **Seams** — Reuse seams already agreed in the spec/tickets. If none are present, propose the highest practical seam briefly and confirm once before coding.

4. **Implement (TDD where possible)** — Prefer red → green at those seams. If a project `tdd` (or equivalent) skill is installed, follow it; otherwise apply standard TDD without requiring another pack.

5. **Keep feedback tight** — Discover the repo’s usual commands from `AGENTS.md` / README / mise/npm/cargo/etc. Run typechecks and focused tests while iterating; run the full relevant suite (and any ticket-stated verification) before claiming done. Do not invent a foreign toolchain.

6. **Review** — Careful pass over the diff (correctness, scope creep, missing tests, ticket AC coverage). If a `code-review` (or equivalent) skill is installed, use it; otherwise review yourself and summarize with evidence.

7. **Quality gates / fixes** — If review or gates fail, apply fixes **on the same slice**, re-run verification, then a short final review. Cap fix rounds reasonably; if still failing, stop and report with reproduction commands — do not silently move to the next ticket.

8. **Commit** — Commit on the branch the repo expects for this work (current branch, or the ticket’s task branch/worktree if the project uses that convention). Clear message matching repo style; mention `#<n>` when useful. Do **not** push or merge unless the user asks. Do **not** close tracker issues unless the user authorizes tracker writes (then follow **`issue-tracker`**).

## Subagents / orchestration

When launching a child (pi-subagents, Cursor Task, etc.) to run this skill:

- Task text must tell the child to **load/follow `implement`** and to **`gh issue view <n> --comments`** (plus parent if named).
- Put a short scope / AC / verify summary **in the task prompt** if the model is small — still sourced from the live issue, not from a file you wrote under the repo.
- Point at repo rules (`AGENTS.md`, project standards skills) by path; do not paste entire skill bodies unless required.
- One child implements one ticket; a separate fresh-context reviewer is encouraged when the harness supports it.

## Out of scope

- Redesigning the ticket breakdown (use **`to-tickets`**).
- Rewriting the parent spec (use **`to-spec`**).
- Publishing new tracker issues unless the user explicitly asks as part of this work.
- Production access, approving baselines/snapshots, or changing unrelated worktrees — follow the ticket and repo hard rules.

## Changelog

- `0.2.0` — GH Issues as SoT; forbid ticket mirrors on disk; one-at-a-time queue; full implement→verify→review→fix→commit loop; subagent pointer rules.
- `0.1.0` — Initial `implement` skill; generic repo tooling; optional tdd/code-review; wired to jborkowski/wikiskill tracker/spec/tickets siblings.
