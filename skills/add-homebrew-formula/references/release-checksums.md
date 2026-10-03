# Release-tarball checksums (variant — compressed)

Default: repo is PRIVATE.

## Hashing rules

- NEVER hash an unauthenticated fetch. Private URL + plain curl = GitHub 404
  HTML page; `shasum` hashes it silently. Check status + content-type first.
- Publish-bound sha256: authenticated download (`gh api repos/OWNER/REPO/tarball/TAG`
  or curl with `gh auth token`) AND byte-verify against brew's downloader route
  (`curl -sL -H "Authorization: token $(gh auth token)"
  https://github.com/OWNER/REPO/archive/refs/tags/TAG.tar.gz`). These two routes
  can differ byte-for-byte — only the archive/refs/tags hash is valid in the formula.
- Tag not yet pushed ⇒ checksum cannot exist. Ship all-zeros
  `"000…0"` placeholder + backfill PR after tag. Users fail install until the
  backfill merges — land bump PR and backfill adjacently.
- Before declaring done: `brew fetch` (or install dry-run) must succeed — it is
  the only check that catches a wrong hash.

## CI

- Compute hash + open backfill PR in tag-push workflow. GITHUB_TOKEN cannot
  open PRs → open with user credentials; that click stays manual.
- Avoid `tar | head` (EPIPE) in release scripts.

## Public repo + existing tag

Plain `curl -L <url> | shasum -a 256` is correct. No placeholder, no auth
ceremony — applying it there is a false positive.
