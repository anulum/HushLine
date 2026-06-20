# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# HUSHLINE — Python core entry-point tests

"""The console-script entry point and the package version export."""

from __future__ import annotations

import hushline_core
from hushline_core.__main__ import main


def test_main_returns_exit_code(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["hushline", "version"])
    assert main() == 0
    assert "hushline" in capsys.readouterr().out


def test_main_unknown_command_exit_code(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["hushline", "definitely-not-a-command"])
    assert main() == 1


def test_package_exports_version_and_run() -> None:
    assert hushline_core.__version__ == "0.1.5"
    assert callable(hushline_core.run)
