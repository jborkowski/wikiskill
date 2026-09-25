# wikiskill

Agent skills for WikiSkill-style workflows: persistent lessons, versioned skills, and evidence-backed evaluation.

Installable via [skills.sh](https://www.skills.sh) / the [`skills`](https://github.com/vercel-labs/skills) CLI.

## Install

Once this repo is public and contains skills under `skills/`:

```bash
# List available skills
npx skills add https://github.com/jborkowski/wikiskills --list

# Install one skill
npx skills add https://github.com/jborkowski/wikiskills --skill <skill>

# Or GitHub shorthand
npx skills add jborkowski/wikiskills --skill <skill>
```

> Local clone is currently named `wikiskill`; the install URL uses `wikiskills` after the GitHub rename.

From a local checkout:

```bash
npx skills add ./path/to/wikiskill --list
npx skills add ./path/to/wikiskill --skill <skill>
```

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
