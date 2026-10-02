# Go Formula Patterns

Load when `go.mod` is present.

## Research

| What | Where |
|------|-------|
| Binary name(s) | `cmd/<name>/`, or `main.go` at root |
| Version injection | `var version` / `internal/version` — wire via `-X` |
| CGO | `import "C"` / `#cgo` → add system lib deps |
| Completions | cobra / urfave — optional install |

```bash
ls cmd/ 2>/dev/null || ls main.go
grep -R --include='*.go' -n 'version' . | head
```

## Dependencies

```ruby
depends_on "go" => :build
```

Add runtime/`CGO` libs globally when linkage requires them.

## Install block

Inside the `cd root do … end` from the formula template:

```ruby
system "go", "build", *std_go_args(ldflags: "-s -w -X main.version=#{version}"), "./cmd/<binary>"
```

- Root `main.go`: omit the package path argument.
- Multiple binaries: build each path, or `./cmd/...` when appropriate.
- `-s -w` strips debug info; adjust `-X` package path to match the real `version` var.

## Test block

```ruby
test do
  assert_match "<binary>", shell_output("#{bin}/<binary> --help 2>&1")
end
```

## Common issues

- Binary name ≠ formula name — trust `cmd/` dir or Go module product name
- CGO with `CGO_ENABLED=0` will break projects that need native libs
- Version `-X` path wrong → binary still builds but `--version` stays `dev`
## Why each flag

| Element | Reason |
|---------|--------|
| `std_go_args` | Injects Homebrew's GOPATH/GOCACHE isolation + correct bindir; hand-rolled `go build -o` breaks reproducibly in the sandbox |
| `-s -w` | Strips symbol/DWARF tables; smaller bottle, no runtime cost for a CLI |
| `-X main.version=#{version}` | Without it `--version` reports `dev` and `brew audit` / user trust checks fail |
| `2>&1` in test | Cobra/urfave print usage to stderr; without redirection the assert never sees the output |

## Failure remedies

| Symptom | Fix |
|---------|-----|
| `version` shows `dev` | The `-X` package path doesn't match where the var lives — grep `R.*version.*string` for the real path |
| Build works, binary missing from bin | Multiple `cmd/` entries but only one built — build each path explicitly |
| CGO link error in Homebrew sandbox | Add the missing lib (`depends_on "openssl@3"` etc.) globally, not `on_linux` only |
