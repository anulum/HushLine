<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<!-- Commercial license available -->
<!-- © Concepts 1996–2026 Miroslav Šotek. All rights reserved. -->
<!-- © Code 2020–2026 Miroslav Šotek. All rights reserved. -->
<!-- ORCID: 0009-0009-3560-0851 -->
<!-- Contact: www.anulum.li | protoscience@anulum.li -->
<!-- HUSHLINE — public documentation -->

# Hushline Language Integration Bindings

This folder is reserved for alternate language implementations that preserve the
same CLI and integration contract.

## Actual implementation roots

Use separate roots under `cores/` to avoid any implementation mixing:

- `cores/core-go/` - canonical reference implementation
- `cores/core-rust/` - low-latency, low-overhead rewrite
- `cores/core-python/` - scripting and orchestration-friendly rewrite
- `cores/core-node/` - JS/TS runtime embedding rewrite

## Contract requirement

All language variants must satisfy:

- identical command-line surface (`mute`, `manifest`, `permit`, `version`)
- same profile merge and redaction semantics
- same exit code behavior and stderr/stdout handling
- same enterprise hardening posture:
  - no telemetry/analytics
  - no network reporting
  - evidence updates for each control family

Deploy only one active core at a time by pointing build/packaging explicitly at one
`cores/core-*` directory.
