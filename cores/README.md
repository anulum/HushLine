<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<!-- Commercial license available -->
<!-- © Concepts 1996–2026 Miroslav Šotek. All rights reserved. -->
<!-- © Code 2020–2026 Miroslav Šotek. All rights reserved. -->
<!-- ORCID: 0009-0009-3560-0851 -->
<!-- Contact: www.anulum.li | protoscience@anulum.li -->
<!-- HUSHLINE — public documentation -->

# Hushline Core Registry

The `HUSHLINE` repository keeps each implementation in its own isolated core
to avoid cross-language mixing.

## Active core map

- `core-go/` — Go reference implementation; the behaviour authority lives at the
  repository root (`cmd/hushline`, `pkg/hushline`).
- `core-rust/` — Rust implementation (regex + serde), built as the `hushline` binary.
- `core-python/` — Python implementation (`hushline_core`), published to PyPI as `hushline`.
- `core-node/` — Node/TypeScript implementation, `hushline` bin target.

Each core is a standalone package: pick one language and deploy it without the
others. All four pass the same contract test suite; measured per-core latency is
in the benchmark table in `docs/guide.md`.

## Core contract

All cores must implement the same command contract:

- `hushline mute -- <command> [args...]`
- `hushline manifest init [--global|--local]`
- `hushline manifest show`
- `hushline permit [status|allow] [path]`
- `hushline version`

and the same hardening constraints:

- no telemetry
- no network reporting
- deterministic output shaping rules
- permit gate behavior

## Migration rule

- Never import or mix runtime artifacts across core folders.
- A deployment must point to exactly one core folder.
- The build target, package config, and operational docs must reference one core
  explicitly.
