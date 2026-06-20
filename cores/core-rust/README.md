<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<!-- Commercial license available -->
<!-- © Concepts 1996–2026 Miroslav Šotek. All rights reserved. -->
<!-- © Code 2020–2026 Miroslav Šotek. All rights reserved. -->
<!-- ORCID: 0009-0009-3560-0851 -->
<!-- Contact: www.anulum.li | protoscience@anulum.li -->
<!-- HUSHLINE — public documentation -->

# Hushline Rust Core

A standalone Rust implementation of the Hushline command contract. It is one of
four independent cores; it shares no runtime artefacts with the Go, Python, or
Node cores. Observable behaviour — default profile, configuration merge order,
redaction, ANSI stripping, byte-bounded line truncation, and exit codes —
matches the Go reference core exactly.

## Layout

- `src/main.rs` — console entry point.
- `src/engine.rs` — command dispatch and Go-style flag parsing.
- `src/config.rs` — profile defaults, strict JSON parsing, and merge.
- `src/muter.rs` — ANSI stripping, redaction, and silence rewrites.
- `src/pipeline.rs` — child execution and output streaming.

## Build

```bash
cd cores/core-rust
cargo build --release
./target/release/hushline version
```

## Test

```bash
cargo test
cargo clippy --all-targets -- -D warnings
cargo fmt --check
```

## Command surface

- `hushline mute [--raw] [--pipe-errors=BOOL] [--max-lines N] [--max-width N] [--timeout N] -- <command> ...`
- `hushline manifest init [--global|--local]`
- `hushline manifest show`
- `hushline permit [status|allow] [path]`
- `hushline version`

The binary target is named `hushline`. This core has no telemetry or network
dependencies.
