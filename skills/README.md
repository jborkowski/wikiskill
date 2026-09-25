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
npx skills add https://github.com/jborkowski/wikiskills --skill <skill>
```
