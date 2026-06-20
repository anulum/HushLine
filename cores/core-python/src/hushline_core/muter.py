# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# HUSHLINE — muter support utilities

"""Line shaping: ANSI stripping, secret redaction, and silence rewrites.

Rules run in the same order as the Go core: ANSI escape removal first (when
enabled), then each mask pattern replaced with ``***``, then the configured
silence rules. Finally, if a positive line width is set, the line is truncated
to that many bytes — matching Go's byte-slice truncation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from hushline_core.config import Config

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
_MASK_REPLACEMENT = "***"


class MuterError(Exception):
    """Raised when a configured pattern is not a valid regular expression."""


@dataclass(frozen=True)
class _Rule:
    name: str
    pattern: re.Pattern[str]
    replacement: str


class Muter:
    """Applies the composed rule chain to a single line of text."""

    def __init__(self, rules: list[_Rule], max_line_width: int) -> None:
        self._rules = rules
        self._max_line_width = max_line_width

    def apply(self, text: str) -> str:
        out = text
        for rule in self._rules:
            out = rule.pattern.sub(rule.replacement, out)
        if self._max_line_width > 0:
            out = _truncate(out, self._max_line_width)
        return out


def compose(cfg: Config) -> Muter:
    """Build a :class:`Muter` from a resolved profile.

    Raises :class:`MuterError` if any mask or silence pattern fails to compile,
    mirroring the Go core's refusal to run with an invalid profile.
    """
    rules: list[_Rule] = []

    if cfg.strip_ansi:
        rules.append(_Rule(name="ansi", pattern=_ANSI_RE, replacement=""))

    for pattern in cfg.mask_patterns:
        rules.append(
            _Rule(
                name="redact",
                pattern=_compile(pattern, "invalid redact pattern"),
                replacement=_MASK_REPLACEMENT,
            )
        )

    for rule in cfg.quiet_rules:
        rules.append(
            _Rule(
                name=rule.name,
                pattern=_compile(rule.pattern, "invalid silence pattern"),
                replacement=rule.replacement,
            )
        )

    return Muter(rules, cfg.max_line_width)


def _compile(pattern: str, label: str) -> re.Pattern[str]:
    try:
        return re.compile(pattern)
    except re.error as exc:
        raise MuterError(f"{label} {pattern!r}: {exc}") from exc


def _truncate(text: str, max_bytes: int) -> str:
    """Truncate ``text`` to at most ``max_bytes`` UTF-8 bytes.

    Go slices the raw byte buffer (``input[:max]``); we bound by byte length the
    same way but decode back with ``errors="ignore"`` so a cut that lands inside
    a multi-byte rune never emits invalid UTF-8. Only called with a positive
    ``max_bytes`` (the caller guards on a positive line width).
    """
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode("utf-8", errors="ignore")
