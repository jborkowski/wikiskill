# Issue tracker: GitHub

Generic GitHub Issues operations for **whatever repo you are in**. Use the `gh` CLI. Infer the repository from the local git remote (`gh` does this automatically inside a clone).

## Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc for multi-line bodies. Pass `--label` using strings from this install's `triage-labels.md` (Repo label column).
- **Read an issue**: `gh issue view <number> --comments`, filtering comments by `jq` and also fetching labels.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Search related / duplicate issues**: resolve owner/repo, then  
  `gh search issues --repo <owner>/<repo> "<keywords>" --state open`  
  Prefer this before `gh issue create`.
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..."`

## Pull requests as a triage surface

**PRs as a request surface: no.**  
_(Change to `yes` in your installed copy if this repo treats external PRs as feature requests that share the same triage labels.)_

When set to `yes`, PRs run through the same roles/labels as issues, using the `gh pr` equivalents:

- **Read a PR**: `gh pr view <number> --comments` and `gh pr diff <number>` for the diff.
- **List external PRs for triage**: `gh pr list --state open --json number,title,body,labels,author,authorAssociation,comments` then keep only `authorAssociation` of `CONTRIBUTOR`, `FIRST_TIME_CONTRIBUTOR`, or `NONE` (drop `OWNER`/`MEMBER`/`COLLABORATOR`).
- **Comment / label / close**: `gh pr comment`, `gh pr edit --add-label`/`--remove-label`, `gh pr close`.

GitHub shares one number space across issues and PRs, so a bare `#42` may be either: resolve with `gh pr view 42` and fall back to `gh issue view 42`.

## When a skill says "publish to the issue tracker"

Create a GitHub issue (following write authorization and the hard publish gate in `SKILL.md`).

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --comments`.
