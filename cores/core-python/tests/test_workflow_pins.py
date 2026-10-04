# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# HUSHLINE — policy tests for pinned actions and hash-locked installs in CI

"""Workflows run only pinned code.

Every external action is referenced by a full commit hash with its version in a
trailing comment, and every ``pip install`` in a workflow installs from a
hash-locked requirements file. A tag or branch reference can be moved to other
code after review; a commit hash cannot.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PINNED = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40} # \S+$")


def _workflow_files() -> list[str]:
    listed = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", ".github/workflows", "action.yml"],
        capture_output=True,
        check=True,
    )
    return sorted(name for name in listed.stdout.decode("utf-8").split("\0") if name)


def _values(text: str, key: str) -> list[str]:
    """Return the value of every ``key:`` line, with or without a list dash."""
    values: list[str] = []
    for line in text.splitlines():
        stripped = line.strip().removeprefix("- ")
        if stripped.startswith(f"{key}: "):
            values.append(stripped.removeprefix(f"{key}: "))
    return values


def _unpinned(text: str) -> list[str]:
    """Return every action reference that is neither local nor pinned by commit."""
    return [
        value
        for value in _values(text, "uses")
        if not value.startswith("./") and not PINNED.match(value)
    ]


def test_every_external_action_is_pinned_by_commit() -> None:
    files = _workflow_files()
    assert ".github/workflows/ci.yml" in files
    assert "action.yml" in files
    for name in files:
        assert _unpinned((ROOT / name).read_text(encoding="utf-8")) == [], name


def test_a_tag_or_branch_reference_is_reported() -> None:
    text = (
        "steps:\n"
        "  - uses: actions/checkout@v6\n"
        "  - name: toolchain\n"
        "    uses: dtolnay/rust-toolchain@stable\n"
        "  - uses: ./\n"
        "  - uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6.1.0\n"
        "  - uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803\n"
    )
    assert _unpinned(text) == [
        "actions/checkout@v6",
        "dtolnay/rust-toolchain@stable",
        "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803",
    ]


def test_every_pip_install_in_a_workflow_requires_hashes() -> None:
    installs: list[str] = []
    for name in _workflow_files():
        text = (ROOT / name).read_text(encoding="utf-8")
        # Every line counts, so an install inside a multi-line script is seen as well.
        installs += [line.strip() for line in text.splitlines() if "pip install" in line]
    assert len(installs) == 3
    for run in installs:
        assert "--require-hashes -r " in run, run
        assert "--upgrade" not in run, run
