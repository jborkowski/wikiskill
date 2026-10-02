# Worked Example — Go CLI with daemon mode

Fully resolved reference for the in-repo local-tap pattern. Every value is
real (fictitious project `gitmirror` by `acme`); use it as the ground truth when
filling the [formula-template.md](../formula-template.md) placeholders.

Project shape that produced this example:

| Signal | Value |
|--------|-------|
| Build | `go.mod` (Go 1.22), `cmd/gitmirror/main.go` |
| Version | git tag `v0.3.1` → `0.3.1` |
| Version var | `internal/version.Version` (string) |
| Daemon | `gitmirror daemon` subcommand |
| License | MIT |
| Remote | `https://github.com/acme/gitmirror` |

## Formula/gitmirror.rb

```ruby
class Gitmirror < Formula
  desc "Mirror local git repositories to remotes on a schedule"
  homepage "https://github.com/acme/gitmirror"
  version "0.3.1"
  license "MIT"

  # dual-source pattern: prefer the tarball packed by `make pack`
  # into the local tap; fall back to building from the git HEAD.
  local_tarball = begin
    Tap.fetch("acme/gitmirror").path/"gitmirror-src.tar.gz"
  rescue NameError, LoadError, StandardError
    nil
  end

  if local_tarball&.exist?
    url "file://#{local_tarball}"
    sha256 local_tarball.sha256
  else
    url "https://github.com/acme/gitmirror.git",
        branch: "main"
  end

  depends_on "go" => :build

  def install
    # The packed tarball wraps sources in build-src/; a git checkout does not.
    root = (buildpath/"build-src").directory? ? buildpath/"build-src" : buildpath
    cd root do
      system "go", "build",
        *std_go_args(ldflags: "-s -w -X github.com/acme/gitmirror/internal/version.Version=#{version}"),
        "./cmd/gitmirror"
    end
  end

  service do
    run [opt_bin/"gitmirror", "daemon"]
    keep_alive true
    process_type :background
    log_path var/"log/gitmirror.log"
    error_log_path var/"log/gitmirror.err.log"
    environment_variables PATH: std_service_path_env,
                          HOME: Dir.home
  end

  test do
    assert_match "gitmirror", shell_output("#{bin}/gitmirror --help 2>&1")
  end
end
```

## Corresponding Makefile fragment

```makefile
BREW    ?= brew
TAP     := acme/gitmirror
FORMULA := $(TAP)/gitmirror
export HOMEBREW_NO_AUTO_UPDATE ?= 1
```

`pack`/`install`/`uninstall`/service targets come unchanged from
[makefile-targets.md](../makefile-targets.md) and [service-block.md](../service-block.md).

## Why each non-obvious line exists

| Line | Reason |
|------|--------|
| `Tap.fetch(...)` begin/rescue | A git-only consumer (no local tap) must still evaluate the formula without raising |
| `build-src` root dance | `make pack` tars a `build-src/` wrapper dir; git HEAD checkouts have no wrapper — `install` must work for both |
| `-X ...version.Version=#{version}` | Injects the formula version into the binary so `--version` matches `brew info` |
| `opt_bin` in `service.run` | Resolves through the versioned optdir so upgrades don't leave the daemon pointing at a deleted path |
| No `sha256` on the git URL | HEAD moves; Homebrew only requires a checksum for the stable file URL |
