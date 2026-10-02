# Validation (user-executed)

The skill generates files only — the user runs every command below. Report the
whole checklist in the skill output so nothing is implicit.

## Install & smoke test

```bash
make install        # tap → pack → build-from-source install; expect: 🍺 <owner>/<repo>/<name> 0.x.y
<binary> --help     # expect: usage text mentioning the binary name
brew info <owner>/<repo>/<name>   # expect: correct version, deps, cellar path
```

Failure → remedy:

| Symptom | Remedy |
|---------|--------|
| `No such file or directory - build-src` | `make pack` never ran; run `make install` (it packs), not `brew install` alone |
| `undefined method 'Tap.fetch'` | Homebrew too old / non-standard env; `brew update` once, retry |
| Formula installs but `--version` shows `dev` | Version injection flag points at the wrong var — re-check the lang ref's `-X`/env wiring |
| `Formula` class name mismatch error | Class must be PascalCase of the filename exactly (`my-tool` → `MyTool`) |

## Style / audit (recommended before any public tap)

```bash
ruby -c Formula/<name>.rb            # syntax; expect: Syntax OK
brew style Formula/<name>.rb         # expect: no offenses (or only pre-existing taps' noise)
brew audit --formula <owner>/<repo>/<name>   # expect: no problems
brew test <owner>/<repo>/<name>      # runs the formula's `test do` block
```

Known acceptable audit finding: `audit` may warn about the `file://` URL — that
is inherent to the local-tarball pattern and only appears with a packed
tarball present.

## Service (only if the formula has a `service` block)

```bash
make start           # expect: Successfully started `...` (label: <owner>/<repo>/<name>)
make status          # expect: running, PID + log paths shown
make logs            # tails both log files; Ctrl-C to stop following
make stop            # expect: Successfully stopped
```

If `make status` shows `error`: read `$(brew --prefix)/var/log/<name>.err.log`
first — 9 times out of 10 it is a missing `PATH` entry, fixed by the
`environment_variables PATH: std_service_path_env` line in
[service-block.md](service-block.md).

## Rollback

```bash
make uninstall       # uninstalls formula, then untaps (both failures tolerated with `-`)
```
