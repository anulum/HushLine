#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# HUSHLINE — Go coverage threshold guard

set -euo pipefail

coverage_file="${1:?coverage profile path required}"
threshold="${2:-95.0}"

total="$(go tool cover -func="${coverage_file}" | awk '/^total:/ { sub(/%/, "", $3); print $3 }')"
if [[ -z "${total}" ]]; then
  echo "could not read total coverage from ${coverage_file}" >&2
  exit 1
fi

awk -v total="${total}" -v threshold="${threshold}" 'BEGIN {
  if (total + 0 < threshold + 0) {
    printf "go coverage %.1f%% is below required %.1f%%\n", total, threshold > "/dev/stderr"
    exit 1
  }
  printf "go coverage %.1f%% meets required %.1f%%\n", total, threshold
}'
