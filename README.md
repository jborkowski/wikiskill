# wikiskill

Agent skills for WikiSkill-style workflows: persistent lessons, versioned skills, and evidence-backed evaluation.

Installable via [skills.sh](https://www.skills.sh) / the [`skills`](https://github.com/vercel-labs/skills) CLI.

## Install

The CLI discovers every `skills/<name>/SKILL.md` on the **default branch**. Install all of them in one shot:

```bash
# All skills → all agents (non-interactive)
npx skills add jborkowski/wikiskill --all

# Or: all skills, then pick agents interactively
npx skills add jborkowski/wikiskill --skill '*'
```

List what GitHub currently exposes:

```bash
npx skills add jborkowski/wikiskill --list
```

Install one or several by name:

```bash
npx skills add jborkowski/wikiskill --skill issue-tracker
npx skills add jborkowski/wikiskill --skill to-spec to-tickets implement skill-evolve
```

From a local checkout (includes unpushed skills):

```bash
npx skills add . --list
npx skills add . --skill '*'
```

`skills.sh.json` only controls **groupings on the skills.sh repo page** — it does not change CLI install. Optional: create a [skills.sh pack](https://www.skills.sh/docs/packs) if you want a single `https://skills.sh/p/<id>` URL that always installs the whole set.

## Repository layout

```
skills/
  <skill-name>/
    SKILL.md          # required — YAML frontmatter + instructions
    scripts/          # optional
    references/       # optional
    assets/           # optional
docs/                 # design notes (not installed as skills)
skills.sh.json        # optional — groupings for the skills.sh repo page
```

The CLI discovers skills in `skills/<name>/SKILL.md` (and a few other well-known locations). Each `SKILL.md` must include:

```yaml
---
name: skill-name          # lowercase, hyphens; must match directory name
description: What it does and when to use it
---
```

### Add a skill

```bash
cd skills
npx skills init my-skill
# edit skills/my-skill/SKILL.md (name must match directory)
cd ..
npx skills add . --list
```

See the [Agent Skills specification](https://agentskills.io/specification) for frontmatter rules and optional fields.

Optional root `skills.sh.json` configures groupings on the skills.sh repo page after you publish skills.

## Docs

- [Paper summary](docs/paper-summary.md) — WikiSkill method and implications for a local tool
- [Evaluation notes](docs/evaluation-notes.md) — proposed CLM-based rough evaluation of skill runs
- [paper.pdf](docs/paper.pdf) — source paper

## Evaluation library (CLM + MLX)

From the **repo root**:

```bash
uv sync
uv run eval run
```

Package sources live under [`eval/`](eval/). Details: [`eval/README.md`](eval/README.md).
