<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<!-- Commercial license available -->
<!-- © Concepts 1996–2026 Miroslav Šotek. All rights reserved. -->
<!-- © Code 2020–2026 Miroslav Šotek. All rights reserved. -->
<!-- ORCID: 0009-0009-3560-0851 -->
<!-- Contact: www.anulum.li | protoscience@anulum.li -->
<!-- HUSHLINE — public documentation -->

# Hushline Node Core

A standalone Node/TypeScript implementation of the Hushline command contract. It
is one of four independent cores; it shares no runtime artefacts with the Go,
Rust, or Python cores and pulls in no runtime dependencies (standard library
only). Observable behaviour — default profile, configuration merge order,
redaction, ANSI stripping, byte-bounded line truncation, and exit codes —
matches the Go reference core exactly.

## Layout

- `src/cli.ts` — console entry point.
- `src/engine.ts` — command dispatch and Go-style flag parsing.
- `src/config.ts` — profile defaults, strict JSON parsing, and merge.
- `src/muter.ts` — ANSI stripping, redaction, and silence rewrites.
- `src/pipeline.ts` — child execution and output streaming.

## Build and run

```bash
cd cores/core-node
npm install
npm run build
node dist/src/cli.js version
```

## Test

```bash
npm test
```

`npm test` compiles the TypeScript and runs the `node --test` suite.

## Command surface

- `hushline mute [--raw] [--pipe-errors=BOOL] [--max-lines N] [--max-width N] [--timeout N] -- <command> ...`
- `hushline manifest init [--global|--local]`
- `hushline manifest show`
- `hushline permit [status|allow] [path]`
- `hushline version`

The `bin` entry installs the command as `hushline`. No telemetry or network
access is present.
