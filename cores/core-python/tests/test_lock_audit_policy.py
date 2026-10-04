# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# HUSHLINE — policy tests for the dependency-lock audit in CI

"""Every committed dependency lock has a blocking advisory audit in CI.

The ``lock-audit`` job in ``.github/workflows/ci.yml`` audits each lock on
every push and pull request to ``main``. These tests pin what can be weakened
without a visible failure: the exact audit command for each lock, the triggers,
the absence of any non-blocking marker, and the negative controls.

The workflow is read as text, so the tests need nothing outside the standard
library and run in the existing Python core job.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path, PurePosixPath

import pytest

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
CONTROL_SCRIPT = "tools/check_lock_audit_controls.sh"
CONTROL_DIR = "tools/lock_audit_controls/"
ROUTES = {
    "package-lock.json": "npm audit --package-lock-only --prefix {directory}",
    "Cargo.lock": "cargo audit --deny warnings --file {path}",
}
OTHER_LOCK_NAMES = frozenset(
    {
        "Pipfile.lock",
        "go.sum",
        "npm-shrinkwrap.json",
        "pnpm-lock.yaml",
        "poetry.lock",
        "uv.lock",
        "yarn.lock",
    }
)
NON_BLOCKING = (
    "continue-on-error",
    "if:",
    "needs:",
    "|| true",
    "--audit-level",
    "--omit",
    "--ignore",
    "--production",
)
HASHED_PIN = re.compile(r"^\s+--hash=sha256:[0-9a-f]{64}", re.MULTILINE)
JOB_HEADER = re.compile(r"^  [A-Za-z0-9_-]+:\s*$")


def _tracked() -> list[str]:
    listed = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, check=True
    )
    return [name for name in listed.stdout.decode("utf-8").split("\0") if name]


def _is_lock(name: str, text: str | None) -> bool:
    """Tell whether a tracked file is a dependency lock."""
    base = PurePosixPath(name).name
    if base in ROUTES or base in OTHER_LOCK_NAMES or base.endswith(".lock"):
        return True
    return text is not None and HASHED_PIN.search(text) is not None


def _locks() -> list[str]:
    """Return every tracked dependency lock, except the negative controls."""
    locks: list[str] = []
    for name in _tracked():
        path = ROOT / name
        if name.startswith(CONTROL_DIR) or not path.is_file():
            continue
        try:
            text: str | None = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = None
        if _is_lock(name, text):
            locks.append(name)
    return sorted(locks)


def _audit_command(lock: str) -> str:
    """Return the one admitted audit command for a lock."""
    path = PurePosixPath(lock)
    assert path.name in ROUTES, f"{lock}: no audit route is defined for this kind of lock"
    return ROUTES[path.name].format(path=lock, directory=path.parent)


def _job(text: str, name: str) -> list[str]:
    """Return the lines of one job in a workflow, without the job header."""
    lines = text.splitlines()
    start = lines.index(f"  {name}:")
    block: list[str] = []
    for line in lines[start + 1 :]:
        if JOB_HEADER.match(line):
            break
        block.append(line)
    return block


def _runs(block: list[str]) -> list[str]:
    """Return every ``run`` value of a job, whether or not the step has a name."""
    steps = [line.strip().removeprefix("- ") for line in block]
    return [step.removeprefix("run: ") for step in steps if step.startswith("run:")]


def _workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_the_workflow_runs_on_every_push_and_pull_request_to_main() -> None:
    text = _workflow()
    triggers = text[text.index("\non:\n") + 1 : text.index("\npermissions:")]
    assert triggers.split() == ["on:", "push:", "branches:", "-", "main", "pull_request:"]


def test_the_audit_job_has_no_non_blocking_marker() -> None:
    block = "\n".join(_job(_workflow(), "lock-audit"))
    for marker in NON_BLOCKING:
        assert marker not in block, marker
    assert "runs-on: ubuntu-latest" in block


def test_every_committed_lock_is_audited_by_its_pinned_command() -> None:
    locks = _locks()
    assert locks == ["cores/core-node/package-lock.json", "cores/core-rust/Cargo.lock"]
    expected = [_audit_command(lock) for lock in locks]
    assert _runs(_job(_workflow(), "lock-audit")) == [*expected, f"bash {CONTROL_SCRIPT}"]


def test_a_lock_without_an_audit_route_is_refused() -> None:
    assert _is_lock("gateway/go.sum", None)
    assert _is_lock("requirements.txt", "requests==2.0 \\\n    --hash=sha256:" + "0" * 64 + "\n")
    assert not _is_lock("requirements.txt", "requests>=2\n")
    assert not _is_lock("README.md", None)
    with pytest.raises(AssertionError, match="no audit route"):
        _audit_command("gateway/go.sum")


def test_the_job_reader_stops_at_the_next_job() -> None:
    text = (
        "jobs:\n  first:\n    steps:\n      - run: one\n  second:\n    steps:\n      - run: two\n"
    )
    assert _runs(_job(text, "first")) == ["one"]
    assert _runs(_job(text, "second")) == ["two"]
    with pytest.raises(ValueError, match="is not in list"):
        _job(text, "third")


def test_the_controls_use_the_audited_commands_and_read_the_report() -> None:
    script = (ROOT / CONTROL_SCRIPT).read_text(encoding="utf-8")
    assert 'npm audit --package-lock-only --prefix "${work}/npm" --json' in script
    cargo = 'cargo audit --deny warnings --file "${controls}/cargo-advisory-control.lock" --json'
    assert cargo in script
    assert script.count('if [[ "${status}" -ne 1 ]]; then') == 2
    assert "report.vulnerabilities.lodash" in script
    assert 'finding.package.name === "time"' in script
    assert "|| true" not in script


def test_the_control_locks_pin_one_release_with_a_published_advisory() -> None:
    tracked = set(_tracked())
    names = [
        "cargo-advisory-control.lock",
        "npm-advisory-control.lock.json",
        "npm-advisory-control.package.json",
    ]
    assert sorted(name for name in tracked if name.startswith(CONTROL_DIR)) == [
        CONTROL_DIR + name for name in names
    ]
    lock = json.loads((ROOT / CONTROL_DIR / names[1]).read_text(encoding="utf-8"))
    assert lock["packages"]["node_modules/lodash"]["version"] == "4.17.15"
    assert set(lock["packages"]) == {"", "node_modules/lodash"}
    cargo = (ROOT / CONTROL_DIR / names[0]).read_text(encoding="utf-8")
    assert re.findall(r'^name = "(.+)"$', cargo, re.MULTILINE) == ["advisory-control", "time"]
    assert 'version = "0.1.43"' in cargo
    # The controls are only ever audited: no workflow names them except through the script.
    assert CONTROL_DIR not in _workflow()
