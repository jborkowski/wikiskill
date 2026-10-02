---
name: add-homebrew-formula
description: >-
  Add a Homebrew formula to a project using the in-repo local-tap pattern
  (private-repo first: local packed tarball, SSH git fallback). Generates
  Formula/<name>.rb, adds brew Makefile targets (tap, pack, install,
  start/stop/restart/status/logs, uninstall), and optionally sets up a private
  team tap. Use when asked to add Homebrew packaging, create a formula, make a
  project brew-installable, or add brew targets.
disable-model-invocation: true
metadata:
  version: "2.1.0"
---

# Add Homebrew Formula

Add an in-repo Homebrew formula and Makefile targets using the local-tap
pattern (local tarball preferred, git HEAD fallback).

Patterns live under `references/` — **load only what the current project needs**.
Do not preload every language file. A fully resolved example (real values, no
placeholders) lives in
[references/examples/gitmirror-go.md](references/examples/gitmirror-go.md); use
it as ground truth when filling template placeholders.

## Contract

- Generates `Formula/<name>.rb` matching the project's build system
- Adds or extends Makefile with `tap`, `pack`, `install`, `uninstall`, and
  optionally `start`/`stop`/`restart`/`status`/`logs` service targets
- Formula uses the local-tarball-or-git-head dual-source pattern
- No external taps are created automatically — user runs `make install` manually
- Formula aims to pass `brew audit --formula` and `brew style` where possible

## Phases

### 1. Detect project shape

Read the project to determine:

| Signal              | Look for                                             |
|---------------------|------------------------------------------------------|
| Language / build    | `go.mod`, `Cargo.toml`, `Package.swift`, `Makefile`, `pyproject.toml`, `package.json` |
| Binary name         | `cmd/*/main.go`, Cargo `[[bin]]`, Swift product, etc.|
| Version             | git tags, `version` in config files, Makefile `VERSION` |
| Runtime deps        | linked libraries, CLI deps, cask deps                |
| Service             | daemon subcommand, `launchd` hints, existing plist   |
| GitHub owner / repo | `git remote -v`                                      |
| Existing formula    | `Formula/*.rb`                                       |
| Private / SSH-only   | `git@github.com:` remote, `GH_TOKEN` in CI, `gh repo view` visibility |

Add a **private-repo check** in this phase: if the remote is `git@github.com:`
or the repo is private (`gh repo view`), load
[references/private-repos.md](references/private-repos.md) — the git fallback
URL must be SSH, and team taps need `HOMEBREW_NO_INSTALL_FROM_API=1`.

If a `Formula/*.rb` already exists, confirm with the user before overwriting.

### 2. Load the matching pattern refs

After detecting language/service needs, **read only** the relevant files:

| Need | Load |
|------|------|
| Formula skeleton (always) | [references/formula-template.md](references/formula-template.md) |
| Makefile targets (always) | [references/makefile-targets.md](references/makefile-targets.md) |
| Go | [references/langs/go.md](references/langs/go.md) |
| Rust | [references/langs/rust.md](references/langs/rust.md) |
| Swift | [references/langs/swift.md](references/langs/swift.md) |
| Node | [references/langs/node.md](references/langs/node.md) |
| Python | [references/langs/python.md](references/langs/python.md) |
| Daemon / `brew services` | [references/service-block.md](references/service-block.md) |
| **Private repo (default assumption)** | [references/private-repos.md](references/private-repos.md) |
| Verify / audit steps | [references/validation.md](references/validation.md) |

If the language has no dedicated ref, do **not** guess a build recipe: take the
skeleton from [references/formula-template.md](references/formula-template.md),
ask the user for the exact build command the project documents (README,
CI, Makefile), and insert that command verbatim inside the `cd root do … end`
block. State in the output that `<lang>` has no curated ref and the install
block was user-confirmed.

When generating or reviewing any filled formula, cross-check against the worked
example [references/examples/gitmirror-go.md](references/examples/gitmirror-go.md).

### 3. Generate Formula/<name>.rb

Adapt the dual-source template from `references/formula-template.md` using the
language-specific `install` block from the loaded lang ref.

Naming:
- Formula file / tap name: **kebab-case** (`my-tool`)
- Ruby class: **PascalCase** (`MyTool`)

### 4. Add Makefile targets

Merge targets from `references/makefile-targets.md` into an existing Makefile
(or create one). Add service targets **only** when the formula has a `service`
block (see `references/service-block.md`).

### 5. Hand off verification

Do **not** run `make install` or `brew install`. Point the user at
[references/validation.md](references/validation.md) for the manual checklist.

### 6. Optional: public tap

Only if the user asks for a public `brew tap`:

```bash
git add Formula/<name>.rb && git push
# Consumers:
brew tap <owner>/<name> https://github.com/<owner>/<name>
brew install <name>
```

Default remains the in-repo local tap — no separate `homebrew-<name>` repo
unless explicitly requested.

## Output Format

```
Created:
  Formula/<name>.rb     — Homebrew formula
  Makefile              — brew targets (tap, pack, install, uninstall, …)

Patterns used:
  references/formula-template.md
  references/langs/<lang>.md
  …

Next steps (run manually):
  make install          — build & install via Homebrew
  <binary> --help       — verify
```

## Anti-Patterns

- **Don't preload every `references/langs/*.md`** — load only the detected language.
- **Don't run `make install` or `brew install` automatically** — generate files only.
- **Don't create a separate `homebrew-<name>` repo** unless the user asks.
- **Don't use `brew install ./Formula/<name>.rb`** — go through the local tap
  (`brew tap-new` → pack → `brew install <tap>/<formula>`).
- **Don't hardcode SHA256 for git sources** — the local-tarball/head pattern
  handles this.
- **Don't add service targets if there's no daemon mode** — check first.
- **Don't clobber existing Makefile targets** — merge with existing content.
