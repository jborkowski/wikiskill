---
name: to-spec
description: "Turn the current conversation into a portable spec and publish it as a GitHub Issue via issue-tracker: draft in chat only — never write local design/spec markdown."
disable-model-invocation: true
metadata:
  version: "0.4.0"
---

# To Spec

Skill version: `0.4.0`

Generic skill for **any** repository. It synthesizes a spec from the current conversation and codebase understanding. Do NOT interview the user; if something critical is missing, record it under **Further Notes** (or stop with a short “blocked on …” list).

## Dependencies

Publishing uses the sibling **`issue-tracker`** skill (same skills pack). Follow that skill for:

- Bootstrap / remote confirmation
- Related-issue discovery and hard publish gate
- Write authorization
- Role → **Repo label** resolution via `triage-labels.md`

Never suggest a third-party skills setup command. If `issue-tracker` is not installed, tell the user to install it from this skills pack, e.g.:

`npx skills add jborkowski/wikiskill --skill issue-tracker`

Then ensure that install's `triage-labels.md` matches the **target** GitHub repo's labels (the project you are working in, not necessarily this skills pack).

## Process

1. Explore the current repo (not a hard-coded path). Prefer domain vocabulary and ADRs when present (`issue-tracker`'s `domain.md`); if missing, proceed silently.

2. **Seams checkpoint (required):** Sketch the seams at which you're going to test the feature. Prefer existing seams; use the highest seam possible; minimize new seams (ideal: one).

   Present the seam list briefly and **check with the user that these seams match their expectations** before writing Implementation Decisions / Testing Decisions or publishing.

3. **Draft the spec in the chat reply only** (use the template below). **Do not write the spec to the working tree** — no `docs/design/**`, `docs/**/*spec*.md`, `.scratch/**`, or similar. Design belongs in GitHub Issues via `issue-tracker`, not on disk.

   **Publish gate:** do not publish until all six core sections are present and non-empty:
   Problem Statement, Solution, User Stories, Implementation Decisions, Testing Decisions, Out of Scope.

4. Publish only with **`issue-tracker`**: hard publish gate, create only when the user authorized publication, put the full template in the **issue body**, apply the **Repo label** for role `ready-for-agent` from that install's `triage-labels.md`, and name related-issue candidates (or an explicit none-found statement) in the issue body.

<spec-template>

## Problem Statement

The problem that the user is facing, from the user's perspective.

## Solution

The solution to the problem, from the user's perspective.

## User Stories

A LONG, numbered list of user stories. Each user story should be in the format of:

1. As an <actor>, I want a <feature>, so that <benefit>

<user-story-example>
1. As a mobile bank customer, I want to see balance on my accounts, so that I can make better informed decisions about my spending
</user-story-example>

This list of user stories should be extremely extensive and cover all aspects of the feature.

## Implementation Decisions

A list of implementation decisions that were made. This can include:

- The modules that will be built/modified
- The interfaces of those modules that will be modified
- Technical clarifications from the developer
- Architectural decisions
- Schema changes
- API contracts
- Specific interactions

Do NOT include specific file paths or code snippets. They may end up being outdated very quickly.

Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it within the relevant decision and note briefly that it came from a prototype. Trim to the decision-rich parts, not a working demo, just the important bits.

## Testing Decisions

A list of testing decisions that were made. Include:

- A description of what makes a good test (only test external behavior, not implementation details)
- Which modules will be tested
- Prior art for the tests (i.e. similar types of tests in the codebase)

## Out of Scope

A description of the things that are out of scope for this spec.

## Further Notes

Any further notes about the feature. Put unresolved context gaps here instead of interviewing.

</spec-template>

## Changelog

- `0.4.0` — Specs stay in chat / GitHub Issues only; never write local design/spec markdown.
- `0.3.0` — Fully generic: role→label via issue-tracker; no project-specific setup commands or paths.
- `0.2.0` — Publish gate (6/6 sections); seams checkpoint; issue-tracker-only publish.
- `0.1.0` — Initial `to-spec` skill; wired to sibling issue-tracker.
