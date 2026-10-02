# Formula Template (local-tarball / git-head)

In-repo tap pattern: prefer a tarball packed by `make pack` into the local tap;
otherwise build from git HEAD.

## Skeleton

```ruby
class <ClassName> < Formula
  desc "<one-line description>"
  homepage "https://github.com/<owner>/<repo>"
  version "<version>"
  license "<license>"

  # Prefer a locally packed tarball from `make install`; otherwise build from git.
  local_tarball = begin
    Tap.fetch("<owner>/<repo>").path/"<name>-src.tar.gz"
  rescue NameError, LoadError, StandardError
    nil
  end

  if local_tarball&.exist?
    url "file://#{local_tarball}"
    sha256 local_tarball.sha256
  else
    url "https://github.com/<owner>/<repo>.git",
        branch: "main"
  end

  depends_on "go" => :build  # replace per language ref

  def install
    root = (buildpath/"build-src").directory? ? buildpath/"build-src" : buildpath
    cd root do
      # Language-specific install — see references/langs/<lang>.md
    end
  end

  # Optional: see references/service-block.md

  test do
    assert_match "<name>", shell_output("#{bin}/<binary> --help")
  end
end
```

## Placeholders

Each `<token>` is a **parameter with a defined source** — never leave one
unsubstituted in generated output. Resolve every row before writing the file:

| Token | Source |
|-------|--------|
| `<ClassName>` | PascalCase of formula name |
| `<name>` | kebab-case formula / binary name |
| `<owner>/<repo>` | from `git remote -v` |
| `<version>` | git tag or project version field |
| `<license>` | SPDX id (`MIT`, `Apache-2.0`, `GPL-3.0-or-later`, …) |
| `<binary>` | actual installed binary name (may differ from formula) |

## Rules

- See [examples/gitmirror-go.md](examples/gitmirror-go.md) for the same skeleton
  fully resolved with real values — use it to disambiguate any placeholder.
- Always wrap the language build in the `build-src` / `buildpath` root dance so
  both packed tarball and git-head installs work.
- Put `depends_on … => :build` before runtime deps; alphabetize within each group.
- Prefer building from source over shipping prebuilt binaries.
- Omit hardcoded `sha256` for the git URL branch — only the local tarball path
  uses checksums (computed at pack time).

## File location

Write to `Formula/<name>.rb` in the project repo (not a separate tap repo).
