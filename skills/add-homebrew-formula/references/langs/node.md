# Node Formula Patterns

Load when `package.json` is present and the deliverable is a CLI.

## Research

| What | Where |
|------|-------|
| Bin entry | `package.json` `"bin"` |
| Package manager | `package-lock.json` / `pnpm-lock.yaml` / `yarn.lock` |
| Native addons | `binding.gyp`, `node-gyp` |
| Build step | `"prepare"` / `"prepublishOnly"` / `tsup` / `tsc` |

```bash
node -e 'const p=require("./package.json"); console.log(p.bin||p.name)'
```

## Dependencies

```ruby
depends_on "node"
# Native modules may also need:
# depends_on "python" => :build
```

## Install block

Prefer Homebrew's npm helpers when applicable:

```ruby
system "npm", "install", *std_npm_args
bin.install_symlink libexec/"bin/<binary>"
```

If the project ships a single built JS entry without a full npm package layout:

```ruby
libexec.install Dir["*"]
(bin/"<binary>").write_env_script libexec/"bin/<binary>", PATH: "#{Formula["node"].opt_bin}:$PATH"
```

Adapt to the real `bin` field — do not invent wrapper names.

## Test block

```ruby
test do
  assert_match "<binary>", shell_output("#{bin}/<binary> --help 2>&1")
end
```

## Common issues

- `bin` map key ≠ package name
- Native addons need build toolchain deps
- Prefer installing the published package layout over hand-copying `node_modules`
## Why each flag

| Element | Reason |
|---------|--------|
| `std_npm_args` | Forces `--global`-style install into the formula prefix with production deps only |
| `bin.install_symlink libexec/"bin/…"` | npm writes its shim to libexec; symlink into `bin` makes it executable on PATH |
| `write_env_script … PATH: node opt_bin` | Without node on PATH the shim fails at runtime with `node: command not found` |
| `depends_on "node"` (no :build) | Node is a runtime dep — the shim invokes it every run |

## Failure remedies

| Symptom | Fix |
|---------|-----|
| Shim not executable / ENOENT | The `bin` map key differs from the installed filename — check `package.json` `bin` object |
| Native module build fails | Add `depends_on "python" => :build` / pkg-config as needed by node-gyp |
| Works locally, missing dep in brew | `.npmignore`/`files` excludes a runtime file — prefer `std_npm_args` production install over `tsup` artifacts |
