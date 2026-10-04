#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# HUSHLINE — negative controls for the dependency-lock audit

set -euo pipefail

# The lock audit must be able to fail. Each control lock pins one release with
# a published advisory and is audited with the same flags as the real lock.
# Both tools also exit non-zero when they cannot run, so the exit status alone
# proves nothing: the report must name the finding.

controls="tools/lock_audit_controls"
work="$(mktemp -d)"
trap 'rm -rf "${work}"' EXIT

mkdir "${work}/npm"
cp "${controls}/npm-advisory-control.package.json" "${work}/npm/package.json"
cp "${controls}/npm-advisory-control.lock.json" "${work}/npm/package-lock.json"
status=0
npm audit --package-lock-only --prefix "${work}/npm" --json >"${work}/npm-report.json" || status=$?
if [[ "${status}" -ne 1 ]]; then
  echo "npm audit exited ${status} on the control lock, expected 1" >&2
  exit 1
fi
node -e '
const report = JSON.parse(require("fs").readFileSync(process.argv[1], "utf8"));
if (!report.vulnerabilities || !report.vulnerabilities.lodash) {
  console.error("npm audit named no finding for the control lock");
  process.exit(1);
}
' "${work}/npm-report.json"

status=0
cargo audit --deny warnings --file "${controls}/cargo-advisory-control.lock" --json >"${work}/cargo-report.json" || status=$?
if [[ "${status}" -ne 1 ]]; then
  echo "cargo audit exited ${status} on the control lock, expected 1" >&2
  exit 1
fi
node -e '
const report = JSON.parse(require("fs").readFileSync(process.argv[1], "utf8"));
const findings = (report.vulnerabilities && report.vulnerabilities.list) || [];
if (!findings.some((finding) => finding.package.name === "time")) {
  console.error("cargo audit named no finding for the control lock");
  process.exit(1);
}
' "${work}/cargo-report.json"

status=0
python -m pip_audit --strict --require-hashes --disable-pip --progress-spinner=off -r "${controls}/pip-advisory-control.lock" -f json -o "${work}/pip-report.json" || status=$?
if [[ "${status}" -ne 1 ]]; then
  echo "pip-audit exited ${status} on the control lock, expected 1" >&2
  exit 1
fi
node -e '
const report = JSON.parse(require("fs").readFileSync(process.argv[1], "utf8"));
const named = report.dependencies.filter((entry) => entry.name === "urllib3" && entry.vulns.length > 0);
if (named.length !== 1) {
  console.error("pip-audit named no finding for the control lock");
  process.exit(1);
}
' "${work}/pip-report.json"

echo "all three control locks fail the audit with a named finding"
