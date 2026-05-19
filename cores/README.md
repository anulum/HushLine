# Hushline Core Registry

The `HUSHLINE` repository keeps each implementation in its own isolated core
to avoid cross-language mixing.

## Active core map

- `core-go/` — Go reference implementation (current behavior source)
- `core-rust/` — Rust isolation candidate
- `core-python/` — Python isolation candidate
- `core-node/` — Node/TypeScript isolation candidate

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
