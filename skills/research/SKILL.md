---
name: research
description: Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo. Use when the user wants a topic researched, docs or API facts gathered, or reading legwork delegated to a background agent.
disable-model-invocation: true
metadata:
  version: "0.2.1"
---

Spin up a **background agent** to do the research, so you keep working while it reads.

Its job:

1. Investigate the question against **primary sources** (official docs, source code, specs, first-party APIs), not a secondary write-up of them. Follow every claim back to the source that owns it.
2. Write the findings to a single Markdown file, citing each claim's source.
3. Save it where the repo already keeps such notes; match the existing convention, and if there is none, put it somewhere sensible and say where.

## Speed with `px` (when available)

If `command -v px` succeeds, the background agent may use it to accelerate discovery. Treat its output as leads only: every kept claim still needs the primary source that owns it.

| Need | Command |
| --- | --- |
| Deep pass (default for open questions) | `px research --out <path> "<question>"` |
| Quick fact / narrow lookup | `px search --out <path> "<question>"` |

`<path>` is the same notes location chosen in step 3 — never a hardcoded home or machine path. If `px` is missing or the command fails, fall back to direct reading. Do not install tools, log in, or ask for credentials unless the user asks.
