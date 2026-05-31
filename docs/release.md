<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<!-- Commercial license available -->
<!-- © Concepts 1996–2026 Miroslav Šotek. All rights reserved. -->
<!-- © Code 2020–2026 Miroslav Šotek. All rights reserved. -->
<!-- ORCID: 0009-0009-3560-0851 -->
<!-- Contact: www.anulum.li | protoscience@anulum.li -->
<!-- HUSHLINE — public documentation -->

# Release evidence

Hushline releases must be traceable to a clean commit on protected `main`.

## Release prerequisites

- `main` is protected.
- `ci`, `CodeQL`, and `github-pages` runs are green on the release commit.
- Open Dependabot alerts: zero.
- Open secret-scanning alerts: zero.
- Open CodeQL alerts: zero.
- Go coverage meets the configured 95 percent gate.
- The working tree used to build release artefacts is clean.

## Build evidence

Generate local release evidence with:

```bash
bash tools/build_go_release_evidence.sh <version>
```

The script produces:

- A trimmed Linux AMD64 CLI binary.
- A CycloneDX SBOM.
- SHA256 checksums.
- A release manifest with commit, toolchain, build time, and artefact hashes.

Evidence is written under `/tmp/hushline-release-evidence/<version>`.

## Publication checklist

Before publishing a GitHub release:

1. Confirm the release commit matches `origin/main`.
2. Confirm the release evidence manifest reports `Dirty worktree: false`.
3. Upload the binary, SBOM, checksums, and release manifest.
4. Record the release tag, commit, and artefact hashes in the release notes.

## Python package publication

The Python package workflow publishes on manual dispatch or release tags that
start with `python-core-v`. General Hushline CLI releases do not publish Python
distributions.

It requires `PYPI_API_TOKEN` to be configured as a repository secret. Existing
distribution files are skipped so a repeat publication attempt does not fail
because PyPI already has the same immutable artefact.
