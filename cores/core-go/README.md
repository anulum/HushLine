<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<!-- Commercial license available -->
<!-- © Concepts 1996–2026 Miroslav Šotek. All rights reserved. -->
<!-- © Code 2020–2026 Miroslav Šotek. All rights reserved. -->
<!-- ORCID: 0009-0009-3560-0851 -->
<!-- Contact: www.anulum.li | protoscience@anulum.li -->
<!-- HUSHLINE — public documentation -->

# Hushline Go Core

This is the canonical Go reference core boundary.

Planned layout:

- `src/` — command and engine implementation (to be migrated from root `cmd/` and `pkg/hushline/`).
- `go.mod` — explicit module definition for this core.
- `build.sh` — local build script.

Build command (placeholder):

```bash
cd core-go
go build ./...
```

This folder is currently scaffold-only until migration is approved.
