# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# HUSHLINE — profile config module

"""Profile configuration: defaults, strict JSON parsing, and the
defaults -> global -> local merge that the Go reference core performs.

The on-disk JSON uses the Go field names (``max_lines``, ``line_width``,
``strip_ansi``, ``preserve_errors``, ``require_permit``, ``mask_patterns``,
``silence_rules`` with ``name``/``pattern``/``replacement``). Unknown keys are
rejected, mirroring Go's ``DisallowUnknownFields``.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, replace
from pathlib import Path

_PROFILE_KEYS = frozenset(
    {
        "max_lines",
        "line_width",
        "strip_ansi",
        "preserve_errors",
        "require_permit",
        "mask_patterns",
        "silence_rules",
    }
)
_RULE_KEYS = frozenset({"name", "pattern", "replacement"})


class ProfileError(Exception):
    """Raised when a profile file cannot be parsed or is malformed."""


@dataclass(frozen=True)
class QuietRule:
    """A named regex rewrite applied to each output line."""

    name: str
    pattern: str
    replacement: str


@dataclass(frozen=True)
class Config:
    """Resolved muting profile."""

    max_output_lines: int = 2000
    max_line_width: int = 0
    strip_ansi: bool = True
    preserve_errors: bool = True
    require_permit: bool = False
    mask_patterns: tuple[str, ...] = ()
    quiet_rules: tuple[QuietRule, ...] = ()


def default_profile() -> Config:
    """Return the built-in default profile (identical to the Go core)."""
    return Config(
        max_output_lines=2000,
        max_line_width=0,
        strip_ansi=True,
        preserve_errors=True,
        require_permit=False,
        mask_patterns=(
            r"AKIA[0-9A-Z]{16}",
            r"sk-[a-zA-Z0-9]{20,}",
        ),
        quiet_rules=(
            QuietRule(name="ci-trim", pattern=r"\n+", replacement=" "),
            QuietRule(name="collapse-space", pattern=r"[ \t]{2,}", replacement=" "),
        ),
    )


def _parse_rule(raw: object, source: str) -> QuietRule:
    if not isinstance(raw, dict):
        raise ProfileError(f"{source}: silence rule must be an object")
    unknown = set(raw) - _RULE_KEYS
    if unknown:
        raise ProfileError(
            f"{source}: unknown silence rule field(s): {', '.join(sorted(unknown))}"
        )
    name = raw.get("name", "")
    pattern = raw.get("pattern", "")
    replacement = raw.get("replacement", "")
    if not isinstance(name, str) or not isinstance(pattern, str) or not isinstance(
        replacement, str
    ):
        raise ProfileError(f"{source}: silence rule fields must be strings")
    return QuietRule(name=name, pattern=pattern, replacement=replacement)


def _apply_patch(base: Config, raw: dict[str, object], source: str) -> Config:
    """Merge one parsed profile file onto ``base`` using Go's patch rules."""
    unknown = set(raw) - _PROFILE_KEYS
    if unknown:
        raise ProfileError(
            f"{source}: unknown field(s): {', '.join(sorted(unknown))}"
        )

    changes: dict[str, object] = {}

    if "max_lines" in raw:
        value = raw["max_lines"]
        if not isinstance(value, int) or isinstance(value, bool):
            raise ProfileError(f"{source}: max_lines must be an integer")
        if value > 0:
            changes["max_output_lines"] = value

    if "line_width" in raw:
        value = raw["line_width"]
        if not isinstance(value, int) or isinstance(value, bool):
            raise ProfileError(f"{source}: line_width must be an integer")
        if value >= 0:
            changes["max_line_width"] = value

    for key, attr in (
        ("strip_ansi", "strip_ansi"),
        ("preserve_errors", "preserve_errors"),
        ("require_permit", "require_permit"),
    ):
        if key in raw:
            value = raw[key]
            if not isinstance(value, bool):
                raise ProfileError(f"{source}: {key} must be a boolean")
            changes[attr] = value

    if "mask_patterns" in raw:
        masks = raw["mask_patterns"]
        if not isinstance(masks, list) or not all(isinstance(m, str) for m in masks):
            raise ProfileError(f"{source}: mask_patterns must be a list of strings")
        if masks:
            changes["mask_patterns"] = base.mask_patterns + tuple(masks)

    if "silence_rules" in raw:
        rules_raw = raw["silence_rules"]
        if not isinstance(rules_raw, list):
            raise ProfileError(f"{source}: silence_rules must be a list")
        parsed = tuple(_parse_rule(r, source) for r in rules_raw)
        if parsed:
            changes["quiet_rules"] = base.quiet_rules + parsed

    return replace(base, **changes)


def _read_profile_file(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProfileError(f"failed reading config {str(path)!r}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProfileError(f"failed reading config {str(path)!r}: not an object")
    return data


def load_profile(cwd: str) -> Config:
    """Load the effective profile: defaults -> global -> local."""
    cfg = default_profile()
    for path_str in (global_profile_path(), local_profile_path(cwd)):
        if not path_str:
            continue
        path = Path(path_str)
        if not path.exists():
            continue
        cfg = _apply_patch(cfg, _read_profile_file(path), str(path))
    return cfg


def _profile_dict(cfg: Config) -> dict[str, object]:
    """Serialise a profile in the Go key order for ``manifest init``."""
    return {
        "max_lines": cfg.max_output_lines,
        "line_width": cfg.max_line_width,
        "strip_ansi": cfg.strip_ansi,
        "preserve_errors": cfg.preserve_errors,
        "require_permit": cfg.require_permit,
        "mask_patterns": list(cfg.mask_patterns),
        "silence_rules": [
            {"name": r.name, "pattern": r.pattern, "replacement": r.replacement}
            for r in cfg.quiet_rules
        ],
    }


def write_profile(path: str) -> None:
    """Write the default profile to ``path`` with restrictive permissions."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(target.parent, 0o700)
    except OSError:
        pass
    blob = json.dumps(_profile_dict(default_profile()), indent=2) + "\n"
    target.write_text(blob, encoding="utf-8")
    try:
        os.chmod(target, 0o600)
    except OSError:
        pass


def user_config_dir() -> str | None:
    """Mirror Go's ``os.UserConfigDir`` for the current platform."""
    if sys.platform == "win32":
        return os.environ.get("AppData") or None
    if sys.platform == "darwin":
        home = os.environ.get("HOME")
        return str(Path(home) / "Library" / "Application Support") if home else None
    explicit = os.environ.get("XDG_CONFIG_HOME")
    if explicit:
        return explicit
    home = os.environ.get("HOME")
    return str(Path(home) / ".config") if home else None


def global_profile_path() -> str:
    base = user_config_dir()
    if not base:
        return ""
    return str(Path(base) / "hushline" / "profile.json")


def local_profile_path(cwd: str) -> str:
    return str(Path(cwd) / ".hushline" / "profile.json")


def permit_marker_path(cwd: str) -> str:
    return str(Path(cwd) / ".hushline" / "permitted")


def is_permitted(cwd: str) -> bool:
    return Path(permit_marker_path(cwd)).exists()


def mark_permitted(cwd: str) -> None:
    marker = Path(permit_marker_path(cwd))
    marker.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(marker.parent, 0o700)
    except OSError:
        pass
    marker.write_text("ok\n", encoding="utf-8")
    try:
        os.chmod(marker, 0o600)
    except OSError:
        pass
