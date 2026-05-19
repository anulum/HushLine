// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// HUSHLINE — muter support utilities

package muter

import (
	"fmt"
	"regexp"

	"github.com/local/hushline/internal/config"
)

type QuietPattern struct {
	Name        string
	Pattern     *regexp.Regexp
	Replacement string
}

type Muter struct {
	rules        []QuietPattern
	maxLineWidth int
}

func Compose(cfg config.Config) (*Muter, error) {
	r := Muter{
		maxLineWidth: cfg.MaxLineWidth,
	}

	rules := make([]QuietPattern, 0, 2+len(cfg.MaskPatterns)+len(cfg.QuietRules))
	if cfg.StripANSI {
		rules = append(rules, QuietPattern{
			Name:        "ansi",
			Pattern:     ansiRe,
			Replacement: "",
		})
	}

	for _, pattern := range cfg.MaskPatterns {
		expr, err := regexp.Compile(pattern)
		if err != nil {
			return nil, fmt.Errorf("invalid redact pattern %q: %w", pattern, err)
		}
		rules = append(rules, QuietPattern{
			Name:        "redact",
			Pattern:     expr,
			Replacement: "***",
		})
	}

	for _, rr := range cfg.QuietRules {
		expr, err := regexp.Compile(rr.Pattern)
		if err != nil {
			return nil, fmt.Errorf("invalid silence pattern %q: %w", rr.Pattern, err)
		}
		rules = append(rules, QuietPattern{
			Name:        rr.Name,
			Pattern:     expr,
			Replacement: rr.Replacement,
		})
	}
	r.rules = rules
	return &r, nil
}

func (f *Muter) Apply(input string) string {
	if f == nil {
		return input
	}
	out := input
	for _, r := range f.rules {
		out = r.Pattern.ReplaceAllString(out, r.Replacement)
	}
	// ansi already included as a first rule but preserve clarity for intent
	if f.maxLineWidth > 0 {
		out = truncate(out, f.maxLineWidth)
	}
	return out
}

var ansiRe = regexp.MustCompile(`\x1b\[[0-9;]*[a-zA-Z]`)

func truncate(input string, max int) string {
	if max <= 0 {
		return input
	}
	if len(input) <= max {
		return input
	}
	return input[:max]
}
