# Swift Formula Patterns

Load when `Package.swift` is present.

## Research

| What | Where |
|------|-------|
| Binary / product | `.executableTarget` / `.executable` product |
| Tools version | `swift-tools-version` header |
| Platforms | `platforms:` — macOS-only is common |
| System libs | `pkgConfig` / unsafe flags |

```bash
grep -E 'executableTarget|executable\(|swift-tools-version|platforms' Package.swift
```

## Dependencies

```ruby
# Usually none beyond Xcode CLT / system Swift.
# depends_on xcode: ["14.0", :build]  # only if required
```

## Install block

Inside the `cd root do … end` from the formula template:

```ruby
system "swift", "build", "-c", "release", "--disable-sandbox"
bin.install ".build/release/<binary>"
```

Linux portability (when supported):

```ruby
system "swift", "build", "-c", "release", "--disable-sandbox", "--static-swift-stdlib"
bin.install ".build/release/<binary>"
```

## Test block

```ruby
test do
  assert_match "<binary>", shell_output("#{bin}/<binary> --help 2>&1")
end
```

## Common issues

- Product/binary name ≠ package name — read `Package.swift` products
- Sandbox: always pass `--disable-sandbox` under Homebrew
- macOS-only packages should not claim Linux support in `desc`/docs casually
## Why each flag

| Element | Reason |
|---------|--------|
| `-c release` | Debug builds are 10–50x slower; Homebrew formula must ship release |
| `--disable-sandbox` | SwiftPM's own sandbox conflicts with Homebrew's build isolation; without this flag builds hang |
| `--static-swift-stdlib` (Linux) | Avoids runtime dependency on a matching system Swift runtime |
| `bin.install ".build/release/<binary>"` | `swift build` places output only under `.build`; no std helper exists for Swift |

## Failure remedies

| Symptom | Fix |
|---------|-----|
| Binary name not found in `.build/release` | Product name ≠ package name — read `products → .executable` in Package.swift |
| Sandbox hang | Confirm `--disable-sandbox` is present; it is the single most common Swift formula failure |
| Linux symbol errors | Add `--static-swift-stdlib`; if still failing the package is macOS-only — say so in `desc` |
