<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<!-- Commercial license available -->
<!-- © Concepts 1996–2026 Miroslav Šotek. All rights reserved. -->
<!-- © Code 2020–2026 Miroslav Šotek. All rights reserved. -->
<!-- ORCID: 0009-0009-3560-0851 -->
<!-- Contact: www.anulum.li | protoscience@anulum.li -->
<!-- HUSHLINE — public documentation -->

# Hushline usage guide

## Core behavior

`mute` is the command execution entry point. It accepts a child command after
`--` and rewrites each output line using compiled redaction and shaping rules.

### Output filters

- ANSI control codes are removed by default.
- Patterns from `mask_patterns` are replaced with `***`.
- `silence_rules` are regex replacement operations applied in configured order.
- `line_width` truncates lines above the configured maximum.
- `max_lines` truncates output stream after the configured number of lines.

### Error path behavior

If `preserve_errors` is true, stderr is passed through the same line muting pipeline.
If false, stderr is consumed but dropped.

### Permit enforcement

When `require_permit` is true, command execution is blocked unless the current
directory has `.hushline/permitted` present.

`permit allow` writes the marker at the provided path or current directory by
default. `permit status` reports marker presence.

## Runtime paths

Global profile:

`$XDG_CONFIG_HOME/hushline/profile.json`

Local profile:

`<cwd>/.hushline/profile.json`

Permit marker:

`<cwd>/.hushline/permitted`

## CLI options reference

`hushline mute`

- `--max-lines <N>`
- `--max-width <N>`
- `--raw` to bypass all muting
- `--pipe-errors <bool>` to route stderr through the same muter
- `--timeout <seconds>`

`hushline manifest`

- `init [--global|--local]` writes defaults to target profile.
- `show` prints global and local profile locations.

`hushline permit`

- `status` checks permit marker state.
- `allow [path]` writes permit marker at `<path>` or current directory.

## Minimal integration pattern

```bash
hushline mute --timeout 30 --max-lines 1500 -- /usr/bin/python3 -m example.task
```

Use this command shape wherever prompt-chain stages execute shell commands.
