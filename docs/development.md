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

## Dependency-lock audit

CI audits every committed dependency lock against its advisory database on each
push and pull request to `main` (`lock-audit` job). A finding fails the job;
there is no severity threshold.

```bash
npm audit --package-lock-only --prefix cores/core-node
python -m pip_audit --strict --require-hashes --disable-pip --progress-spinner=off -r cores/core-python/requirements/audit.txt
python -m pip_audit --strict --require-hashes --disable-pip --progress-spinner=off -r cores/core-python/requirements/dev.txt
cargo audit --deny warnings --file cores/core-rust/Cargo.lock
bash tools/check_lock_audit_controls.sh
```

The last command audits three control locks under `tools/lock_audit_controls/`,
each pinning one release with a published advisory. Every audit must fail and
its report must name the finding. The audit tools also exit non-zero when they
cannot run, so the exit status alone is not accepted.

`pip-audit` skips a pin whose environment marker is false on the interpreter it
runs on, and still exits 0. The Python locks are compiled for one interpreter
and platform and hold no marked pin; the policy test fails if one appears.

`cores/core-python/tests/test_lock_audit_policy.py` pins the audit commands. It
fails when a committed lock has no audit step, when a command changes, or when
a lock of a kind without an audit route (for example `go.sum`) is committed. To
add a lock, add its audit step and its route in that test in the same change.

## Pinned workflow code

Every external action in `.github/workflows/` is referenced by a full commit
hash, with the version in a trailing comment. Every `pip install` in a workflow
installs from a hash-locked file under `cores/core-python/requirements/` with
`--require-hashes`. `cores/core-python/tests/test_workflow_pins.py` fails on a
tag or branch reference and on an install without hashes.

The locks are regenerated with the command in the first line of each file.
`.github/dependabot.yml` proposes updates weekly; an update lands as a normal
reviewed change.

## Required remote gates

Protected `main` requires:

- The `core-go`, `core-python`, `core-rust`, `core-node` and `lock-audit`
  status checks.
- Strict branch synchronisation before merge.
- One approving review.
- Resolved conversations.
- Linear history.
- No force pushes.
- No branch deletions.

A repository administrator may push to `main` directly. A failing run on the
pushed head is fixed forward before any further work.

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
