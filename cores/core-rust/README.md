<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<!-- Commercial license available -->
<!-- © Concepts 1996–2026 Miroslav Šotek. All rights reserved. -->
<!-- © Code 2020–2026 Miroslav Šotek. All rights reserved. -->
<!-- ORCID: 0009-0009-3560-0851 -->
<!-- Contact: www.anulum.li | protoscience@anulum.li -->
<!-- HUSHLINE — public documentation -->

# Hushline Rust Core

Scaffold for a Rust rewrite that must follow the shared Hushline contract.

Planned files:

- `src/main.rs` command bootstrap
- `src/execution.rs` child process shaping
- `src/config.rs` profile loading + merge

Build command:

```bash
cd core-rust
cargo build
```

This core has no telemetry dependencies.
