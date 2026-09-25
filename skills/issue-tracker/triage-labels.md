# Triage Labels

Canonical **roles** used by this skills pack, mapped to **this repo's** GitHub label strings.

After installing into a project, edit the **Repo label** column so it matches labels that exist (or will exist) on that repository. Leave a cell blank only temporarily; agents should ask before inventing labels.

| Role | Repo label | Meaning |
| --- | --- | --- |
| `needs-triage` | `needs-triage` | Maintainer needs to evaluate this issue |
| `needs-info` | `needs-info` | Waiting on reporter for more information |
| `ready-for-agent` | `ready-for-agent` | Fully specified, ready for an AFK / agent run |
| `ready-for-human` | `ready-for-human` | Requires human implementation |
| `wontfix` | `wontfix` | Will not be actioned |

When a skill says “apply the AFK-ready triage label”, use the **Repo label** for role `ready-for-agent` (right-hand editable column above — same string until you customize it).

## Adapting to an existing tracker

Examples (illustrative only — put your real strings in the table):

| Role | Example remaps |
| --- | --- |
| `ready-for-agent` | `agent-ready`, `autofix`, `good-first-agent` |
| `needs-triage` | `triage`, `unreviewed` |
| `needs-info` | `waiting-for-author` |

If the repo uses fewer labels, map multiple roles to the closest existing label and note that in a comment under the table.
