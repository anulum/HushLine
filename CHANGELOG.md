<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<!-- Commercial license available -->
<!-- © Concepts 1996–2026 Miroslav Šotek. All rights reserved. -->
<!-- © Code 2020–2026 Miroslav Šotek. All rights reserved. -->
<!-- ORCID: 0009-0009-3560-0851 -->
<!-- Contact: www.anulum.li | protoscience@anulum.li -->
<!-- HUSHLINE — public documentation -->

# Changelog

All notable changes to this project are documented here. The format follows
Keep a Changelog, and the project adheres to Semantic Versioning.

## [Unreleased]

### Added

- Python core (`hushline_core`): full implementation of the command contract,
  stdlib only, with a complete test suite.
- Rust core: full implementation of the command contract with unit and
  integration tests.
- Node core: full implementation of the command contract with a `node --test`
  suite.
- Side-by-side core benchmarks with a committed results file.
- `LICENSE`, `LICENSES/AGPL-3.0-or-later.txt`, and `REUSE.toml` for REUSE
  compliance.
- `CITATION.cff`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, and this changelog.
- OpenSSF Scorecard workflow and README status badges.
- A blocking advisory audit of every committed dependency lock in CI
  (`lock-audit` job: `npm audit` for the Node core, `cargo audit` for the Rust
  core, `pip-audit` for the Python tooling locks), with control locks that must
  fail the audit and a policy test that pins the audit commands.
- Hash-locked Python tooling for CI and publishing
  (`cores/core-python/requirements/`), and a Dependabot configuration.

### Changed

- Python core packaging now builds a non-empty distribution containing
  `hushline_core`; the published wheel carries the implementation.
- README and developer documentation no longer reference internal layout.
- Every external GitHub Action is pinned by commit hash; a policy test refuses
  tag and branch references and `pip install` without hashes.
- Rust core lock: `regex` 1.13.1, `serde` 1.0.229, `serde_json` 1.0.151.
- Workflows: every pinned action updated to its current release (checkout
  7.0.1, setup-go 7.0.0, setup-node 7.0.0, setup-python 7.0.0, upload-artifact
  7.0.1, codecov-action 7.1.1, scorecard-action 2.4.4, codeql-action 4.38.2,
  gh-action-pypi-publish 1.14.2, install-action 2.87.24).

## [0.1.0] - 2026-05-31

### Added

- Go reference core: `mute`, `manifest`, `permit`, and `version` commands.
- Default profile with ANSI stripping, secret redaction, and output bounds.
- GitHub release with binary, SBOM, and checksums.
- Production-readiness documentation and release runbooks.
