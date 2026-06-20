// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// HUSHLINE — muter support utilities

//! Line shaping: ANSI stripping, secret redaction, and silence rewrites.
//!
//! Rules run in the same order as the Go core: ANSI removal first (when
//! enabled), then each mask pattern replaced with `***`, then the configured
//! silence rules. Finally, a positive line width truncates the line to that many
//! bytes, matching Go's byte-slice truncation.

use regex::Regex;

use crate::config::Config;

const MASK_REPLACEMENT: &str = "***";

struct Rule {
    pattern: Regex,
    replacement: String,
}

/// Applies the composed rule chain to a single line of text.
pub struct Muter {
    rules: Vec<Rule>,
    max_line_width: i64,
}

impl Muter {
    /// Shape one line through every rule, then truncate to the byte width.
    pub fn apply(&self, line: &str) -> String {
        let mut out = line.to_string();
        for rule in &self.rules {
            out = rule
                .pattern
                .replace_all(&out, rule.replacement.as_str())
                .into_owned();
        }
        if self.max_line_width > 0 {
            out = truncate(&out, self.max_line_width as usize);
        }
        out
    }
}

/// Build a [`Muter`] from a resolved profile.
///
/// Returns an error if any mask or silence pattern fails to compile, mirroring
/// the Go core's refusal to run with an invalid profile.
pub fn compose(cfg: &Config) -> Result<Muter, String> {
    let mut rules: Vec<Rule> = Vec::new();

    if cfg.strip_ansi {
        rules.push(Rule {
            pattern: ansi_regex(),
            replacement: String::new(),
        });
    }

    for pattern in &cfg.mask_patterns {
        rules.push(Rule {
            pattern: compile(pattern, "invalid redact pattern")?,
            replacement: MASK_REPLACEMENT.to_string(),
        });
    }

    for rule in &cfg.quiet_rules {
        rules.push(Rule {
            pattern: compile(&rule.pattern, "invalid silence pattern")?,
            replacement: rule.replacement.clone(),
        });
    }

    Ok(Muter {
        rules,
        max_line_width: cfg.max_line_width,
    })
}

fn ansi_regex() -> Regex {
    Regex::new(r"\x1b\[[0-9;]*[a-zA-Z]").expect("static ANSI pattern is valid")
}

fn compile(pattern: &str, label: &str) -> Result<Regex, String> {
    Regex::new(pattern).map_err(|e| format!("{} {:?}: {}", label, pattern, e))
}

/// Truncate `text` to at most `max_bytes` UTF-8 bytes on a char boundary.
///
/// Go slices the raw byte buffer; we bound by byte length the same way but step
/// back to the nearest char boundary so a cut inside a multi-byte rune never
/// yields invalid UTF-8.
fn truncate(text: &str, max_bytes: usize) -> String {
    if text.len() <= max_bytes {
        return text.to_string();
    }
    let mut end = max_bytes;
    while end > 0 && !text.is_char_boundary(end) {
        end -= 1;
    }
    text[..end].to_string()
}
