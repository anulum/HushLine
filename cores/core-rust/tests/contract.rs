// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// HUSHLINE — Rust core contract tests

use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Mutex;

use hushline_rust_core::config::{self, Config, QuietRule};
use hushline_rust_core::{engine, muter, pipeline};

static ENV_LOCK: Mutex<()> = Mutex::new(());
static COUNTER: AtomicUsize = AtomicUsize::new(0);

struct Workspace {
    _guard: std::sync::MutexGuard<'static, ()>,
    work: PathBuf,
}

fn workspace() -> Workspace {
    let guard = ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
    let n = COUNTER.fetch_add(1, Ordering::SeqCst);
    let base = std::env::temp_dir().join(format!("hushline_rs_{}_{}", std::process::id(), n));
    let xdg = base.join("xdg");
    let work = base.join("work");
    fs::create_dir_all(&xdg).unwrap();
    fs::create_dir_all(&work).unwrap();
    std::env::set_var("XDG_CONFIG_HOME", &xdg);
    Workspace {
        _guard: guard,
        work,
    }
}

fn run(args: &[&str], cwd: &Path) -> (i32, String, String) {
    let argv: Vec<String> = args.iter().map(|s| s.to_string()).collect();
    let mut out = Vec::new();
    let mut err = Vec::new();
    let code = engine::run(&argv, &mut out, &mut err, cwd);
    (
        code,
        String::from_utf8_lossy(&out).into_owned(),
        String::from_utf8_lossy(&err).into_owned(),
    )
}

fn write_local_profile(work: &Path, json: &str) {
    let target = work.join(".hushline").join("profile.json");
    fs::create_dir_all(target.parent().unwrap()).unwrap();
    fs::write(target, json).unwrap();
}

fn secret() -> String {
    format!("sk-{}", "abcdefghijklmnopqrstuvwxyz")
}

// ----- dispatch -----

#[test]
fn version_prints_in_lockstep() {
    let ws = workspace();
    let (code, out, _) = run(&["version"], &ws.work);
    assert_eq!(code, 0);
    assert_eq!(out, "hushline 0.1.5\n");
}

#[test]
fn help_and_empty_show_usage() {
    let ws = workspace();
    for args in [vec![], vec!["help"], vec!["-h"], vec!["--help"]] {
        let (code, out, _) = run(&args, &ws.work);
        assert_eq!(code, 0);
        assert!(out.contains("local command output shaping utility"));
    }
}

#[test]
fn unknown_command_is_one() {
    let ws = workspace();
    let (code, out, _) = run(&["wat"], &ws.work);
    assert_eq!(code, 1);
    assert!(out.contains("unknown command: wat"));
}

// ----- manifest -----

#[test]
fn manifest_show_lists_paths() {
    let ws = workspace();
    let (code, out, _) = run(&["manifest"], &ws.work);
    assert_eq!(code, 0);
    assert!(out.contains("global profile:"));
    assert!(out.contains("local profile:"));
    assert_eq!(run(&["manifest", "show"], &ws.work).1, out);
}

#[test]
fn manifest_init_global_and_local() {
    let ws = workspace();
    assert_eq!(run(&["manifest", "init", "--global"], &ws.work).0, 0);
    assert!(config::global_profile_path().unwrap().exists());
    assert_eq!(run(&["manifest", "init", "--local"], &ws.work).0, 0);
    assert!(config::local_profile_path(&ws.work).exists());
}

#[test]
fn manifest_init_default_and_both_are_global() {
    let ws = workspace();
    run(&["manifest", "init"], &ws.work);
    assert!(config::global_profile_path().unwrap().exists());
    assert!(!config::local_profile_path(&ws.work).exists());
    run(&["manifest", "init", "--global", "--local"], &ws.work);
    assert!(!config::local_profile_path(&ws.work).exists());
}

#[test]
fn manifest_unknown_action_and_bad_flag() {
    let ws = workspace();
    let (code, _, err) = run(&["manifest", "huh"], &ws.work);
    assert_eq!(code, 2);
    assert!(err.contains("unknown action"));
    let (code, _, err) = run(&["manifest", "init", "--bogus"], &ws.work);
    assert_eq!(code, 2);
    assert!(err.contains("manifest options"));
}

// ----- permit -----

#[test]
fn permit_status_allow_status_round_trip() {
    let ws = workspace();
    let (code, out, _) = run(&["permit", "status"], &ws.work);
    assert_eq!(code, 2);
    assert_eq!(out, "permitted: false\n");

    let (code, out, _) = run(&["permit", "allow"], &ws.work);
    assert_eq!(code, 0);
    assert!(out.contains("permitted:"));

    let (code, out, _) = run(&["permit"], &ws.work);
    assert_eq!(code, 0);
    assert_eq!(out, "permitted: true\n");
}

#[test]
fn permit_allow_explicit_path_and_unknown_action() {
    let ws = workspace();
    let target = ws.work.join("elsewhere");
    let target_str = target.to_string_lossy().into_owned();
    let (code, out, _) = run(&["permit", "allow", &target_str], &ws.work);
    assert_eq!(code, 0);
    assert!(out.contains(&target_str));
    assert!(config::is_permitted(&target));

    let (code, _, err) = run(&["permit", "wat"], &ws.work);
    assert_eq!(code, 2);
    assert!(err.contains("unknown action"));
}

// ----- mute -----

#[test]
fn mute_missing_command_is_two() {
    let ws = workspace();
    let (code, _, err) = run(&["mute"], &ws.work);
    assert_eq!(code, 2);
    assert!(err.contains("missing command"));
}

#[test]
fn mute_redacts_secret() {
    let ws = workspace();
    let arg = format!("{}\\n", secret());
    let (code, out, _) = run(&["mute", "--", "printf", &arg], &ws.work);
    assert_eq!(code, 0);
    assert!(!out.contains(&secret()));
    assert!(out.contains("***"));
}

#[test]
fn mute_raw_keeps_secret() {
    let ws = workspace();
    let arg = format!("{}\\n", secret());
    let (code, out, _) = run(&["mute", "--raw", "--", "printf", &arg], &ws.work);
    assert_eq!(code, 0);
    assert!(out.contains(&secret()));
}

#[test]
fn mute_pipe_errors_false_discards_stderr() {
    let ws = workspace();
    let (code, _, err) = run(
        &[
            "mute",
            "--pipe-errors=false",
            "--",
            "sh",
            "-c",
            "printf boom 1>&2",
        ],
        &ws.work,
    );
    assert_eq!(code, 0);
    assert!(!err.contains("boom"));
}

#[test]
fn mute_max_lines_marker() {
    let ws = workspace();
    let (code, out, _) = run(
        &[
            "mute",
            "--max-lines",
            "1",
            "--raw",
            "--",
            "printf",
            "a\\nb\\nc\\n",
        ],
        &ws.work,
    );
    assert_eq!(code, 0);
    let lines: Vec<&str> = out.lines().collect();
    assert_eq!(lines, vec!["a", "[output truncated]"]);
}

#[test]
fn mute_max_width_truncates() {
    let ws = workspace();
    let (code, out, _) = run(
        &["mute", "--max-width=3", "--", "printf", "abcdef\\n"],
        &ws.work,
    );
    assert_eq!(code, 0);
    assert_eq!(out, "abc\n");
}

#[test]
fn mute_timeout_is_124() {
    let ws = workspace();
    let (code, _, err) = run(
        &["mute", "--timeout", "1", "--", "sh", "-c", "sleep 5"],
        &ws.work,
    );
    assert_eq!(code, 124);
    assert!(err.contains("timed out"));
}

#[test]
fn mute_require_permit_gate_and_satisfied() {
    let ws = workspace();
    write_local_profile(&ws.work, r#"{"require_permit": true}"#);
    let (code, _, err) = run(&["mute", "--", "printf", "hi\\n"], &ws.work);
    assert_eq!(code, 3);
    assert!(err.contains("not permitted"));

    config::mark_permitted(&ws.work).unwrap();
    let (code, out, _) = run(&["mute", "--raw", "--", "printf", "hi\\n"], &ws.work);
    assert_eq!(code, 0);
    assert_eq!(out, "hi\n");
}

#[test]
fn mute_invalid_mask_pattern_is_one() {
    let ws = workspace();
    write_local_profile(&ws.work, r#"{"mask_patterns": ["(unclosed"]}"#);
    let (code, _, err) = run(&["mute", "--", "printf", "x\\n"], &ws.work);
    assert_eq!(code, 1);
    assert!(err.contains("mute:"));
}

#[test]
fn mute_profile_load_error_is_one() {
    let ws = workspace();
    write_local_profile(&ws.work, "{bad");
    let (code, _, err) = run(&["mute", "--", "printf", "x\\n"], &ws.work);
    assert_eq!(code, 1);
    assert!(err.contains("profile:"));
}

#[test]
fn mute_flag_errors() {
    let ws = workspace();
    assert_eq!(
        run(&["mute", "--raw=maybe", "--", "printf", "x"], &ws.work).0,
        2
    );
    assert_eq!(run(&["mute", "--nope", "--", "printf", "x"], &ws.work).0, 2);
    assert_eq!(run(&["mute", "--timeout"], &ws.work).0, 2);
    assert_eq!(
        run(&["mute", "--timeout=x", "--", "printf", "x"], &ws.work).0,
        2
    );
}

#[test]
fn mute_non_flag_stops_parsing() {
    let ws = workspace();
    let (code, out, _) = run(&["mute", "printf", "hi\\n"], &ws.work);
    assert_eq!(code, 0);
    assert!(out.contains("hi"));
}

// ----- config -----

#[test]
fn default_profile_matches_reference() {
    let cfg = config::default_profile();
    assert_eq!(cfg.max_output_lines, 2000);
    assert!(cfg.strip_ansi);
    assert_eq!(cfg.mask_patterns.len(), 2);
    assert_eq!(cfg.quiet_rules[0].name, "ci-trim");
}

#[test]
fn merge_overrides_and_appends() {
    let ws = workspace();
    write_local_profile(
        &ws.work,
        r#"{"max_lines": 50, "strip_ansi": false, "mask_patterns": ["X"], "silence_rules": [{"name":"n","pattern":"a","replacement":"b"}]}"#,
    );
    let cfg = config::load_profile(&ws.work).unwrap();
    assert_eq!(cfg.max_output_lines, 50);
    assert!(!cfg.strip_ansi);
    assert_eq!(cfg.mask_patterns.len(), 3);
    assert_eq!(cfg.quiet_rules.len(), 3);
}

#[test]
fn merge_ignores_zero_and_negative_and_empty_lists() {
    let ws = workspace();
    write_local_profile(
        &ws.work,
        r#"{"max_lines": 0, "line_width": -5, "mask_patterns": [], "silence_rules": []}"#,
    );
    let cfg = config::load_profile(&ws.work).unwrap();
    assert_eq!(cfg.max_output_lines, 2000);
    assert_eq!(cfg.max_line_width, 0);
    assert_eq!(cfg.mask_patterns.len(), 2);
}

#[test]
fn strict_parse_rejects_unknown_key() {
    let ws = workspace();
    write_local_profile(&ws.work, r#"{"unknown": 1}"#);
    assert!(config::load_profile(&ws.work).is_err());
}

// ----- muter -----

#[test]
fn muter_redacts_and_strips_ansi() {
    let m = muter::compose(&config::default_profile()).unwrap();
    let input = format!("\x1b[31mtoken {}\x1b[0m   tail", secret());
    let out = m.apply(&input);
    assert!(!out.contains(&secret()));
    assert!(out.contains("***"));
    assert!(!out.contains('\x1b'));
    assert!(!out.contains("   "));
}

#[test]
fn muter_order_and_truncation() {
    let cfg = Config {
        max_output_lines: 2000,
        max_line_width: 4,
        strip_ansi: false,
        preserve_errors: true,
        require_permit: false,
        mask_patterns: vec![],
        quiet_rules: vec![
            QuietRule {
                name: "a".into(),
                pattern: "a".into(),
                replacement: "b".into(),
            },
            QuietRule {
                name: "b".into(),
                pattern: "b".into(),
                replacement: "c".into(),
            },
        ],
    };
    let m = muter::compose(&cfg).unwrap();
    // "a" -> "b" (first rule) -> "c" (second rule): order is significant.
    assert_eq!(m.apply("a"), "c");
}

#[test]
fn muter_truncates_plain_ascii_to_byte_width() {
    let cfg = Config {
        max_output_lines: 2000,
        max_line_width: 4,
        strip_ansi: false,
        preserve_errors: true,
        require_permit: false,
        mask_patterns: vec![],
        quiet_rules: vec![],
    };
    assert_eq!(muter::compose(&cfg).unwrap().apply("abcdef"), "abcd");
}

#[test]
fn muter_truncation_respects_char_boundary() {
    let cfg = Config {
        max_output_lines: 2000,
        max_line_width: 2,
        strip_ansi: false,
        preserve_errors: true,
        require_permit: false,
        mask_patterns: vec![],
        quiet_rules: vec![],
    };
    let m = muter::compose(&cfg).unwrap();
    assert_eq!(m.apply("aéb"), "a");
}

#[test]
fn muter_invalid_pattern_errors() {
    let cfg = Config {
        max_output_lines: 2000,
        max_line_width: 0,
        strip_ansi: false,
        preserve_errors: true,
        require_permit: false,
        mask_patterns: vec!["(".into()],
        quiet_rules: vec![],
    };
    assert!(muter::compose(&cfg).is_err());
}

// ----- pipeline -----

fn pipe(
    command: &str,
    args: &[&str],
    max_lines: i64,
    preserve: bool,
    timeout: i64,
    redact: bool,
) -> (i32, String, String) {
    let argv: Vec<String> = args.iter().map(|s| s.to_string()).collect();
    let m = if redact {
        Some(muter::compose(&config::default_profile()).unwrap())
    } else {
        None
    };
    let mut out = Vec::new();
    let mut err = Vec::new();
    let code = pipeline::through(
        command,
        &argv,
        &mut out,
        &mut err,
        m.as_ref(),
        max_lines,
        preserve,
        timeout,
    );
    (
        code,
        String::from_utf8_lossy(&out).into_owned(),
        String::from_utf8_lossy(&err).into_owned(),
    )
}

#[test]
fn pipeline_passthrough_and_exit_code() {
    let (code, out, err) = pipe("printf", &["one\\ntwo\\n"], 2000, true, 0, false);
    assert_eq!(code, 0);
    assert_eq!(out, "one\ntwo\n");
    assert_eq!(err, "");
    assert_eq!(pipe("sh", &["-c", "exit 7"], 2000, true, 0, false).0, 7);
}

#[test]
fn pipeline_start_failure_and_signal() {
    assert_eq!(
        pipe("hushline-no-such-binary-xyz", &[], 2000, true, 0, false).0,
        2
    );
    assert_eq!(pipe("sh", &["-c", "kill -9 $$"], 2000, true, 0, false).0, 1);
}

#[test]
fn pipeline_timeout() {
    assert_eq!(pipe("sh", &["-c", "sleep 5"], 2000, true, 1, false).0, 124);
}

#[test]
fn pipeline_stderr_modes() {
    let (_, _, err) = pipe("sh", &["-c", "printf oops 1>&2"], 2000, true, 0, false);
    assert!(err.contains("oops"));
    let (_, _, err) = pipe("sh", &["-c", "printf oops 1>&2"], 2000, false, 0, false);
    assert_eq!(err, "");
}
