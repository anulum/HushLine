// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// HUSHLINE — profile config module

//! Profile configuration: defaults, strict JSON parsing, and the
//! defaults -> global -> local merge that the Go reference core performs.

use serde::{Deserialize, Serialize};
use std::fs;
use std::io;
use std::path::{Path, PathBuf};

/// A named regex rewrite applied to each output line.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct QuietRule {
    pub name: String,
    pub pattern: String,
    pub replacement: String,
}

/// Resolved muting profile.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Config {
    pub max_output_lines: i64,
    pub max_line_width: i64,
    pub strip_ansi: bool,
    pub preserve_errors: bool,
    pub require_permit: bool,
    pub mask_patterns: Vec<String>,
    pub quiet_rules: Vec<QuietRule>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RulePatch {
    name: Option<String>,
    pattern: Option<String>,
    replacement: Option<String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ProfilePatch {
    max_lines: Option<i64>,
    line_width: Option<i64>,
    strip_ansi: Option<bool>,
    preserve_errors: Option<bool>,
    require_permit: Option<bool>,
    mask_patterns: Option<Vec<String>>,
    silence_rules: Option<Vec<RulePatch>>,
}

#[derive(Serialize)]
struct RuleWire {
    name: String,
    pattern: String,
    replacement: String,
}

#[derive(Serialize)]
struct ProfileWire {
    max_lines: i64,
    line_width: i64,
    strip_ansi: bool,
    preserve_errors: bool,
    require_permit: bool,
    mask_patterns: Vec<String>,
    silence_rules: Vec<RuleWire>,
}

/// Return the built-in default profile (identical to the Go core).
pub fn default_profile() -> Config {
    Config {
        max_output_lines: 2000,
        max_line_width: 0,
        strip_ansi: true,
        preserve_errors: true,
        require_permit: false,
        mask_patterns: vec![
            r"AKIA[0-9A-Z]{16}".to_string(),
            r"sk-[a-zA-Z0-9]{20,}".to_string(),
        ],
        quiet_rules: vec![
            QuietRule {
                name: "ci-trim".to_string(),
                pattern: r"\n+".to_string(),
                replacement: " ".to_string(),
            },
            QuietRule {
                name: "collapse-space".to_string(),
                pattern: r"[ \t]{2,}".to_string(),
                replacement: " ".to_string(),
            },
        ],
    }
}

fn apply_patch(base: &mut Config, patch: ProfilePatch) {
    if let Some(value) = patch.max_lines {
        if value > 0 {
            base.max_output_lines = value;
        }
    }
    if let Some(value) = patch.line_width {
        if value >= 0 {
            base.max_line_width = value;
        }
    }
    if let Some(value) = patch.strip_ansi {
        base.strip_ansi = value;
    }
    if let Some(value) = patch.preserve_errors {
        base.preserve_errors = value;
    }
    if let Some(value) = patch.require_permit {
        base.require_permit = value;
    }
    if let Some(masks) = patch.mask_patterns {
        if !masks.is_empty() {
            base.mask_patterns.extend(masks);
        }
    }
    if let Some(rules) = patch.silence_rules {
        if !rules.is_empty() {
            base.quiet_rules
                .extend(rules.into_iter().map(|r| QuietRule {
                    name: r.name.unwrap_or_default(),
                    pattern: r.pattern.unwrap_or_default(),
                    replacement: r.replacement.unwrap_or_default(),
                }));
        }
    }
}

/// Load the effective profile: defaults -> global -> local.
pub fn load_profile(cwd: &Path) -> Result<Config, String> {
    let mut cfg = default_profile();
    let mut paths: Vec<PathBuf> = Vec::new();
    if let Some(global) = global_profile_path() {
        paths.push(global);
    }
    paths.push(local_profile_path(cwd));

    for path in paths {
        if !path.exists() {
            continue;
        }
        let text = fs::read_to_string(&path)
            .map_err(|e| format!("failed reading config {:?}: {}", path, e))?;
        let patch: ProfilePatch = serde_json::from_str(&text)
            .map_err(|e| format!("failed reading config {:?}: {}", path, e))?;
        apply_patch(&mut cfg, patch);
    }
    Ok(cfg)
}

/// Write the default profile to `path` with restrictive permissions.
pub fn write_profile(path: &Path) -> io::Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
        set_mode(parent, 0o700);
    }
    let cfg = default_profile();
    let wire = ProfileWire {
        max_lines: cfg.max_output_lines,
        line_width: cfg.max_line_width,
        strip_ansi: cfg.strip_ansi,
        preserve_errors: cfg.preserve_errors,
        require_permit: cfg.require_permit,
        mask_patterns: cfg.mask_patterns,
        silence_rules: cfg
            .quiet_rules
            .into_iter()
            .map(|r| RuleWire {
                name: r.name,
                pattern: r.pattern,
                replacement: r.replacement,
            })
            .collect(),
    };
    let mut blob = serde_json::to_string_pretty(&wire).map_err(io::Error::other)?;
    blob.push('\n');
    fs::write(path, blob)?;
    set_mode(path, 0o600);
    Ok(())
}

fn config_base_dir() -> Option<PathBuf> {
    if cfg!(windows) {
        std::env::var_os("AppData").map(PathBuf::from)
    } else if cfg!(target_os = "macos") {
        std::env::var_os("HOME").map(|h| PathBuf::from(h).join("Library/Application Support"))
    } else if let Some(xdg) = std::env::var_os("XDG_CONFIG_HOME") {
        Some(PathBuf::from(xdg))
    } else {
        std::env::var_os("HOME").map(|h| PathBuf::from(h).join(".config"))
    }
}

/// Global profile path, or `None` when no config directory can be resolved.
pub fn global_profile_path() -> Option<PathBuf> {
    config_base_dir().map(|base| base.join("hushline").join("profile.json"))
}

/// Local profile path relative to the working directory.
pub fn local_profile_path(cwd: &Path) -> PathBuf {
    cwd.join(".hushline").join("profile.json")
}

/// Permit marker path relative to the working directory.
pub fn permit_marker_path(cwd: &Path) -> PathBuf {
    cwd.join(".hushline").join("permitted")
}

/// Whether the working directory carries a permit marker.
pub fn is_permitted(cwd: &Path) -> bool {
    permit_marker_path(cwd).exists()
}

/// Create the permit marker for the working directory.
pub fn mark_permitted(cwd: &Path) -> io::Result<()> {
    let marker = permit_marker_path(cwd);
    if let Some(parent) = marker.parent() {
        fs::create_dir_all(parent)?;
        set_mode(parent, 0o700);
    }
    fs::write(&marker, "ok\n")?;
    set_mode(&marker, 0o600);
    Ok(())
}

#[cfg(unix)]
fn set_mode(path: &Path, mode: u32) {
    use std::os::unix::fs::PermissionsExt;
    let _ = fs::set_permissions(path, fs::Permissions::from_mode(mode));
}

#[cfg(not(unix))]
fn set_mode(_path: &Path, _mode: u32) {}
