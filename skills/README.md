# Skills

Each subdirectory is one installable skill for the [skills.sh](https://www.skills.sh) ecosystem.

```
skills/
  <skill-name>/
    SKILL.md           # required
    scripts/           # optional helpers
    references/        # optional progressive disclosure
    assets/            # optional templates / static files
```

These skills are written to be **generic**: they work in any GitHub-backed clone after a short per-repo config step. They do not embed a single product's paths, remotes, or label taxonomy.

## Pack contents

| Skill | Purpose |
| --- | --- |
| `issue-tracker` | Safe GitHub Issues read/write, related-issue discovery, triage **roles** → repo labels |
| `to-spec` | Synthesize a conversation into a spec and publish via `issue-tracker` |
| `to-tickets` | Break a plan/spec into tracer-bullet tickets with blockers; publish via `issue-tracker` or local scratch files |
| `implement` | Implement a spec or ticket slice (TDD when possible, review, commit) |
| `skill-evolve` | Score session runs, write evaluation retrospectives, distill lessons, patch skills, dogfood |

## Adapt to your repo (required for real use)

After `npx skills add jborkowski/wikiskill --skill issue-tracker` (project or global install):

1. Open the installed `triage-labels.md` and set the **Repo label** column to labels that exist on **your** GitHub repo (create labels in GitHub if needed).
2. Optionally flip **PRs as a request surface** in `issue-tracker-github.md`.
3. Install the other skills from the same pack (`to-spec`, `to-tickets`, `implement`, `skill-evolve`) so they share the same `issue-tracker` copy.

Typical flow: **`to-spec`** → **`to-tickets`** → **`implement`** (frontier tickets), with **`issue-tracker`** for all publish/fetch. Use **`skill-evolve`** to evaluate and improve any of those skills from agent transcripts.

`to-spec` / `to-tickets` / `implement` never assume a particular codebase layout; they explore whatever repo the agent is in.

## Requirements

- Directory name matches the `name` field in `SKILL.md`
- `name`: lowercase letters, numbers, hyphens only (max 64 chars)
- `description`: what the skill does **and** when to use it (max 1024 chars)

## Create a skill

From this directory (so the frontmatter `name` matches the folder):

```bash
cd skills
npx skills init my-skill
```

Then verify discovery from the repo root:

```bash
npx skills add . --list
npx skills add . --skill my-skill -l
```

Optional: add root `skills.sh.json` to group skills on the [skills.sh](https://www.skills.sh) repo page once you have more than one skill.

Skills here are what users install with:

```bash
npx skills add https://github.com/jborkowski/wikiskill --skill issue-tracker
npx skills add jborkowski/wikiskill --skill to-spec
npx skills add jborkowski/wikiskill --skill to-tickets
npx skills add jborkowski/wikiskill --skill implement
npx skills add jborkowski/wikiskill --skill skill-evolve
```
