# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# HUSHLINE — core engine bootstrap

"""Command dispatch for the Python core.

``run`` maps argv to the ``mute``, ``manifest``, ``permit``, and ``version``
commands, parsing flags with the same semantics as Go's ``flag`` package
(parsing stops at the first non-flag token or ``--``; boolean flags take no
following argument). Output streams and the working directory are injectable so
the behaviour is fully testable.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Sequence, TextIO

from hushline_core import config
from hushline_core import muter as muter_mod
from hushline_core import pipeline
from hushline_core.version import VERSION

USAGE = """hushline - local command output shaping utility

Usage:
  hushline <command> [options]

Commands:
  mute [options] -- <command> [args...]   execute command through silence profile
  manifest init [--global|--local]         create default profile file
  manifest show                            print profile locations
  permit [status|allow] [path]             manage local permit marker
  version                                  print hushline version
  help                                     print this help text

Global options:
  -h, --help                               show usage for a command
"""

_TRUE_TOKENS = frozenset({"1", "t", "T", "TRUE", "true", "True"})
_FALSE_TOKENS = frozenset({"0", "f", "F", "FALSE", "false", "False"})


class _FlagError(Exception):
    """Raised on malformed command flags."""


def run(
    argv: Sequence[str],
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    cwd: str | None = None,
) -> int:
    """Execute the Hushline command described by ``argv``."""
    out = stdout if stdout is not None else sys.stdout
    err = stderr if stderr is not None else sys.stderr
    work_dir = cwd if cwd is not None else os.getcwd()

    if not argv or argv[0] in ("help", "-h", "--help"):
        out.write(USAGE)
        return 0

    command = argv[0]
    if command == "mute":
        return _mute(argv[1:], out, err, work_dir)
    if command == "manifest":
        return _manifest(argv[1:], out, err, work_dir)
    if command == "permit":
        return _permit(argv[1:], out, err, work_dir)
    if command == "version":
        out.write(f"hushline {VERSION}\n")
        return 0

    out.write(f"unknown command: {command}\n\n")
    out.write(USAGE)
    return 1


def _manifest(argv: Sequence[str], out: TextIO, err: TextIO, cwd: str) -> int:
    if not argv or argv[0] == "show":
        out.write(f"global profile: {config.global_profile_path()}\n")
        out.write(f"local profile:  {config.local_profile_path(cwd)}\n")
        return 0
    if argv[0] != "init":
        err.write(f'manifest: unknown action "{argv[0]}"\n')
        return 2

    try:
        flags, _ = _parse_flags(
            argv[1:], bool_flags={"global", "local"}, int_flags=set()
        )
    except _FlagError as exc:
        err.write(f"manifest options: {exc}\n")
        return 2

    try:
        _emit_profile(bool(flags.get("global")), bool(flags.get("local")), cwd, out)
    except OSError as exc:
        err.write(f"manifest init: {exc}\n")
        return 1
    return 0


def _permit(argv: Sequence[str], out: TextIO, err: TextIO, cwd: str) -> int:
    action = argv[0] if argv else "status"
    if action == "status":
        if config.is_permitted(cwd):
            out.write("permitted: true\n")
            return 0
        out.write("permitted: false\n")
        return 2
    if action == "allow":
        target = argv[1] if len(argv) > 1 else cwd
        try:
            config.mark_permitted(target)
        except OSError as exc:
            err.write(f"permit allow: {exc}\n")
            return 1
        out.write(f"permitted: {target}\n")
        return 0
    err.write(f'permit: unknown action "{action}"\n')
    return 2


def _mute(argv: Sequence[str], out: TextIO, err: TextIO, cwd: str) -> int:
    try:
        flags, rest = _parse_flags(
            argv,
            bool_flags={"raw", "pipe-errors"},
            int_flags={"max-lines", "max-width", "timeout"},
            defaults={"pipe-errors": True},
        )
    except _FlagError as exc:
        err.write(f"mute options: {exc}\n")
        return 2

    if not rest:
        err.write("mute: missing command\n")
        return 2

    try:
        profile = config.load_profile(cwd)
    except config.ProfileError as exc:
        err.write(f"profile: {exc}\n")
        return 1

    max_lines = int(flags.get("max-lines", 0))
    max_width = int(flags.get("max-width", 0))
    if max_lines > 0:
        profile = _with(profile, max_output_lines=max_lines)
    if max_width > 0:
        profile = _with(profile, max_line_width=max_width)
    preserve_errors = bool(flags.get("pipe-errors", True))
    profile = _with(profile, preserve_errors=preserve_errors)

    if profile.require_permit and not config.is_permitted(cwd):
        err.write(
            "hushline: current directory not permitted. run "
            "`hushline permit allow` first or set require_permit: false\n"
        )
        return 3

    silence: muter_mod.Muter | None = None
    if not flags.get("raw"):
        try:
            silence = muter_mod.compose(profile)
        except muter_mod.MuterError as exc:
            err.write(f"mute: {exc}\n")
            return 1

    exit_code = pipeline.through(
        rest[0],
        rest[1:],
        out,
        err,
        silence,
        profile.max_output_lines,
        profile.preserve_errors,
        int(flags.get("timeout", 0)),
    )
    if exit_code == 124:
        err.write("hushline: command timed out\n")
    return exit_code


def _emit_profile(
    write_global: bool, write_local: bool, cwd: str, out: TextIO
) -> None:
    if write_local and not write_global:
        target = config.local_profile_path(cwd)
    else:
        target = config.global_profile_path()
    if not target:
        raise OSError("could not resolve profile path")
    Path(target).parent.mkdir(parents=True, exist_ok=True)
    config.write_profile(target)
    out.write(f"profile written: {target}\n")


def _with(profile: config.Config, **changes: object) -> config.Config:
    from dataclasses import replace

    return replace(profile, **changes)


def _parse_flags(
    argv: Sequence[str],
    *,
    bool_flags: set[str],
    int_flags: set[str],
    defaults: dict[str, object] | None = None,
) -> tuple[dict[str, object], list[str]]:
    """Parse ``argv`` with Go ``flag``-style semantics.

    Returns ``(flags, rest)``. Parsing stops at the first non-flag token or at a
    bare ``--``; the remaining tokens are positional. Boolean flags consume no
    following argument; integer flags take ``=value`` or the next token.
    """
    flags: dict[str, object] = dict(defaults or {})
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--":
            return flags, list(argv[index + 1 :])
        if not (len(token) > 1 and token.startswith("-")):
            return flags, list(argv[index:])

        body = token.lstrip("-")
        name, sep, value = body.partition("=")
        has_value = bool(sep)

        if name in bool_flags:
            flags[name] = True if not has_value else _parse_bool(name, value)
        elif name in int_flags:
            if not has_value:
                index += 1
                if index >= len(argv):
                    raise _FlagError(f"flag needs an argument: -{name}")
                value = argv[index]
            flags[name] = _parse_int(name, value)
        else:
            raise _FlagError(f"flag provided but not defined: -{name}")
        index += 1

    return flags, []


def _parse_bool(name: str, value: str) -> bool:
    if value in _TRUE_TOKENS:
        return True
    if value in _FALSE_TOKENS:
        return False
    raise _FlagError(f"invalid boolean value {value!r} for -{name}")


def _parse_int(name: str, value: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise _FlagError(f"invalid value {value!r} for -{name}") from exc
