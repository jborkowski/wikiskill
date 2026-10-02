# Service Block (`brew services`)

Add a `service` block only when the project has a real daemon / long-running mode
(e.g. `<binary> daemon`, `serve`, or an existing launchd plist).

## Formula snippet (each line justified)

```ruby
service do
  run [opt_bin/"<binary>", "daemon"]   # optdir symlink survives upgrades; daemon = the project's real background subcommand
  keep_alive true                       # relaunch on crash; drop only if the process self-supervises
  process_type :background              # launchd Nice/ scheduling class; never :interactive for daemons
  log_path var/"log/<name>.log"         # Homebrew-managed var/log — never /tmp or a user home path
  error_log_path var/"log/<name>.err.log"
  environment_variables PATH: std_service_path_env,  # brew-linked deps stay reachable after prefix changes
                        HOME: Dir.home               # daemons reading dotfiles need this; harmless otherwise
end
```

Only `run` is mandatory in Homebrew ≥4.x; keep every line above unless the
project gives a reason to drop one — each exists because a daemon broke
without it.

## Checklist before adding

- [ ] Confirmed daemon/serve subcommand exists and is stable
- [ ] Log paths use `var/"log/<name>.…"` (Homebrew-managed)
- [ ] Makefile service targets added ([makefile-targets.md](makefile-targets.md))
- [ ] No hardcoded absolute user paths in `run` / env

## Anti-patterns

- Adding `service` for a pure CLI with no background mode
- Using `bin/"…"` instead of `opt_bin/"…"` inside `run`
- Forgetting matching `start`/`stop`/`logs` Makefile targets
