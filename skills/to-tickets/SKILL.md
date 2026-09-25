---
name: to-tickets
description: "Break a plan, spec, or the current conversation into tracer-bullet tickets with blocking edges, published as GitHub Issues via the issue-tracker skill (local scratch only if the user explicitly asks for files)."
disable-model-invocation: true
metadata:
  version: "0.2.0"
---

# To Tickets

Skill version: `0.2.0`

Break a plan, spec, or conversation into a set of **tickets**: tracer-bullet vertical slices, each declaring the tickets that **block** it.

## Dependencies

Tracker vocabulary and publish rules come from the sibling **`issue-tracker`** skill in [jborkowski/wikiskill](https://github.com/jborkowski/wikiskill). Follow it for remote confirmation, related-issue discovery, write authorization, and role → **Repo label** resolution (`triage-labels.md`).

If `issue-tracker` is not installed:

`npx skills add jborkowski/wikiskill --skill issue-tracker`

Never invent a parallel tracker setup. Specs may come from sibling **`to-spec`** or an existing issue/path the user names.

## Process

### 1. Gather context

Work from whatever is already in the conversation context. If the user passes a reference (a spec path, an issue number or URL) as an argument, fetch it and read its full body and comments (`issue-tracker`: `gh issue view <n> --comments` when it is a GitHub issue).

### 2. Explore the codebase (optional)

If you have not already explored the codebase, do so to understand the current state of the code. Ticket titles and descriptions should use the project's domain glossary vocabulary when present, and respect ADRs in the area you're touching (`issue-tracker`'s `domain.md`; proceed silently if missing).

Look for opportunities to prefactor the code to make the implementation easier. "Make the change easy, then make the easy change."

### 3. Draft vertical slices

Break the work into **tracer bullet** tickets.

- Each slice cuts a narrow but COMPLETE path through every layer (schema, API, UI, tests): vertical, NOT a horizontal slice of one layer
- A completed slice is demoable or verifiable on its own
- Each slice is sized to fit in a single fresh context window
- Any prefactoring should be done first

Give each ticket its **blocking edges**: the other tickets that must complete before it can start. A ticket with no blockers can start immediately.

**Wide refactors are the exception to vertical slicing.** A **wide refactor** is one mechanical change (rename a column, retype a shared symbol) whose **blast radius** fans across the whole codebase, so a single edit breaks thousands of call sites at once and no vertical slice can land green. Don't force it into a tracer bullet; sequence it as **expand–contract**. First expand: add the new form beside the old so nothing breaks. Then migrate the call sites over in batches sized by blast radius (per package, per directory), each batch its own ticket blocked by the expand, keeping CI green batch to batch because the old form still exists. Finally contract: delete the old form once no caller remains, in a ticket blocked by every migrate batch. When even the batches can't stay green alone, keep the sequence but let them share an integration branch that all block a final integrate-and-verify ticket; green is promised only there.

### 4. Quiz the user

Present the proposed breakdown as a numbered list. For each ticket, show:

- **Title**: short descriptive name
- **Blocked by**: which other tickets (if any) must complete first
- **What it delivers**: the end-to-end behaviour this ticket makes work

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the blocking edges correct: does each ticket only depend on tickets that genuinely gate it?
- Should any tickets be merged or split further?

Iterate until the user approves the breakdown.

### 5. Publish the tickets

Publish the approved tickets as **GitHub Issues** via **`issue-tracker`** (default). Preview the breakdown in the chat reply; do not write ticket markdown under `docs/` or `docs/design/`.

If Issues/`gh` are unavailable, **stop and tell the user** — do not silently fall back to disk. Use **local files** only when the user **explicitly** asks for scratch files.

#### Real issue tracker (default)

Publish one issue per ticket in dependency order (blockers first) so each ticket's blocking edges can reference real identifiers. Follow **`issue-tracker`**: hard publish gate / related-issue discovery for the batch theme, write authorization, native `blocked_by` dependencies when available (else `Blocked by:` lines). Apply the **Repo label** for role `ready-for-agent` unless instructed otherwise; the tickets are agent-grabbable by construction.

Do NOT close or modify any parent issue unless the user separately authorizes that.

#### Local files (explicit opt-in only)

Only if the user asked for files: write one file per ticket under `.scratch/<slug>/issues/<nn>-<slug>.md`, numbered from `01` in dependency order (blockers first). Each file's "Blocked by" lists the numbers/titles it depends on. Use the per-ticket file template below: one ticket per file, never a single combined file. Never use `docs/design/` for tickets.

Work the **frontier**: any ticket whose blockers are all done. For a purely linear chain that means top to bottom.

## Preview template (quiz step)

```text
#<n>: <title>

**What to build:** the end-to-end behaviour this ticket makes work, from the user's perspective, not a layer-by-layer implementation list.

**Blocked by:** the numbers/titles of the tickets that gate this one, or "None (can start immediately)".

**Status:** <ready-for-agent role / Repo label>

- [ ] Acceptance criterion 1
- [ ] Acceptance criterion 2
```

## Per-ticket file / issue body template

```markdown
## Parent

A reference to the parent issue on the tracker (if the source was an existing issue, otherwise omit this section).

## What to build

The end-to-end behaviour this ticket makes work, from the user's perspective, not layer-by-layer implementation.

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2

## Blocked by

- A reference to each blocking ticket, or "None (can start immediately)".
```

In either form, avoid specific file paths or code snippets: they go stale fast. Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it and note briefly that it came from a prototype. Trim to the decision-rich parts, not a working demo, just the important bits.

## Changelog

- `0.2.0` — GitHub Issues default; local scratch only on explicit user request; no `docs/design/` tickets.
- `0.1.0` — Initial `to-tickets` skill; wired to jborkowski/wikiskill `issue-tracker`.
