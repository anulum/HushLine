<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<!-- Commercial license available -->
<!-- © Concepts 1996–2026 Miroslav Šotek. All rights reserved. -->
<!-- © Code 2020–2026 Miroslav Šotek. All rights reserved. -->
<!-- ORCID: 0009-0009-3560-0851 -->
<!-- Contact: www.anulum.li | protoscience@anulum.li -->
<!-- HUSHLINE — public documentation -->

# Hushline Go Core

This is the canonical Go reference core. Its implementation lives at the
repository root and is the behaviour authority for every other core:

- `cmd/hushline/` — command bootstrap.
- `pkg/hushline/{config,muter,pipeline,engine,version}` — engine implementation.

Build and test from the repository root:

```bash
go build -buildvcs=false ./...
go test -race ./...
```

`build.sh` here is a thin convenience wrapper. The Go core is not duplicated
under `core-go/src/` so that Go behaviour has a single source of truth.
