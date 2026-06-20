# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# HUSHLINE — Python core muter tests

"""ANSI stripping, redaction, silence rewrites, and byte truncation."""

from __future__ import annotations

import pytest

from hushline_core import muter as muter_mod
from hushline_core.config import Config, QuietRule, default_profile


def test_default_chain_redacts_and_collapses() -> None:
    m = muter_mod.compose(default_profile())
    secret = "sk-" + "abcdefghijklmnopqrstuvwxyz"
    out = m.apply(f"\x1b[31mtoken {secret}\x1b[0m   suffix")
    assert secret not in out
    assert "***" in out
    assert "\x1b[" not in out
    assert "   " not in out  # collapse-space rule


def test_strip_ansi_disabled_keeps_escapes() -> None:
    cfg = Config(strip_ansi=False, mask_patterns=(), quiet_rules=())
    m = muter_mod.compose(cfg)
    assert m.apply("\x1b[31mred\x1b[0m") == "\x1b[31mred\x1b[0m"


def test_aws_key_redacted() -> None:
    m = muter_mod.compose(default_profile())
    assert "AKIA" not in m.apply("AKIA0123456789ABCDEF")


def test_rules_apply_in_order() -> None:
    cfg = Config(
        strip_ansi=False,
        mask_patterns=(),
        quiet_rules=(
            QuietRule(name="first", pattern="a", replacement="b"),
            QuietRule(name="second", pattern="b", replacement="c"),
        ),
    )
    # "a" -> "b" (first rule) -> "c" (second rule): order matters.
    assert muter_mod.compose(cfg).apply("a") == "c"


def test_truncation_is_byte_bounded() -> None:
    cfg = Config(strip_ansi=False, max_line_width=4, mask_patterns=(), quiet_rules=())
    assert muter_mod.compose(cfg).apply("abcdef") == "abcd"


def test_truncation_below_limit_is_untouched() -> None:
    cfg = Config(strip_ansi=False, max_line_width=10, mask_patterns=(), quiet_rules=())
    assert muter_mod.compose(cfg).apply("abc") == "abc"


def test_truncation_does_not_emit_invalid_utf8() -> None:
    # "é" is two UTF-8 bytes; cutting at 2 bytes lands mid-rune, so the partial
    # rune is dropped rather than emitted as invalid UTF-8.
    cfg = Config(strip_ansi=False, max_line_width=2, mask_patterns=(), quiet_rules=())
    out = muter_mod.compose(cfg).apply("aéb")
    assert out == "a"
    out.encode("utf-8")  # round-trips cleanly


def test_truncation_keeps_whole_multibyte_rune_on_boundary() -> None:
    # Cutting exactly on a rune boundary (3 bytes = "a" + "é") keeps both.
    cfg = Config(strip_ansi=False, max_line_width=3, mask_patterns=(), quiet_rules=())
    assert muter_mod.compose(cfg).apply("aéb") == "aé"


def test_invalid_mask_pattern_raises() -> None:
    cfg = Config(mask_patterns=("(unclosed",), quiet_rules=())
    with pytest.raises(muter_mod.MuterError, match="invalid redact pattern"):
        muter_mod.compose(cfg)


def test_invalid_silence_pattern_raises() -> None:
    cfg = Config(
        mask_patterns=(),
        quiet_rules=(QuietRule(name="bad", pattern="(", replacement=""),),
    )
    with pytest.raises(muter_mod.MuterError, match="invalid silence pattern"):
        muter_mod.compose(cfg)
