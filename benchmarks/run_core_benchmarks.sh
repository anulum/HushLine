#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# HUSHLINE — build every core and run the side-by-side benchmark

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/.." && pwd)"
BIN="${SCRIPT_DIR}/bin"
REPS="${1:-7}"
WORKLOAD_LINES="${WORKLOAD_LINES:-20000}"

mkdir -p "${BIN}" "${SCRIPT_DIR}/results"

echo "==> building Go core"
( cd "${REPO}" && go build -buildvcs=false -o "${BIN}/hushline-go" ./cmd/hushline )

echo "==> building Rust core (release)"
( cd "${REPO}/cores/core-rust" && cargo build --release --quiet )
cp "${REPO}/cores/core-rust/target/release/hushline" "${BIN}/hushline-rust"

echo "==> building Node core"
( cd "${REPO}/cores/core-node" && npm run build --silent )

echo "==> generating workload (${WORKLOAD_LINES} lines)"
WORKLOAD_LINES="${WORKLOAD_LINES}" python3 - "${BIN}/workload.txt" <<'PY'
import os, sys

target = sys.argv[1]
lines = int(os.environ["WORKLOAD_LINES"])
ansi = "\x1b[31m"
reset = "\x1b[0m"
with open(target, "w", encoding="utf-8") as handle:
    for i in range(lines):
        kind = i % 5
        if kind == 0:
            handle.write(f"{ansi}build step {i} completed{reset}   with   padding\n")
        elif kind == 1:
            handle.write(f"token sk-abcdefghijklmnopqrstuvwxyz{i % 10} emitted at {i}\n")
        elif kind == 2:
            handle.write(f"aws key AKIA{i % 10:0>16} found in log line {i}\n")
        elif kind == 3:
            handle.write(f"plain informational line number {i} with trailing words\n")
        else:
            handle.write(f"warning:  double  spaced  diagnostic  {i}\n")
PY

echo "==> measuring (${REPS} repetitions per core)"
python3 "${SCRIPT_DIR}/measure.py" "${REPS}"
