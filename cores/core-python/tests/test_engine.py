# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# HUSHLINE — Python core engine tests

"""Command dispatch, flag parsing, and the permit/redaction gates."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from hushline_core import config
from hushline_core import engine


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return tmp_path / "work"


def call(argv, cwd):
    out, err = io.StringIO(), io.StringIO()
    code = engine.run(argv, stdout=out, stderr=err, cwd=str(cwd))
    return code, out.getvalue(), err.getvalue()


def _write_local_profile(work: Path, payload: object) -> None:
    target = work / ".hushline" / "profile.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload), encoding="utf-8")


@pytest.mark.parametrize("argv", [[], ["help"], ["-h"], ["--help"]])
def test_help_variants(argv, workspace) -> None:
    code, out, _ = call(argv, workspace)
    assert code == 0
    assert "local command output shaping utility" in out


def test_version(workspace) -> None:
    code, out, _ = call(["version"], workspace)
    assert code == 0
    assert out == f"hushline {engine.VERSION}\n"


def test_unknown_command(workspace) -> None:
    code, out, _ = call(["nope"], workspace)
    assert code == 1
    assert "unknown command: nope" in out


def test_default_streams_and_cwd(capsys) -> None:
    # Exercises the stdout=None / cwd=None default branches.
    assert engine.run(["version"]) == 0
    assert "hushline" in capsys.readouterr().out


def test_manifest_show(workspace) -> None:
    code, out, _ = call(["manifest"], workspace)
    assert code == 0
    assert "global profile:" in out
    assert "local profile:" in out
    assert call(["manifest", "show"], workspace)[1] == out


def test_manifest_init_global(workspace) -> None:
    code, out, _ = call(["manifest", "init", "--global"], workspace)
    assert code == 0
    assert "profile written" in out
    assert Path(config.global_profile_path()).exists()


def test_manifest_init_local(workspace) -> None:
    code, out, _ = call(["manifest", "init", "--local"], workspace)
    assert code == 0
    assert Path(config.local_profile_path(str(workspace))).exists()


def test_manifest_init_default_is_global(workspace) -> None:
    call(["manifest", "init"], workspace)
    assert Path(config.global_profile_path()).exists()
    assert not Path(config.local_profile_path(str(workspace))).exists()


def test_manifest_init_both_flags_is_global(workspace) -> None:
    call(["manifest", "init", "--global", "--local"], workspace)
    assert Path(config.global_profile_path()).exists()
    assert not Path(config.local_profile_path(str(workspace))).exists()


def test_manifest_unknown_action(workspace) -> None:
    code, _, err = call(["manifest", "wat"], workspace)
    assert code == 2
    assert "unknown action" in err


def test_manifest_init_bad_flag(workspace) -> None:
    code, _, err = call(["manifest", "init", "--bogus"], workspace)
    assert code == 2
    assert "manifest options" in err


def test_manifest_init_write_failure(workspace, monkeypatch) -> None:
    monkeypatch.setattr(config, "write_profile", lambda _p: (_ for _ in ()).throw(OSError("nope")))
    code, _, err = call(["manifest", "init", "--global"], workspace)
    assert code == 1
    assert "manifest init" in err


def test_manifest_init_unresolvable_path(workspace, monkeypatch) -> None:
    monkeypatch.setattr(config, "global_profile_path", lambda: "")
    code, _, err = call(["manifest", "init", "--global"], workspace)
    assert code == 1
    assert "manifest init" in err


def test_permit_status_false_then_allow_then_true(workspace) -> None:
    code, out, _ = call(["permit", "status"], workspace)
    assert code == 2
    assert out == "permitted: false\n"

    code, out, _ = call(["permit", "allow"], workspace)
    assert code == 0
    assert "permitted:" in out

    code, out, _ = call(["permit"], workspace)
    assert code == 0
    assert out == "permitted: true\n"


def test_permit_allow_explicit_path(workspace) -> None:
    target = workspace / "elsewhere"
    code, out, _ = call(["permit", "allow", str(target)], workspace)
    assert code == 0
    assert str(target) in out
    assert config.is_permitted(str(target))


def test_permit_unknown_action(workspace) -> None:
    code, _, err = call(["permit", "wat"], workspace)
    assert code == 2
    assert "unknown action" in err


def test_permit_allow_failure(workspace, monkeypatch) -> None:
    monkeypatch.setattr(config, "mark_permitted", lambda _p: (_ for _ in ()).throw(OSError("x")))
    code, _, err = call(["permit", "allow"], workspace)
    assert code == 1
    assert "permit allow" in err


def test_mute_missing_command(workspace) -> None:
    code, _, err = call(["mute"], workspace)
    assert code == 2
    assert "missing command" in err


def test_mute_redacts(workspace) -> None:
    secret = "sk-" + "abcdefghijklmnopqrstuvwxyz"
    code, out, _ = call(["mute", "--", "printf", f"{secret}\\n"], workspace)
    assert code == 0
    assert secret not in out
    assert "***" in out


def test_mute_raw_bypasses_redaction(workspace) -> None:
    secret = "sk-" + "abcdefghijklmnopqrstuvwxyz"
    code, out, _ = call(["mute", "--raw", "--", "printf", f"{secret}\\n"], workspace)
    assert code == 0
    assert secret in out


def test_mute_pipe_errors_false_discards_stderr(workspace) -> None:
    code, _, err = call(
        ["mute", "--pipe-errors=false", "--", "sh", "-c", "printf boom 1>&2"],
        workspace,
    )
    assert code == 0
    assert "boom" not in err


def test_mute_max_lines_flag(workspace) -> None:
    # --raw keeps line content verbatim so the truncation marker is unambiguous.
    code, out, _ = call(
        ["mute", "--max-lines", "1", "--raw", "--", "printf", "a\\nb\\nc\\n"],
        workspace,
    )
    assert code == 0
    assert out.splitlines() == ["a", "[output truncated]"]


def test_mute_max_width_flag(workspace) -> None:
    # Width truncation lives in the muter, so --raw is intentionally absent here.
    code, out, _ = call(
        ["mute", "--max-width=3", "--", "printf", "abcdef\\n"], workspace
    )
    assert code == 0
    assert out == "abc\n"


def test_mute_timeout_flag(workspace) -> None:
    code, _, err = call(
        ["mute", "--timeout", "1", "--", "sh", "-c", "sleep 5"], workspace
    )
    assert code == 124
    assert "timed out" in err


def test_mute_require_permit_gate(workspace) -> None:
    _write_local_profile(workspace, {"require_permit": True})
    code, _, err = call(["mute", "--", "printf", "hi\\n"], workspace)
    assert code == 3
    assert "not permitted" in err


def test_mute_require_permit_satisfied(workspace) -> None:
    _write_local_profile(workspace, {"require_permit": True})
    config.mark_permitted(str(workspace))
    code, out, _ = call(["mute", "--raw", "--", "printf", "hi\\n"], workspace)
    assert code == 0
    assert out == "hi\n"


def test_mute_invalid_mask_pattern(workspace) -> None:
    _write_local_profile(workspace, {"mask_patterns": ["(unclosed"]})
    code, _, err = call(["mute", "--", "printf", "x\\n"], workspace)
    assert code == 1
    assert "mute:" in err


def test_mute_profile_load_error(workspace) -> None:
    target = workspace / ".hushline" / "profile.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("{bad", encoding="utf-8")
    code, _, err = call(["mute", "--", "printf", "x\\n"], workspace)
    assert code == 1
    assert "profile:" in err


def test_mute_bad_bool_flag_value(workspace) -> None:
    code, _, err = call(["mute", "--raw=maybe", "--", "printf", "x"], workspace)
    assert code == 2
    assert "mute options" in err


def test_mute_undefined_flag(workspace) -> None:
    code, _, err = call(["mute", "--nope", "--", "printf", "x"], workspace)
    assert code == 2
    assert "not defined" in err


def test_mute_int_flag_missing_argument(workspace) -> None:
    code, _, err = call(["mute", "--timeout"], workspace)
    assert code == 2
    assert "needs an argument" in err


def test_mute_int_flag_bad_value(workspace) -> None:
    code, _, err = call(["mute", "--timeout=x", "--", "printf", "x"], workspace)
    assert code == 2
    assert "mute options" in err


def test_mute_non_flag_stops_parsing(workspace) -> None:
    # A bare command with no leading "--" must still run (parsing stops at it).
    code, out, _ = call(["mute", "printf", "hi\\n"], workspace)
    assert code == 0
    assert "hi" in out


def test_parse_bool_true_token() -> None:
    flags, rest = engine._parse_flags(
        ["--raw=true", "cmd"], bool_flags={"raw"}, int_flags=set()
    )
    assert flags["raw"] is True
    assert rest == ["cmd"]
