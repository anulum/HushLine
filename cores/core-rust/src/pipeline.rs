// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// HUSHLINE — pipeline conduit

//! Run a child command and shape its output through the muter.
//!
//! Stdout and stderr are drained concurrently to avoid pipe-buffer deadlock,
//! then shaped line by line. Exit codes mirror the Go core: child code is
//! propagated, a start failure is `2`, a signal kill is `1`, and a timeout is
//! `124`.

use std::io::{Read, Write};
use std::process::{Command, Stdio};
use std::thread;
use std::time::{Duration, Instant};

use crate::muter::Muter;

const TIMEOUT_EXIT: i32 = 124;
const START_FAILURE_EXIT: i32 = 2;
const SIGNAL_EXIT: i32 = 1;
const POLL_INTERVAL: Duration = Duration::from_millis(10);

/// Execute `command` and shape its output, returning the exit code.
#[allow(clippy::too_many_arguments)]
pub fn through(
    command: &str,
    args: &[String],
    out: &mut dyn Write,
    err: &mut dyn Write,
    muter: Option<&Muter>,
    max_output_lines: i64,
    preserve_errors: bool,
    timeout_seconds: i64,
) -> i32 {
    let mut child = match Command::new(command)
        .args(args)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
    {
        Ok(child) => child,
        Err(_) => return START_FAILURE_EXIT,
    };

    let stdout = child.stdout.take().expect("stdout was piped");
    let stderr = child.stderr.take().expect("stderr was piped");
    let out_reader = thread::spawn(move || read_all(stdout));
    let err_reader = thread::spawn(move || read_all(stderr));

    let (code, timed_out) = wait_with_timeout(&mut child, timeout_seconds);

    let out_buf = out_reader.join().unwrap_or_default();
    let err_buf = err_reader.join().unwrap_or_default();

    stream(&out_buf, out, muter, max_output_lines);
    if preserve_errors {
        stream(&err_buf, err, muter, 0);
    }

    if timed_out {
        return TIMEOUT_EXIT;
    }
    match code {
        Some(value) if value >= 0 => value,
        _ => SIGNAL_EXIT,
    }
}

fn wait_with_timeout(child: &mut std::process::Child, timeout_seconds: i64) -> (Option<i32>, bool) {
    if timeout_seconds <= 0 {
        return match child.wait() {
            Ok(status) => (status.code(), false),
            Err(_) => (None, false),
        };
    }
    let deadline = Instant::now() + Duration::from_secs(timeout_seconds as u64);
    loop {
        match child.try_wait() {
            Ok(Some(status)) => return (status.code(), false),
            Ok(None) => {
                if Instant::now() >= deadline {
                    let _ = child.kill();
                    let _ = child.wait();
                    return (None, true);
                }
                thread::sleep(POLL_INTERVAL);
            }
            Err(_) => return (None, false),
        }
    }
}

fn read_all<R: Read>(mut reader: R) -> Vec<u8> {
    let mut buffer = Vec::new();
    let _ = reader.read_to_end(&mut buffer);
    buffer
}

fn stream(buffer: &[u8], writer: &mut dyn Write, muter: Option<&Muter>, max_lines: i64) {
    let text = String::from_utf8_lossy(buffer);
    let mut count: i64 = 0;
    let mut truncated = false;
    for line in text.split_inclusive('\n') {
        if max_lines > 0 && count >= max_lines {
            if !truncated {
                let _ = writeln!(writer, "[output truncated]");
                truncated = true;
            }
            continue;
        }
        let shaped = match muter {
            Some(engine) => engine.apply(line),
            None => line.to_string(),
        };
        let _ = writeln!(writer, "{}", shaped.trim_end_matches('\n'));
        count += 1;
    }
}
