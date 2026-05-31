#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# HUSHLINE — Go test-surface guard

set -euo pipefail

if ! find internal cmd -name '*_test.go' -print -quit | grep -q .; then
  echo "no Go test files found under internal/ or cmd/" >&2
  exit 1
fi
