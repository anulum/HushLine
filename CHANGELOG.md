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

### Changed

- Python core packaging now builds a non-empty distribution containing
  `hushline_core`; the published wheel carries the implementation.
- README and developer documentation no longer reference internal layout.

## [0.1.0] - 2026-05-31

### Added

- Go reference core: `mute`, `manifest`, `permit`, and `version` commands.
- Default profile with ANSI stripping, secret redaction, and output bounds.
- GitHub release with binary, SBOM, and checksums.
- Production-readiness documentation and release runbooks.
