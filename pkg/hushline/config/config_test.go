// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// HUSHLINE — config behaviour tests

package config

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLoadProfileAllowsExplicitBooleanOverrides(t *testing.T) {
	t.Setenv("XDG_CONFIG_HOME", filepath.Join(t.TempDir(), "xdg"))
	cwd := t.TempDir()
	profilePath := LocalProfilePath(cwd)
	if err := os.MkdirAll(filepath.Dir(profilePath), 0o700); err != nil {
		t.Fatalf("create profile directory: %v", err)
	}
	if err := os.WriteFile(profilePath, []byte(`{
  "strip_ansi": false,
  "preserve_errors": false,
  "require_permit": true
}
`), 0o600); err != nil {
		t.Fatalf("write profile: %v", err)
	}

	cfg, err := LoadProfile(cwd)
	if err != nil {
		t.Fatalf("LoadProfile returned error: %v", err)
	}

	if cfg.StripANSI {
		t.Fatalf("StripANSI = true, want explicit local false override")
	}
	if cfg.PreserveErrors {
		t.Fatalf("PreserveErrors = true, want explicit local false override")
	}
	if !cfg.RequirePermit {
		t.Fatalf("RequirePermit = false, want explicit local true override")
	}
}

func TestLoadProfileMergesNumericPatternsAndRules(t *testing.T) {
	t.Setenv("XDG_CONFIG_HOME", filepath.Join(t.TempDir(), "xdg"))
	cwd := t.TempDir()
	profilePath := LocalProfilePath(cwd)
	if err := os.MkdirAll(filepath.Dir(profilePath), 0o700); err != nil {
		t.Fatalf("create profile directory: %v", err)
	}
	if err := os.WriteFile(profilePath, []byte(`{
  "max_lines": 7,
  "line_width": 12,
  "mask_patterns": ["secret-[0-9]+"],
  "silence_rules": [
    {"name": "digits", "pattern": "[0-9]+", "replacement": "#"}
  ]
}
`), 0o600); err != nil {
		t.Fatalf("write profile: %v", err)
	}

	cfg, err := LoadProfile(cwd)
	if err != nil {
		t.Fatalf("LoadProfile returned error: %v", err)
	}

	if cfg.MaxOutputLines != 7 {
		t.Fatalf("MaxOutputLines = %d, want 7", cfg.MaxOutputLines)
	}
	if cfg.MaxLineWidth != 12 {
		t.Fatalf("MaxLineWidth = %d, want 12", cfg.MaxLineWidth)
	}
	if got := cfg.MaskPatterns[len(cfg.MaskPatterns)-1]; got != "secret-[0-9]+" {
		t.Fatalf("last mask pattern = %q, want custom pattern", got)
	}
	if got := cfg.QuietRules[len(cfg.QuietRules)-1].Name; got != "digits" {
		t.Fatalf("last quiet rule = %q, want digits", got)
	}
}

func TestLoadProfileRejectsUnknownFields(t *testing.T) {
	t.Setenv("XDG_CONFIG_HOME", filepath.Join(t.TempDir(), "xdg"))
	cwd := t.TempDir()
	profilePath := LocalProfilePath(cwd)
	if err := os.MkdirAll(filepath.Dir(profilePath), 0o700); err != nil {
		t.Fatalf("create profile directory: %v", err)
	}
	if err := os.WriteFile(profilePath, []byte(`{"unexpected": true}`), 0o600); err != nil {
		t.Fatalf("write profile: %v", err)
	}

	if _, err := LoadProfile(cwd); err == nil {
		t.Fatalf("LoadProfile returned nil error for unknown field")
	}
}

func TestMarkPermittedCreatesPrivateMarker(t *testing.T) {
	cwd := t.TempDir()

	if err := MarkPermitted(cwd); err != nil {
		t.Fatalf("MarkPermitted returned error: %v", err)
	}

	marker := PermitMarkerPath(cwd)
	info, err := os.Stat(marker)
	if err != nil {
		t.Fatalf("stat marker: %v", err)
	}
	if !IsPermitted(cwd) {
		t.Fatalf("IsPermitted returned false after MarkPermitted")
	}
	if got := info.Mode().Perm(); got != 0o600 {
		t.Fatalf("marker permissions = %o, want 600", got)
	}
}

func TestWriteProfileCreatesPrivateDefaultProfile(t *testing.T) {
	target := filepath.Join(t.TempDir(), "profile.json")

	if err := WriteProfile(target); err != nil {
		t.Fatalf("WriteProfile returned error: %v", err)
	}

	info, err := os.Stat(target)
	if err != nil {
		t.Fatalf("stat profile: %v", err)
	}
	if got := info.Mode().Perm(); got != 0o600 {
		t.Fatalf("profile permissions = %o, want 600", got)
	}
	cfg, err := readProfileFile(target)
	if err != nil {
		t.Fatalf("read written profile: %v", err)
	}
	if cfg.MaxOutputLines == nil || *cfg.MaxOutputLines != DefaultProfile().MaxOutputLines {
		t.Fatalf("written max_lines = %v, want default", cfg.MaxOutputLines)
	}
}

func TestWriteProfileReturnsDirectoryCreationError(t *testing.T) {
	if err := WriteProfile("/proc/hushline/profile.json"); err == nil {
		t.Fatalf("WriteProfile returned nil error for unwritable target")
	}
}

func TestWriteProfileReturnsFileWriteError(t *testing.T) {
	if err := WriteProfile(t.TempDir()); err == nil {
		t.Fatalf("WriteProfile returned nil error when target is a directory")
	}
}

func TestLoadProfileSkipsUnavailableGlobalProfilePath(t *testing.T) {
	t.Setenv("XDG_CONFIG_HOME", "")
	t.Setenv("HOME", "")

	cfg, err := LoadProfile(t.TempDir())
	if err != nil {
		t.Fatalf("LoadProfile returned error: %v", err)
	}
	if cfg.MaxOutputLines != DefaultProfile().MaxOutputLines {
		t.Fatalf("MaxOutputLines = %d, want default", cfg.MaxOutputLines)
	}
}

func TestMarkPermittedReturnsDirectoryCreationError(t *testing.T) {
	if err := MarkPermitted("/proc/hushline"); err == nil {
		t.Fatalf("MarkPermitted returned nil error for unwritable target")
	}
}

func TestGlobalProfilePathReturnsEmptyWhenUserConfigUnavailable(t *testing.T) {
	t.Setenv("XDG_CONFIG_HOME", "")
	t.Setenv("HOME", "")

	if got := GlobalProfilePath(); got != "" {
		t.Fatalf("GlobalProfilePath = %q, want empty when user config directory is unavailable", got)
	}
}
