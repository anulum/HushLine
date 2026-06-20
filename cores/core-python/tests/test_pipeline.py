# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# HUSHLINE — Python core pipeline tests

"""Child execution: streaming, truncation, stderr handling, and exit codes."""

from __future__ import annotations

import io

from hushline_core import pipeline
from hushline_core.config import Config, default_profile
from hushline_core.muter import compose


def _run(command, args, muter=None, max_lines=2000, preserve_errors=True, timeout=0):
    out, err = io.StringIO(), io.StringIO()
    code = pipeline.through(
        command, args, out, err, muter, max_lines, preserve_errors, timeout
    )
    return code, out.getvalue(), err.getvalue()


def test_plain_stdout_passthrough() -> None:
    code, out, err = _run("printf", ["one\\ntwo\\n"])
    assert code == 0
    assert out == "one\ntwo\n"
    assert err == ""


def test_stdout_is_redacted() -> None:
    muter = compose(default_profile())
    secret = "sk-" + "abcdefghijklmnopqrstuvwxyz"
    code, out, _ = _run("printf", [f"{secret}\\n"], muter=muter)
    assert code == 0
    assert secret not in out
    assert "***" in out


def test_max_lines_emits_single_truncation_marker() -> None:
    code, out, _ = _run("printf", ["a\\nb\\nc\\nd\\n"], max_lines=2)
    assert code == 0
    assert out.count("[output truncated]") == 1
    assert out.splitlines() == ["a", "b", "[output truncated]"]


def test_stderr_passes_through_when_preserved() -> None:
    code, _, err = _run("sh", ["-c", "printf oops 1>&2"], preserve_errors=True)
    assert code == 0
    assert "oops" in err


def test_stderr_discarded_when_not_preserved() -> None:
    code, _, err = _run("sh", ["-c", "printf oops 1>&2"], preserve_errors=False)
    assert code == 0
    assert err == ""


def test_exit_code_is_propagated() -> None:
    code, _, _ = _run("sh", ["-c", "exit 7"])
    assert code == 7


def test_missing_command_is_start_failure() -> None:
    code, _, _ = _run("hushline-no-such-binary-xyz", [])
    assert code == 2


def test_signal_kill_maps_to_one() -> None:
    code, _, _ = _run("sh", ["-c", "kill -9 $$"])
    assert code == 1


def test_timeout_maps_to_124() -> None:
    code, _, _ = _run("sh", ["-c", "sleep 5"], timeout=1)
    assert code == 124


def test_no_muter_leaves_output_raw() -> None:
    secret = "sk-" + "abcdefghijklmnopqrstuvwxyz"
    code, out, _ = _run("printf", [f"{secret}\\n"], muter=None)
    assert code == 0
    assert secret in out


def test_stderr_truncation_is_unbounded_even_with_max_lines() -> None:
    # Stderr always streams with max_lines=0, so no truncation marker appears.
    muter = compose(Config(strip_ansi=False, mask_patterns=(), quiet_rules=()))
    code, _, err = _run(
        "sh",
        ["-c", "for i in 1 2 3 4 5; do echo line$i 1>&2; done"],
        muter=muter,
        max_lines=1,
        preserve_errors=True,
    )
    assert code == 0
    assert "[output truncated]" not in err
    assert err.count("line") == 5
