<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<!-- Commercial license available -->
<!-- © Concepts 1996–2026 Miroslav Šotek. All rights reserved. -->
<!-- © Code 2020–2026 Miroslav Šotek. All rights reserved. -->
<!-- ORCID: 0009-0009-3560-0851 -->
<!-- Contact: www.anulum.li | protoscience@anulum.li -->
<!-- HUSHLINE — public documentation -->

# Contributing to Hushline

Thank you for considering a contribution. Hushline keeps four independent
language cores (Go, Rust, Python, Node) behind one shared command contract, so
the contribution rules are designed to keep those cores in lockstep.

## Ground rules

- The Go core under `cmd/hushline` and `pkg/hushline` is the behaviour authority.
  Any change to observable behaviour must land in the Go core and be mirrored in
  every other core in the same change, with matching tests.
- Cores must stay independent. Never import or share runtime artefacts across
  `cores/<lang>/` folders.
- New or changed production code ships with tests in the same change. The
  coverage gate is high on purpose; do not lower it.
- Keep redaction and silence rules strict and reviewed. Hushline is a privacy
  boundary.

## Per-core local gates

Run the gates for every core you touched before opening a pull request.

Go (root):

```bash
go build -buildvcs=false ./...
go vet ./...
go test -race -covermode=atomic -coverprofile=/tmp/hushline_coverage.out ./...
bash tools/check_go_coverage.sh /tmp/hushline_coverage.out 95.0
test -z "$(gofmt -s -l .)"
```

Python (`cores/core-python`):

```bash
python -m pytest --cov=hushline_core --cov-report=term-missing
python -m build
```

Rust (`cores/core-rust`):

```bash
cargo fmt --check
cargo clippy -- -D warnings
cargo test
```

Node (`cores/core-node`):

```bash
npm ci
npx tsc --noEmit
node --test
```

## Pull request expectations

- One responsibility per pull request.
- Branch is up to date with `main`; history stays linear.
- All conversations resolved before merge.
- British English in prose and documentation.
- Every new file carries the SPDX header block.

## Reporting security issues

Do not open a public issue for vulnerabilities. Follow `SECURITY.md`.
