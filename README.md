<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<!-- Commercial license available -->
<!-- © Concepts 1996–2026 Miroslav Šotek. All rights reserved. -->
<!-- © Code 2020–2026 Miroslav Šotek. All rights reserved. -->
<!-- ORCID: 0009-0009-3560-0851 -->
<!-- Contact: www.anulum.li | protoscience@anulum.li -->
<!-- HUSHLINE — public documentation -->

<p align="center">
  <img src="docs/assets/hushline_header.png" width="100%" alt="Hushline — local command-output muting across four independent cores (Go, Rust, Python, Node)">
</p>

<p align="center">
  <a href="https://github.com/anulum/HushLine/actions/workflows/ci.yml"><img src="https://github.com/anulum/HushLine/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/anulum/HushLine/actions/workflows/pages.yml"><img src="https://github.com/anulum/HushLine/actions/workflows/pages.yml/badge.svg" alt="Pages"></a>
  <a href="https://github.com/anulum/HushLine/actions/workflows/scorecard.yml"><img src="https://github.com/anulum/HushLine/actions/workflows/scorecard.yml/badge.svg" alt="Scorecard"></a>
  <a href="https://securityscorecards.dev/viewer/?uri=github.com/anulum/HushLine"><img src="https://api.securityscorecards.dev/projects/github.com/anulum/HushLine/badge" alt="OpenSSF Scorecard"></a>
  <a href="https://www.bestpractices.dev/projects/13319"><img src="https://www.bestpractices.dev/projects/13319/badge" alt="OpenSSF Best Practices"></a>
  <a href="https://pypi.org/project/hushline/"><img src="https://img.shields.io/pypi/v/hushline.svg" alt="PyPI"></a>
  <a href="https://pypi.org/project/hushline/"><img src="https://img.shields.io/pypi/pyversions/hushline.svg" alt="Python"></a>
  <a href="https://codecov.io/gh/anulum/HushLine"><img src="https://codecov.io/gh/anulum/HushLine/branch/main/graph/badge.svg" alt="Coverage"></a>
  <a href="https://doi.org/10.5281/zenodo.20775432"><img src="https://zenodo.org/badge/DOI/10.5281/zenodo.20775432.svg" alt="DOI"></a>
  <a href="https://www.gnu.org/licenses/agpl-3.0"><img src="https://img.shields.io/badge/license-AGPL_3.0-blue.svg" alt="License: AGPL v3"></a>
  <a href="https://api.reuse.software/info/github.com/anulum/HushLine"><img src="https://api.reuse.software/badge/github.com/anulum/HushLine" alt="REUSE"></a>
  <img src="https://img.shields.io/badge/cores-Go_·_Rust_·_Python_·_Node-orange" alt="Cores">
</p>

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

## Use as a GitHub Action

Run any command through Hushline in a workflow so secrets (`sk-…`, `AKIA…`),
ANSI escapes, and noise are muted before they reach the CI log:

```yaml
- name: Plan with muted output
  uses: anulum/HushLine@v0
  with:
    command: terraform plan
```

Inputs: `command` (required), `max-lines`, `max-width`, `timeout`, `raw`,
`pipe-errors`, `working-directory`. The action builds the Go core from source, so
the runner needs Go (preinstalled on GitHub-hosted runners; otherwise add
`actions/setup-go` first).

## Polyglot cores

The same command contract is implemented by four independent cores. Each is a
standalone package — pick the one that fits your stack and deploy it without the
others.

| Core | Install | Notes |
|------|---------|-------|
| Go | `go install github.com/anulum/HushLine/cmd/hushline@latest` | reference implementation |
| Rust | `cargo install hushline` | fastest measured core |
| Python | `pip install hushline` | standard library only |
| Node | `npm install` in `cores/core-node` | standard library only |

All four produce byte-identical output. Measured per-core latency is in
[docs/benchmarks.md](docs/benchmarks.md); the core registry and contract are in
[cores/README.md](cores/README.md).

For deeper usage details, see:

- `docs/guide.md`
- `docs/development.md`
- `docs/release.md`
- `docs/benchmarks.md`

## Support

Hushline is free and open source under AGPL-3.0. If it saves you from leaking a
secret in a log, consider supporting its upkeep:

- GitHub Sponsors: https://github.com/sponsors/anulum
- Buy Me a Coffee: https://buymeacoffee.com/anulum

<p align="center">
  <a href="https://buymeacoffee.com/anulum"><img src="docs/assets/bmc_qr.png" width="160" alt="Buy Me a Coffee — buymeacoffee.com/anulum"></a>
</p>

A commercial licence is also available; contact protoscience@anulum.li.
