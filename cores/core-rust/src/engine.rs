// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// HUSHLINE — core engine bootstrap

//! Command dispatch for the Rust core.
//!
//! Flags are parsed with the same semantics as Go's `flag` package: parsing
//! stops at the first non-flag token or `--`, and boolean flags take no
//! following argument. Output streams and the working directory are injected so
//! the behaviour is fully testable.

use std::collections::HashMap;
use std::io::Write;
use std::path::Path;

use crate::config;
use crate::muter;
use crate::pipeline;
use crate::VERSION;

const USAGE: &str = "hushline - local command output shaping utility

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
";

enum FlagValue {
    Bool(bool),
    Int(i64),
}

/// Execute the Hushline command described by `args`.
pub fn run(args: &[String], out: &mut dyn Write, err: &mut dyn Write, cwd: &Path) -> i32 {
    if args.is_empty() || matches!(args[0].as_str(), "help" | "-h" | "--help") {
        let _ = write!(out, "{}", USAGE);
        return 0;
    }
    match args[0].as_str() {
        "mute" => mute(&args[1..], out, err, cwd),
        "manifest" => manifest(&args[1..], out, err, cwd),
        "permit" => permit(&args[1..], out, err, cwd),
        "version" => {
            let _ = writeln!(out, "hushline {}", VERSION);
            0
        }
        other => {
            let _ = write!(out, "unknown command: {}\n\n", other);
            let _ = write!(out, "{}", USAGE);
            1
        }
    }
}

fn manifest(args: &[String], out: &mut dyn Write, err: &mut dyn Write, cwd: &Path) -> i32 {
    if args.is_empty() || args[0] == "show" {
        let global = config::global_profile_path()
            .map(|p| p.display().to_string())
            .unwrap_or_default();
        let _ = writeln!(out, "global profile: {}", global);
        let _ = writeln!(
            out,
            "local profile:  {}",
            config::local_profile_path(cwd).display()
        );
        return 0;
    }
    if args[0] != "init" {
        let _ = writeln!(err, "manifest: unknown action \"{}\"", args[0]);
        return 2;
    }

    let (flags, _) = match parse_flags(&args[1..], &["global", "local"], &[]) {
        Ok(parsed) => parsed,
        Err(message) => {
            let _ = writeln!(err, "manifest options: {}", message);
            return 2;
        }
    };

    let write_global = flag_bool(&flags, "global");
    let write_local = flag_bool(&flags, "local");
    match emit_profile(write_global, write_local, cwd, out) {
        Ok(()) => 0,
        Err(message) => {
            let _ = writeln!(err, "manifest init: {}", message);
            1
        }
    }
}

fn permit(args: &[String], out: &mut dyn Write, err: &mut dyn Write, cwd: &Path) -> i32 {
    let action = args.first().map(String::as_str).unwrap_or("status");
    match action {
        "status" => {
            if config::is_permitted(cwd) {
                let _ = writeln!(out, "permitted: true");
                0
            } else {
                let _ = writeln!(out, "permitted: false");
                2
            }
        }
        "allow" => {
            let target = args
                .get(1)
                .cloned()
                .unwrap_or_else(|| cwd.to_string_lossy().into_owned());
            match config::mark_permitted(Path::new(&target)) {
                Ok(()) => {
                    let _ = writeln!(out, "permitted: {}", target);
                    0
                }
                Err(error) => {
                    let _ = writeln!(err, "permit allow: {}", error);
                    1
                }
            }
        }
        other => {
            let _ = writeln!(err, "permit: unknown action \"{}\"", other);
            2
        }
    }
}

fn mute(args: &[String], out: &mut dyn Write, err: &mut dyn Write, cwd: &Path) -> i32 {
    let (flags, rest) = match parse_flags(
        args,
        &["raw", "pipe-errors"],
        &["max-lines", "max-width", "timeout"],
    ) {
        Ok(parsed) => parsed,
        Err(message) => {
            let _ = writeln!(err, "mute options: {}", message);
            return 2;
        }
    };

    if rest.is_empty() {
        let _ = writeln!(err, "mute: missing command");
        return 2;
    }

    let mut profile = match config::load_profile(cwd) {
        Ok(profile) => profile,
        Err(message) => {
            let _ = writeln!(err, "profile: {}", message);
            return 1;
        }
    };

    let max_lines = flag_int(&flags, "max-lines");
    let max_width = flag_int(&flags, "max-width");
    if max_lines > 0 {
        profile.max_output_lines = max_lines;
    }
    if max_width > 0 {
        profile.max_line_width = max_width;
    }
    profile.preserve_errors = flag_bool_default(&flags, "pipe-errors", true);

    if profile.require_permit && !config::is_permitted(cwd) {
        let _ = writeln!(
            err,
            "hushline: current directory not permitted. run `hushline permit allow` first or set require_permit: false"
        );
        return 3;
    }

    let silence = if flag_bool(&flags, "raw") {
        None
    } else {
        match muter::compose(&profile) {
            Ok(engine) => Some(engine),
            Err(message) => {
                let _ = writeln!(err, "mute: {}", message);
                return 1;
            }
        }
    };

    let code = pipeline::through(
        &rest[0],
        &rest[1..],
        out,
        err,
        silence.as_ref(),
        profile.max_output_lines,
        profile.preserve_errors,
        flag_int(&flags, "timeout"),
    );
    if code == 124 {
        let _ = writeln!(err, "hushline: command timed out");
    }
    code
}

fn emit_profile(
    write_global: bool,
    write_local: bool,
    cwd: &Path,
    out: &mut dyn Write,
) -> Result<(), String> {
    let target = if write_local && !write_global {
        config::local_profile_path(cwd)
    } else {
        match config::global_profile_path() {
            Some(path) => path,
            None => return Err("could not resolve profile path".to_string()),
        }
    };
    config::write_profile(&target).map_err(|e| e.to_string())?;
    let _ = writeln!(out, "profile written: {}", target.display());
    Ok(())
}

fn parse_flags(
    args: &[String],
    bool_flags: &[&str],
    int_flags: &[&str],
) -> Result<(HashMap<String, FlagValue>, Vec<String>), String> {
    let mut flags: HashMap<String, FlagValue> = HashMap::new();
    let mut index = 0;
    while index < args.len() {
        let token = &args[index];
        if token == "--" {
            return Ok((flags, args[index + 1..].to_vec()));
        }
        if !(token.len() > 1 && token.starts_with('-')) {
            return Ok((flags, args[index..].to_vec()));
        }

        let body = token.trim_start_matches('-');
        let (name, value, has_value) = match body.split_once('=') {
            Some((name, value)) => (name, value.to_string(), true),
            None => (body, String::new(), false),
        };

        if bool_flags.contains(&name) {
            let parsed = if has_value {
                parse_bool(name, &value)?
            } else {
                true
            };
            flags.insert(name.to_string(), FlagValue::Bool(parsed));
        } else if int_flags.contains(&name) {
            let raw = if has_value {
                value
            } else {
                index += 1;
                if index >= args.len() {
                    return Err(format!("flag needs an argument: -{}", name));
                }
                args[index].clone()
            };
            let parsed = raw
                .parse::<i64>()
                .map_err(|_| format!("invalid value {:?} for -{}", raw, name))?;
            flags.insert(name.to_string(), FlagValue::Int(parsed));
        } else {
            return Err(format!("flag provided but not defined: -{}", name));
        }
        index += 1;
    }
    Ok((flags, Vec::new()))
}

fn parse_bool(name: &str, value: &str) -> Result<bool, String> {
    match value {
        "1" | "t" | "T" | "TRUE" | "true" | "True" => Ok(true),
        "0" | "f" | "F" | "FALSE" | "false" | "False" => Ok(false),
        _ => Err(format!("invalid boolean value {:?} for -{}", value, name)),
    }
}

fn flag_bool(flags: &HashMap<String, FlagValue>, name: &str) -> bool {
    flag_bool_default(flags, name, false)
}

fn flag_bool_default(flags: &HashMap<String, FlagValue>, name: &str, fallback: bool) -> bool {
    match flags.get(name) {
        Some(FlagValue::Bool(value)) => *value,
        _ => fallback,
    }
}

fn flag_int(flags: &HashMap<String, FlagValue>, name: &str) -> i64 {
    match flags.get(name) {
        Some(FlagValue::Int(value)) => *value,
        _ => 0,
    }
}
