---
name: implement
description: "Implement a piece of work based on a spec or set of tickets in the current repo: prefer TDD at agreed seams, keep checks green, review, and commit on the current branch."
disable-model-invocation: true
metadata:
  version: "0.1.0"
---

# Implement

Skill version: `0.1.0`

Implement the work described by the user in a **spec** and/or **tickets** for **whatever repository you are in**. Do not assume a hard-coded project path.

## Context sources

Resolve the work from, in order of what the user provided:

1. Explicit ticket / issue numbers or URLs — fetch with sibling **`issue-tracker`** (`gh issue view <n> --comments`) when they are GitHub issues.
2. A spec path or conversation produced by sibling **`to-spec`**.
3. Ticket files under `.scratch/**/issues/` if that is how **`to-tickets`** published locally.
4. Otherwise, the description already in the conversation.

If `issue-tracker` is needed and missing:

`npx skills add jborkowski/wikiskill --skill issue-tracker`

## Process

1. **Clarify the slice** — Identify the single ticket or smallest approved slice you are implementing now. Prefer frontier tickets (blockers done). Do not expand scope into neighboring tickets unless the user asks.

2. **Seams** — Reuse any seams already agreed in the spec/tickets. If none are present, propose the highest practical seam briefly and confirm once before coding.

3. **TDD where possible** — Prefer red → green at those seams. If a project `tdd` (or equivalent) skill is installed, follow it; otherwise apply standard TDD discipline without requiring another skills pack.

4. **Keep feedback tight** — Run typechecking regularly, single test files regularly while iterating, and the full relevant test suite once at the end (project’s usual commands: `mise`, `npm test`, `cargo test`, etc. — discover from the repo; do not invent a foreign toolchain).

5. **Review** — When implementation is done, run a careful pass over the diff (correctness, scope creep, missing tests). If a `code-review` (or equivalent) skill is installed, use it; otherwise perform the review yourself and summarize findings.

6. **Commit** — Commit on the **current** branch with a clear message matching repo conventions. Do not push unless the user asks. Do not close tracker issues unless the user authorizes tracker writes (then follow **`issue-tracker`** authz).

## Out of scope

- Redesigning the ticket breakdown (use **`to-tickets`**).
- Rewriting the parent spec (use **`to-spec`**).
- Publishing new tracker issues unless the user explicitly asks as part of this work.

## Changelog

- `0.1.0` — Initial `implement` skill; generic repo tooling; optional tdd/code-review; wired to jborkowski/wikiskill tracker/spec/tickets siblings.
