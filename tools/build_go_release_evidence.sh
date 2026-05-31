#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# HUSHLINE — local Go release evidence builder

set -euo pipefail

version="${1:-dev}"
root="$(git rev-parse --show-toplevel)"
release_dir="/tmp/hushline-release-evidence/${version}"
manifest="${release_dir}/release_manifest.md"
tmp_binary="/tmp/hushline-${version}-linux-amd64.bin"
sbom="${release_dir}/sbom.cdx.json"

mkdir -p "${release_dir}"

go build -buildvcs=false -trimpath -ldflags="-s -w" -o "${tmp_binary}" ./cmd/hushline
bash "${root}/tools/generate_go_sbom.sh" "${version}" "${sbom}"
binary_sha="$(sha256sum "${tmp_binary}" | awk '{ print $1 }')"
go_mod_sha="$(sha256sum "${root}/go.mod" | awk '{ print $1 }')"
sbom_sha="$(sha256sum "${sbom}" | awk '{ print $1 }')"
commit="$(git rev-parse HEAD)"
dirty="false"
if ! git diff --quiet || ! git diff --cached --quiet; then
  dirty="true"
fi

{
  echo "# HushLine Go Release Evidence"
  echo
  echo "- Version: \`${version}\`"
  echo "- Commit: \`${commit}\`"
  echo "- Dirty worktree: \`${dirty}\`"
  echo "- Built at UTC: \`$(date -u +%Y-%m-%dT%H:%M:%SZ)\`"
  echo "- Go toolchain: \`$(go version)\`"
  echo
  echo "| Artifact | Path | SHA256 |"
  echo "|---|---|---|"
  echo "| Go module | \`go.mod\` | \`${go_mod_sha}\` |"
  echo "| CycloneDX SBOM | \`${sbom}\` | \`${sbom_sha}\` |"
  echo "| CLI binary | \`${tmp_binary}\` | \`${binary_sha}\` |"
} > "${manifest}"

sha256sum "${tmp_binary}" > "${release_dir}/hushline-linux-amd64.sha256"
sha256sum "${sbom}" > "${release_dir}/sbom.cdx.json.sha256"
echo "release evidence written: ${release_dir}"
