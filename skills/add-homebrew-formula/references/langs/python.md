# Python Formula Patterns

Load when `pyproject.toml` / `setup.py` / `requirements.txt` indicates a Python CLI.

## Research

| What | Where |
|------|-------|
| Package / PyPI name | `pyproject.toml` `[project].name` |
| Console scripts | `[project.scripts]` |
| Python version | `requires-python` |
| Native deps | C extensions, `openssl`, etc. |

```bash
grep -A20 '\[project\]' pyproject.toml | head -40
grep -A20 '\[project.scripts\]' pyproject.toml || true
```

## Dependencies

```ruby
depends_on "python@3.12"
```

Pin to the version the project actually supports.

## Install block (libexec venv)

Inside the `cd root do … end` from the formula template:

```ruby
virtualenv_install_with_resources
```

Or explicit virtualenv when resources are declared:

```ruby
venv = virtualenv_create(libexec, "python3.12")
venv.pip_install resources
venv.pip_install_and_link buildpath
```

If installing a pinned PyPI name that differs from the repo:

```ruby
venv.pip_install "<pypi-name>==#{version}"
```

## Test block

```ruby
test do
  assert_match "<binary>", shell_output("#{bin}/<binary> --help 2>&1")
end
```

## Common issues

- PyPI name ≠ repo / formula name — check `[project].name`
- Missing `setuptools` for older `pkg_resources` usage
- Prefer `venv.pip_install`, not raw `system libexec/"bin/pip"`
- Console script name comes from `[project.scripts]`, not the folder name
## Why each flag

| Element | Reason |
|---------|--------|
| `virtualenv_install_with_resources` | One-liner that creates libexec venv, installs declared resources, links console scripts; hand-rolled pip calls break Homebrew isolation |
| `resources` blocks | Each PyPI dependency is installed pinned by Homebrew (parallel, cached) instead of resolving at build time |
| `venv.pip_install_and_link buildpath` | Installs the project itself and symlinks its `[project.scripts]` into `bin` |
| `depends_on "python@3.12"` unpinned-to-latest | Pin the oldest supported minor; unpinned breaks when Homebrew bumps default python |

## Failure remedies

| Symptom | Fix |
|---------|-----|
| Script name mismatch | Console script comes from `[project.scripts]`, not the repo folder name — grep the table |
| `pkg_resources` deprecation crash | Add `resource "setuptools" …` or switch the project to `importlib.metadata` |
| Wheel builds against wrong python | `requires-python` excludes the pinned minor — choose a `python@X.Y` inside the supported range |
