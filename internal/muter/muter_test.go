// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// HUSHLINE — muter behaviour tests

package muter

import (
	"strings"
	"testing"

	"github.com/local/hushline/internal/config"
)

func TestApplyRedactsSecretsStripsANSIAndTruncates(t *testing.T) {
	cfg := config.DefaultProfile()
	cfg.MaxLineWidth = 18
	instance, err := Compose(cfg)
	if err != nil {
		t.Fatalf("Compose returned error: %v", err)
	}
	secret := "sk-" + "abcdefghijklmnopqrstuvwxyz"

	got := instance.Apply("\x1b[31mtoken " + secret + "\x1b[0m suffix")

	if strings.Contains(got, secret) {
		t.Fatalf("secret was not redacted: %q", got)
	}
	if strings.Contains(got, "\x1b[") {
		t.Fatalf("ANSI escape sequence was not stripped: %q", got)
	}
	if len(got) > cfg.MaxLineWidth {
		t.Fatalf("output length = %d, want <= %d: %q", len(got), cfg.MaxLineWidth, got)
	}
}

func TestApplyNilMuterReturnsInput(t *testing.T) {
	var instance *Muter

	if got := instance.Apply("unchanged"); got != "unchanged" {
		t.Fatalf("nil muter Apply = %q, want unchanged", got)
	}
}

func TestApplyLeavesShortInputUntruncated(t *testing.T) {
	cfg := config.DefaultProfile()
	cfg.MaxLineWidth = 100
	instance, err := Compose(cfg)
	if err != nil {
		t.Fatalf("Compose returned error: %v", err)
	}

	if got := instance.Apply("short"); got != "short" {
		t.Fatalf("Apply short input = %q, want short", got)
	}
}

func TestTruncateReturnsInputForDisabledOrEqualWidth(t *testing.T) {
	if got := truncate("abc", 0); got != "abc" {
		t.Fatalf("truncate disabled = %q, want abc", got)
	}
	if got := truncate("abc", -1); got != "abc" {
		t.Fatalf("truncate negative width = %q, want abc", got)
	}
	if got := truncate("abc", 3); got != "abc" {
		t.Fatalf("truncate equal width = %q, want abc", got)
	}
}

func TestComposeHonoursDisabledANSIStripping(t *testing.T) {
	cfg := config.DefaultProfile()
	cfg.StripANSI = false
	instance, err := Compose(cfg)
	if err != nil {
		t.Fatalf("Compose returned error: %v", err)
	}

	got := instance.Apply("\x1b[31mvisible\x1b[0m")

	if !strings.Contains(got, "\x1b[31m") {
		t.Fatalf("ANSI was stripped despite disabled setting: %q", got)
	}
}

func TestComposeRejectsInvalidRedactionPattern(t *testing.T) {
	cfg := config.DefaultProfile()
	cfg.MaskPatterns = append(cfg.MaskPatterns, "[")

	if _, err := Compose(cfg); err == nil {
		t.Fatalf("Compose returned nil error for invalid redaction pattern")
	}
}

func TestComposeRejectsInvalidSilenceRulePattern(t *testing.T) {
	cfg := config.DefaultProfile()
	cfg.QuietRules = append(cfg.QuietRules, config.QuietRule{
		Name:        "broken",
		Pattern:     "[",
		Replacement: "",
	})

	if _, err := Compose(cfg); err == nil {
		t.Fatalf("Compose returned nil error for invalid silence rule pattern")
	}
}
