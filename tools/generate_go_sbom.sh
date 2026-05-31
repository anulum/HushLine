#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# HUSHLINE — Go module CycloneDX SBOM generator

set -euo pipefail

version="${1:-dev}"
out="${2:-/tmp/hushline-release-evidence/${version}/sbom.cdx.json}"
root="$(git rev-parse --show-toplevel)"
commit="$(git rev-parse HEAD)"
modules_json="$(mktemp)"
trap 'rm -f "${modules_json}"' EXIT

mkdir -p "$(dirname "${out}")"

go list -m -json all > "${modules_json}"

python3 - "${version}" "${commit}" "${out}" "${modules_json}" <<'PY'
import json
import sys
from pathlib import Path

version = sys.argv[1]
commit = sys.argv[2]
out = Path(sys.argv[3])
modules_json = Path(sys.argv[4])
raw = modules_json.read_text(encoding="utf-8").strip()

modules = []
decoder = json.JSONDecoder()
idx = 0
while idx < len(raw):
    obj, end = decoder.raw_decode(raw[idx:])
    modules.append(obj)
    idx += end
    while idx < len(raw) and raw[idx].isspace():
        idx += 1

if not modules:
    raise SystemExit("go list returned no modules")

root_module = modules[0]
root_name = root_module["Path"]

components = []
for module in modules[1:]:
    module_version = module.get("Version", "")
    component = {
        "type": "library",
        "name": module["Path"],
        "version": module_version,
        "bom-ref": f"pkg:golang/{module['Path']}@{module_version}" if module_version else f"pkg:golang/{module['Path']}",
        "purl": f"pkg:golang/{module['Path']}@{module_version}" if module_version else f"pkg:golang/{module['Path']}",
    }
    if "Replace" in module:
        component["properties"] = [
            {"name": "go:replace", "value": module["Replace"]["Path"]},
        ]
    components.append(component)

sbom = {
    "bomFormat": "CycloneDX",
    "specVersion": "1.5",
    "version": 1,
    "metadata": {
        "component": {
            "type": "application",
            "name": root_name,
            "version": version,
            "bom-ref": f"pkg:golang/{root_name}@{version}",
            "purl": f"pkg:golang/{root_name}@{version}",
            "properties": [
                {"name": "vcs:commit", "value": commit},
            ],
        }
    },
    "components": components,
}

out.write_text(json.dumps(sbom, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

echo "go sbom written: ${out}"
