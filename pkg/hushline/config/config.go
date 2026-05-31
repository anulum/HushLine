// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// HUSHLINE — profile config module

package config

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

type Config struct {
	MaxOutputLines int         `json:"max_lines"`
	MaxLineWidth   int         `json:"line_width"`
	StripANSI      bool        `json:"strip_ansi"`
	PreserveErrors bool        `json:"preserve_errors"`
	RequirePermit  bool        `json:"require_permit"`
	MaskPatterns   []string    `json:"mask_patterns"`
	QuietRules     []QuietRule `json:"silence_rules"`
}

type QuietRule struct {
	Name        string `json:"name"`
	Pattern     string `json:"pattern"`
	Replacement string `json:"replacement"`
}

type profilePatch struct {
	MaxOutputLines *int        `json:"max_lines"`
	MaxLineWidth   *int        `json:"line_width"`
	StripANSI      *bool       `json:"strip_ansi"`
	PreserveErrors *bool       `json:"preserve_errors"`
	RequirePermit  *bool       `json:"require_permit"`
	MaskPatterns   []string    `json:"mask_patterns"`
	QuietRules     []QuietRule `json:"silence_rules"`
}

func DefaultProfile() Config {
	return Config{
		MaxOutputLines: 2000,
		MaxLineWidth:   0,
		StripANSI:      true,
		PreserveErrors: true,
		RequirePermit:  false,
		MaskPatterns: []string{
			`AKIA[0-9A-Z]{16}`,
			`sk-[a-zA-Z0-9]{20,}`,
		},
		QuietRules: []QuietRule{
			{Name: "ci-trim", Pattern: `\n+`, Replacement: " "},
			{Name: "collapse-space", Pattern: `[ \t]{2,}`, Replacement: " "},
		},
	}
}

func LoadProfile(cwd string) (Config, error) {
	cfg := DefaultProfile()
	paths := []string{
		GlobalProfilePath(),
		LocalProfilePath(cwd),
	}
	for _, p := range paths {
		if p == "" {
			continue
		}
		next, err := readProfileFile(p)
		if err != nil {
			if os.IsNotExist(err) {
				continue
			}
			return cfg, fmt.Errorf("failed reading config %q: %w", p, err)
		}
		mergePatch(&cfg, next)
	}
	return cfg, nil
}

func readProfileFile(path string) (profilePatch, error) {
	var out profilePatch
	data, err := os.ReadFile(path)
	if err != nil {
		return out, err
	}
	dec := json.NewDecoder(strings.NewReader(string(data)))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&out); err != nil {
		return out, err
	}
	return out, nil
}

func WriteProfile(path string) error {
	cfg := DefaultProfile()
	blob, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return err
	}
	return os.WriteFile(path, append(blob, '\n'), 0o600)
}

func mergePatch(base *Config, next profilePatch) {
	if next.MaxOutputLines != nil && *next.MaxOutputLines > 0 {
		base.MaxOutputLines = *next.MaxOutputLines
	}
	if next.MaxLineWidth != nil && *next.MaxLineWidth >= 0 {
		base.MaxLineWidth = *next.MaxLineWidth
	}
	if next.StripANSI != nil {
		base.StripANSI = *next.StripANSI
	}
	if next.PreserveErrors != nil {
		base.PreserveErrors = *next.PreserveErrors
	}
	if next.RequirePermit != nil {
		base.RequirePermit = *next.RequirePermit
	}
	if len(next.MaskPatterns) > 0 {
		base.MaskPatterns = append(base.MaskPatterns, next.MaskPatterns...)
	}
	if len(next.QuietRules) > 0 {
		base.QuietRules = append(base.QuietRules, next.QuietRules...)
	}
}

func GlobalProfilePath() string {
	base, err := os.UserConfigDir()
	if err != nil {
		return ""
	}
	return filepath.Join(base, "hushline", "profile.json")
}

func LocalProfilePath(cwd string) string {
	return filepath.Join(cwd, ".hushline", "profile.json")
}

func PermitMarkerPath(cwd string) string {
	return filepath.Join(cwd, ".hushline", "permitted")
}

func IsPermitted(cwd string) bool {
	_, err := os.Stat(PermitMarkerPath(cwd))
	return err == nil
}

func MarkPermitted(cwd string) error {
	if err := os.MkdirAll(filepath.Dir(PermitMarkerPath(cwd)), 0o700); err != nil {
		return err
	}
	return os.WriteFile(PermitMarkerPath(cwd), []byte("ok\n"), 0o600)
}
