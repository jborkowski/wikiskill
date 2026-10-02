# Makefile Brew Targets

Core local-tap workflow: `tap` → `pack` → `install`. Merge into an existing
Makefile; do not wipe unrelated targets.

## Core variables & targets

```makefile
BREW    ?= brew
TAP     := <owner>/<repo>
FORMULA := $(TAP)/<name>
export HOMEBREW_NO_AUTO_UPDATE ?= 1

.PHONY: tap pack install uninstall

tap:
	@if ! $(BREW) tap | grep -qx "$(TAP)"; then \
		$(BREW) tap-new "$(TAP)" --branch main; \
	fi

pack: tap
	@TAPDIR="$$($(BREW) --repo $(TAP))"; \
	mkdir -p "$$TAPDIR/Formula"; \
	rm -rf "$$TAPDIR/build-src" "$$TAPDIR/<name>-src.tar.gz"; \
	rsync -a \
		--exclude '.git/' \
		--exclude 'bin/' \
		--exclude '.cursor/' \
		--exclude '.agents/' \
		--exclude '.claude/' \
		--exclude '.DS_Store' \
		./ "$$TAPDIR/build-src/"; \
	tar -C "$$TAPDIR" -czf "$$TAPDIR/<name>-src.tar.gz" build-src; \
	cp -f Formula/<name>.rb "$$TAPDIR/Formula/<name>.rb"; \
	echo "packed $$TAPDIR/<name>-src.tar.gz"

install: pack
	@if $(BREW) list --formula "$(FORMULA)" >/dev/null 2>&1; then \
		$(BREW) reinstall --build-from-source "$(FORMULA)"; \
	else \
		$(BREW) install --build-from-source "$(FORMULA)"; \
	fi

uninstall:
	-$(BREW) uninstall "$(FORMULA)"
	-$(BREW) untap "$(TAP)"
```

## Why each line is shaped this way

| Line | Reason it must stay exactly this way |
|------|--------------------------------------|
| `BREW ?= brew` | `?=` lets CI/users override with a wrapper brew |
| `TAP := <owner>/<repo>` | In-repo tap identity — must match `git remote` owner/repo exactly, or `Tap.fetch` in the formula resolves the wrong tap |
| `FORMULA := $(TAP)/<name>` | Fully-qualified install name prevents shadowing a same-named core formula |
| `export HOMEBREW_NO_AUTO_UPDATE ?= 1` | Stops `make install` from racing a concurrent `brew update` mid-build |
| `.PHONY: …` | Targets produce no files; without this, a stray file named `install` silences the target |
| `rm -rf … tarball` in `pack` | A stale tarball would keep the previous `sha256`, so edits would silently not ship |
| `build-src/` wrapper dir | The formula's `root = (buildpath/"build-src").directory? …` dance expects exactly this wrapper name |
| rsync `--exclude` list | Ships source only — `.git/`, editor/agent dirs, and stale local `bin/` must not enter the tarball |
| `--build-from-source` | Never let a cached bottle shadow the local tarball build |
| leading `-` in `uninstall` | Uninstall/untap failures (already gone) must not fail the target |

## Service targets (conditional)

Add only when the formula includes a `service` block
([service-block.md](service-block.md)):

```makefile
.PHONY: start stop restart status logs

start:
	$(BREW) services start $(FORMULA)

stop:
	$(BREW) services stop $(FORMULA)

restart:
	$(BREW) services restart $(FORMULA)

status:
	-$(BREW) services info $(FORMULA)

logs:
	@prefix="$$($(BREW) --prefix)"; \
	tail -n 80 -f "$$prefix/var/log/<name>.log" "$$prefix/var/log/<name>.err.log"
```

## Merge rules

- Reuse existing `BREW` / `TAP` variables if present; don't duplicate.
- Keep `.PHONY` declarations additive.
- Prefer appending a clearly marked `# Homebrew` section when the Makefile is large.
- Never replace a project's primary `install` target that builds without Homebrew —
  use a distinct name only if collision is unavoidable, and tell the user.
