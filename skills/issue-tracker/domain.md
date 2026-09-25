# Domain Docs

Optional conventions for consuming **this repo's** domain documentation. These paths are recommendations shared by many engineering workflows — **not** required for `issue-tracker` or `to-spec` to function.

## Before exploring, prefer these if present

- **`CONTEXT.md`** at the repo root, or
- **`CONTEXT-MAP.md`** at the repo root if it exists: it points at one `CONTEXT.md` per context. Read each one relevant to the topic.
- **`docs/adr/`**: read ADRs that touch the area you're about to work in. In multi-context repos, also check `src/<context>/docs/adr/` when that layout exists.

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront unless the user asks for domain modeling.

Other common glossary / decision locations (use if the repo clearly has them): `docs/glossary.md`, `ARCHITECTURE.md`, `docs/decisions/`, ADR tools under `docs/adr`.

## Example layouts (illustrative)

Single-context:

```
/
├── CONTEXT.md          # optional
├── docs/adr/           # optional
└── src/
```

Multi-context (only when `CONTEXT-MAP.md` exists):

```
/
├── CONTEXT-MAP.md
├── docs/adr/
└── src/
    ├── ordering/CONTEXT.md
    └── billing/CONTEXT.md
```

## Use the project's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), prefer terms the repo already uses in its glossary or docs. Don't invent synonyms the project avoids.

## Flag decision conflicts

If your output contradicts an existing ADR or recorded decision, surface it explicitly rather than silently overriding.
