<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<!-- Commercial license available -->
<!-- © Concepts 1996–2026 Miroslav Šotek. All rights reserved. -->
<!-- © Code 2020–2026 Miroslav Šotek. All rights reserved. -->
<!-- ORCID: 0009-0009-3560-0851 -->
<!-- Contact: www.anulum.li | protoscience@anulum.li -->
<!-- HUSHLINE — public documentation -->

# Development and verification

Every change must keep the public repository free of private planning material,
generated build trees, local virtual environments, and local permit state.

## Required local gates

Run these checks before proposing a change:

```bash
go build -buildvcs=false ./...
go vet ./...
go test -race -covermode=atomic -coverprofile=/tmp/hushline_coverage.out ./...
bash tools/check_go_coverage.sh /tmp/hushline_coverage.out 95.0
bash tools/check_go_test_files.sh
test -z "$(gofmt -s -l .)"
```

The Go coverage gate is intentionally high. New production code must carry
behavioural tests in the same change unless the change is documentation-only.

## Required remote gates

Protected `main` requires:

- `test-and-build` status check.
- Strict branch synchronisation before merge.
- One approving review.
- Resolved conversations.
- Linear history.
- No force pushes.
- No branch deletions.
- Admin enforcement.

Security checks expected on `main`:

- CodeQL default setup enabled.
- Dependabot alerts reviewed.
- Secret scanning enabled.
- Secret scanning push protection enabled.

## Repository hygiene

The public tree must not contain:

- Local virtual environments.
- Build output directories.
- Generated package metadata.
- Local permit marker directories.
- Private planning or handover material.

Private operational notes belong outside the public tree.
