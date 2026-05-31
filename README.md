<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<!-- Commercial license available -->
<!-- © Concepts 1996–2026 Miroslav Šotek. All rights reserved. -->
<!-- © Code 2020–2026 Miroslav Šotek. All rights reserved. -->
<!-- ORCID: 0009-0009-3560-0851 -->
<!-- Contact: www.anulum.li | protoscience@anulum.li -->
<!-- HUSHLINE — public documentation -->

# Hushline

## Local command output muting for prompt chains

`hushline` is a thin, local wrapper that runs any command, then filters and shapes
stdout/stderr before it reaches the caller. It is intended for deterministic,
privacy-aware prompt chains and local automation where untrusted or noisy output
can break downstream parsing.

## What Hushline gives you

- Consistent, filtered command output.
- Optional redaction of tokens and secrets via regex.
- Stable line handling with configurable line width and output limits.
- Optional local gate checks before command execution.
- No network reporting, telemetry, or cloud dependency.

## Quick start

Build:

```bash
go build -o /usr/local/bin/hushline ./cmd/hushline
```

Show locations:

```bash
hushline manifest show
```

Create profiles:

```bash
hushline manifest init
hushline manifest init --global
```

Run a command:

```bash
hushline mute -- git status
```

Permit checks:

```bash
hushline permit status
hushline permit allow
```

## Command surface

- `hushline mute [--max-lines N] [--max-width N] [--raw] [--pipe-errors bool] [--timeout N] -- <command> ...`
- `hushline manifest init [--global|--local]`
- `hushline manifest show`
- `hushline permit [status|allow] [path]`
- `hushline version`

`mute` runs the child process and routes output through the configured muting
pipeline.

`permit` stores a local marker file in `.hushline/permitted` so only approved
directories execute when `require_permit` is enabled.

## Configuration

Config merge order is:

1. built-in defaults
2. global profile
3. local profile in current working directory

Global profile path: `$XDG_CONFIG_HOME/hushline/profile.json` (or platform equivalent).
Local profile path: `.hushline/profile.json` in the current directory.

Example config:

```json
{
  "max_lines": 2000,
  "line_width": 0,
  "strip_ansi": true,
  "preserve_errors": true,
  "require_permit": false,
  "mask_patterns": [
    "AKIA[0-9A-Z]{16}",
    "sk-[a-zA-Z0-9]{20,}"
  ],
  "silence_rules": [
    {
      "name": "ci-trim",
      "pattern": "\\n+",
      "replacement": " "
    },
    {
      "name": "collapse-space",
      "pattern": "[ \\t]{2,}",
      "replacement": " "
    }
  ]
}
```

## Notes for integration

- Repository (public): https://github.com/anulum/HushLine
- GitHub Pages: https://anulum.github.io/HushLine/
- Use `hushline mute` at the boundary of any command execution stage.
- Keep `~/.config/hushline` and `.hushline` local for private environments.
- Keep redaction rules strict and reviewed.
- Keep the repository checked out as `03_CODE/HushLine` for enterprise path rules.

## Polyglot integration

- The enterprise path is language-agnostic by interface:
  - CLI contract is preserved across implementations.
  - You can choose a rewrite in Go, Rust, Python, or Node based on latency, embedding, and ops constraints.
- Reference policy:
  - [enterprise_polyglot_integration.md](docs/guide.md)
  - [cores/README.md](cores/README.md)

For deeper usage details, see:

- `docs/guide.md`
- `docs/development.md`
- `docs/release.md`
