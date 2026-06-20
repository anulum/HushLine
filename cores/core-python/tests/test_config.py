# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# HUSHLINE — Python core config tests

"""Profile defaults, strict parsing, merge semantics, paths, and permit state."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from hushline_core import config


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_default_profile_matches_go_reference() -> None:
    cfg = config.default_profile()
    assert cfg.max_output_lines == 2000
    assert cfg.max_line_width == 0
    assert cfg.strip_ansi is True
    assert cfg.preserve_errors is True
    assert cfg.require_permit is False
    assert cfg.mask_patterns == (r"AKIA[0-9A-Z]{16}", r"sk-[a-zA-Z0-9]{20,}")
    assert [r.name for r in cfg.quiet_rules] == ["ci-trim", "collapse-space"]


def test_load_profile_no_files_returns_defaults(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    cfg = config.load_profile(str(tmp_path / "work"))
    assert cfg == config.default_profile()


def test_local_overrides_and_appends(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    work = tmp_path / "work"
    _write(
        work / ".hushline" / "profile.json",
        {
            "max_lines": 50,
            "line_width": 80,
            "strip_ansi": False,
            "preserve_errors": False,
            "require_permit": True,
            "mask_patterns": ["EXTRA[0-9]+"],
            "silence_rules": [{"name": "x", "pattern": "a", "replacement": "b"}],
        },
    )
    cfg = config.load_profile(str(work))
    assert cfg.max_output_lines == 50
    assert cfg.max_line_width == 80
    assert cfg.strip_ansi is False
    assert cfg.preserve_errors is False
    assert cfg.require_permit is True
    # masks and rules append onto the defaults, never replace them.
    assert cfg.mask_patterns[-1] == "EXTRA[0-9]+"
    assert len(cfg.mask_patterns) == 3
    assert cfg.quiet_rules[-1].name == "x"
    assert len(cfg.quiet_rules) == 3


def test_global_then_local_merge_order(tmp_path, monkeypatch) -> None:
    xdg = tmp_path / "xdg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    _write(xdg / "hushline" / "profile.json", {"max_lines": 10})
    work = tmp_path / "work"
    _write(work / ".hushline" / "profile.json", {"max_lines": 20})
    cfg = config.load_profile(str(work))
    assert cfg.max_output_lines == 20


def test_zero_max_lines_and_negative_line_width_are_ignored(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    work = tmp_path / "work"
    _write(work / ".hushline" / "profile.json", {"max_lines": 0, "line_width": -5})
    cfg = config.load_profile(str(work))
    assert cfg.max_output_lines == 2000
    assert cfg.max_line_width == 0


def test_line_width_zero_is_applied(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    work = tmp_path / "work"
    _write(work / ".hushline" / "profile.json", {"line_width": 0})
    assert config.load_profile(str(work)).max_line_width == 0


def test_empty_mask_and_silence_lists_are_noops(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    work = tmp_path / "work"
    _write(work / ".hushline" / "profile.json", {"mask_patterns": [], "silence_rules": []})
    cfg = config.load_profile(str(work))
    # Present-but-empty lists must not change the inherited defaults.
    assert cfg.mask_patterns == config.default_profile().mask_patterns
    assert cfg.quiet_rules == config.default_profile().quiet_rules


def test_empty_global_path_is_skipped(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(config, "global_profile_path", lambda: "")
    work = tmp_path / "work"
    _write(work / ".hushline" / "profile.json", {"max_lines": 7})
    cfg = config.load_profile(str(work))
    assert cfg.max_output_lines == 7


@pytest.mark.parametrize(
    "payload, message",
    [
        ({"unknown": 1}, "unknown field"),
        ({"max_lines": "x"}, "max_lines must be an integer"),
        ({"max_lines": True}, "max_lines must be an integer"),
        ({"line_width": "x"}, "line_width must be an integer"),
        ({"strip_ansi": "x"}, "strip_ansi must be a boolean"),
        ({"mask_patterns": "x"}, "mask_patterns must be a list"),
        ({"mask_patterns": [1]}, "mask_patterns must be a list"),
        ({"silence_rules": "x"}, "silence_rules must be a list"),
        ({"silence_rules": ["x"]}, "must be an object"),
        ({"silence_rules": [{"bad": 1}]}, "unknown silence rule field"),
        ({"silence_rules": [{"name": 1}]}, "fields must be strings"),
    ],
)
def test_strict_parse_rejects_malformed(tmp_path, monkeypatch, payload, message) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    work = tmp_path / "work"
    _write(work / ".hushline" / "profile.json", payload)
    with pytest.raises(config.ProfileError, match=message):
        config.load_profile(str(work))


def test_invalid_json_raises(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    work = tmp_path / "work"
    target = work / ".hushline" / "profile.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("{not json", encoding="utf-8")
    with pytest.raises(config.ProfileError, match="failed reading config"):
        config.load_profile(str(work))


def test_non_object_json_raises(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    work = tmp_path / "work"
    target = work / ".hushline" / "profile.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(config.ProfileError, match="not an object"):
        config.load_profile(str(work))


def test_write_profile_content_and_permissions(tmp_path) -> None:
    target = tmp_path / "nested" / "profile.json"
    config.write_profile(str(target))
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["max_lines"] == 2000
    assert data["silence_rules"][0]["name"] == "ci-trim"
    assert list(data.keys()) == [
        "max_lines",
        "line_width",
        "strip_ansi",
        "preserve_errors",
        "require_permit",
        "mask_patterns",
        "silence_rules",
    ]
    mode = stat.S_IMODE(target.stat().st_mode)
    assert mode == 0o600


def test_loading_a_written_default_appends_masks_and_rules(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    work = tmp_path / "work"
    config.write_profile(config.local_profile_path(str(work)))
    # Merge appends mask/silence lists (matching Go), so a written default
    # profile reloads with its masks and rules doubled — scalars stay put.
    cfg = config.load_profile(str(work))
    assert cfg.max_output_lines == 2000
    assert cfg.strip_ansi is True
    assert len(cfg.mask_patterns) == 2 * len(config.default_profile().mask_patterns)
    assert len(cfg.quiet_rules) == 2 * len(config.default_profile().quiet_rules)


def test_write_profile_tolerates_chmod_failure(tmp_path, monkeypatch) -> None:
    def boom(*_args, **_kwargs):
        raise OSError("no chmod")

    monkeypatch.setattr(config.os, "chmod", boom)
    target = tmp_path / "profile.json"
    config.write_profile(str(target))  # must not raise
    assert target.exists()


def test_permit_round_trip_and_chmod_failure(tmp_path, monkeypatch) -> None:
    work = str(tmp_path / "work")
    assert config.is_permitted(work) is False
    config.mark_permitted(work)
    assert config.is_permitted(work) is True
    assert Path(config.permit_marker_path(work)).read_text() == "ok\n"

    monkeypatch.setattr(config.os, "chmod", lambda *a, **k: (_ for _ in ()).throw(OSError()))
    other = str(tmp_path / "other")
    config.mark_permitted(other)  # must not raise despite chmod failure
    assert config.is_permitted(other) is True


def test_user_config_dir_linux_xdg(monkeypatch) -> None:
    monkeypatch.setattr(config.sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", "/xdg")
    assert config.user_config_dir() == "/xdg"


def test_user_config_dir_linux_home_fallback(monkeypatch) -> None:
    monkeypatch.setattr(config.sys, "platform", "linux")
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", "/home/x")
    assert config.user_config_dir() == "/home/x/.config"


def test_user_config_dir_linux_no_home(monkeypatch) -> None:
    monkeypatch.setattr(config.sys, "platform", "linux")
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("HOME", raising=False)
    assert config.user_config_dir() is None


def test_user_config_dir_darwin(monkeypatch) -> None:
    monkeypatch.setattr(config.sys, "platform", "darwin")
    monkeypatch.setenv("HOME", "/Users/x")
    assert config.user_config_dir() == "/Users/x/Library/Application Support"


def test_user_config_dir_darwin_no_home(monkeypatch) -> None:
    monkeypatch.setattr(config.sys, "platform", "darwin")
    monkeypatch.delenv("HOME", raising=False)
    assert config.user_config_dir() is None


def test_user_config_dir_windows(monkeypatch) -> None:
    monkeypatch.setattr(config.sys, "platform", "win32")
    monkeypatch.setenv("AppData", r"C:\\Users\\x\\AppData\\Roaming")
    assert config.user_config_dir() == r"C:\\Users\\x\\AppData\\Roaming"


def test_user_config_dir_windows_missing(monkeypatch) -> None:
    monkeypatch.setattr(config.sys, "platform", "win32")
    monkeypatch.delenv("AppData", raising=False)
    assert config.user_config_dir() is None


def test_global_profile_path_empty_without_base(monkeypatch) -> None:
    monkeypatch.setattr(config, "user_config_dir", lambda: None)
    assert config.global_profile_path() == ""
