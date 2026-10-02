# Private Repositories (SSH-only access)

**Default assumption for this skill: the source repo is private.** Brew's
HTTPS/API machinery (`brew install owner/name`) cannot see private repos — the
only transports that work are:

1. **Local packed tarball** (the `make pack` target) — brew needs
   **zero** network access to the source repo. This is why the dual-source
   template prefers the tarball.
2. **SSH git clone** — `git@github.com:<owner>/<repo>.git`, using the user's
   SSH key.

## Detection (Phase 1)

| Signal | Meaning |
|--------|---------|
| `git remote -v` shows `git@github.com:…` | SSH remote → private-first pattern |
| `git remote -v` shows `https://…` but `git ls-remote` fails without creds / CI uses `GH_TOKEN` | Private behind HTTPS → treat as private; switch remote to SSH for brew |
| `gh repo view --json visibility` (if gh installed) | Confirms `visibility: "private"` |

When private, formula `homepage` still points to the repo URL (display-only),
but the **`url` for the git fallback must be SSH**.

## Formula git fallback (private variant)

```ruby
if local_tarball&.exist?
  url "file://#{local_tarball}"
  sha256 local_tarball.sha256
else
  url "git@github.com:<owner>/<repo>.git",   # SSH — NOT https
      branch: "main"
end
```

Homebrew clones git-source formulas with the invoking user's git/SSH config, so
anyone with repo read access + a registered SSH key can build. No token, no
HTTPS fallback needed.

## Tapping a private formula repo (team distribution)

`brew tap owner/repo` without a URL uses the GitHub API and **fails for private
repos**. Always pass the git URL explicitly:

```bash
brew tap <owner>/<repo> git@github.com:<owner>/<repo>.git
# requires: HOMEBREW_NO_INSTALL_FROM_API=1 (env or shell rc)
brew install --build-from-source <owner>/<repo>/<name>
```

Notes:
- `HOMEBREW_NO_INSTALL_FROM_API=1` is mandatory — otherwise brew checks the
  public API index and reports the formula as missing.
- `--build-from-source` is mandatory — private repos get no bottles.
- Every consumer needs: SSH key with repo read access, and Homebrew's
  developer mode conveniences (`brew developer on` avoids some API checks) if
  hitting further walls.

## Makefile adjustments for private repos

The core targets in [makefile-targets.md](makefile-targets.md) are unchanged —
`tap-new` creates a **local** tap (no network), and `pack` copies the source in.
For the team-distribution variant, replace the `tap` target body with:

```makefile
tap:
	@if ! $(BREW) tap | grep -qx "$(TAP)"; then \
		$(BREW) tap "$(TAP)" "git@github.com:$(TAP).git"; \
	fi
```

and export `HOMEBREW_NO_INSTALL_FROM_API=1` alongside the existing
`HOMEBREW_NO_AUTO_UPDATE`.

## Failure remedies

| Symptom | Fix |
|---------|------|
| `No available formula` / API 404 | Missing `HOMEBREW_NO_INSTALL_FROM_API=1`, or tap was created without the git URL |
| `Permission denied (publickey)` when cloning | Consumer's SSH key lacks repo access — `ssh -T git@github.com` to verify |
| `ValidationFailed: URL does not end in .git` | HTTPS URL leaked into the formula — must be `git@github.com:…git` |
| CI builds fail to fetch | CI runners have no SSH key: use the local-tarball path (`make pack` artifacts) instead of git fallback |
