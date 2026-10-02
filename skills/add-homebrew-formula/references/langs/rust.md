# Rust Formula Patterns

Load when `Cargo.toml` is present.

## Research

| What | Where |
|------|-------|
| Binary name(s) | `Cargo.toml` `[[bin]]` / `src/main.rs` |
| Workspace | `[workspace]` members |
| Native deps | `openssl`, `sqlite` crates → `depends_on` |
| Features | `[features]` / README feature flags |

```bash
grep -A2 '\[\[bin\]\]' Cargo.toml || true
grep -E 'openssl|libsqlite|pkg-config' Cargo.toml Cargo.lock 2>/dev/null | head
```

## Dependencies

```ruby
depends_on "rust" => :build
# If dynamically linked:
# depends_on "openssl@3"
```

## Install block

Inside the `cd root do … end` from the formula template:

```ruby
system "cargo", "install", *std_cargo_args, "--path", "."
```

Workspace member:

```ruby
system "cargo", "install", *std_cargo_args, "--path", "crates/<binary>"
```

Optional features:

```ruby
system "cargo", "install", *std_cargo_args, "--path", ".", "--features", "foo"
```

## Test block

```ruby
test do
  assert_match version.to_s, shell_output("#{bin}/<binary> --version")
rescue
  assert_match "<binary>", shell_output("#{bin}/<binary> --help 2>&1")
end
```

## Common issues

- OpenSSL linkage failures → add `depends_on "openssl@3"` globally (not only `on_linux`)
- Binary name from `[[bin]] name =` may differ from package/crate name
- Very large crates may need `ENV.deparallelize` rarely — prefer default parallelism
## Why each flag

| Element | Reason |
|---------|--------|
| `std_cargo_args` | Points cargo at Homebrew's isolated CARGO_HOME + `--locked`; a bare `--path` install can drift from `Cargo.lock` |
| `--path .` vs crate name | Path installs build exactly the checked-out sources; a name install would fetch crates.io and ignore local changes |
| `openssl@3` as global dep | `on_linux`-only placement breaks macOS bottles; global is always safe |
| rescue in test | Not all CLIs implement `--version`; the fallback keeps the test honest instead of guessing |

## Failure remedies

| Symptom | Fix |
|---------|-----|
| `pkg-config` not found | Native dep chain needs it: `depends_on "pkg-config" => :build` |
| Build OK, wrong binary name | `[[bin]] name =` differs from package name — trust `[[bin]]`, not the crate name |
| Feature-gated runtime panic | Default features not enabled — add `--features` from the project README's install line |
