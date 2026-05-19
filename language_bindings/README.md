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
