# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# HUSHLINE — pipeline conduit

"""Run a child command and stream its output through the muter.

Stdout and stderr are read concurrently. Stdout is bounded by ``max_output_lines``
(emitting a single ``[output truncated]`` marker once the bound is hit); stderr is
shaped through the muter when ``preserve_errors`` is set, otherwise drained. Exit
codes mirror the Go core: child code is propagated, a start failure is ``2``, a
signal kill is ``1``, and a timeout is ``124``.
"""

from __future__ import annotations

import subprocess
from threading import Thread
from typing import BinaryIO, Sequence, TextIO

from hushline_core.muter import Muter

_TIMEOUT_EXIT = 124
_START_FAILURE_EXIT = 2
_SIGNAL_EXIT = 1


def through(
    command: str,
    args: Sequence[str],
    out_writer: TextIO,
    err_writer: TextIO,
    muter: Muter | None,
    max_output_lines: int,
    preserve_errors: bool,
    timeout_seconds: int,
) -> int:
    """Execute ``command`` and shape its output, returning the exit code."""
    try:
        proc = subprocess.Popen(
            [command, *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError:
        return _START_FAILURE_EXIT

    workers: list[Thread] = []
    assert proc.stdout is not None and proc.stderr is not None

    out_worker = Thread(
        target=_stream, args=(proc.stdout, out_writer, muter, max_output_lines)
    )
    out_worker.start()
    workers.append(out_worker)

    if preserve_errors:
        err_worker = Thread(target=_stream, args=(proc.stderr, err_writer, muter, 0))
    else:
        err_worker = Thread(target=_drain, args=(proc.stderr,))
    err_worker.start()
    workers.append(err_worker)

    timed_out = False
    try:
        if timeout_seconds and timeout_seconds > 0:
            proc.wait(timeout=timeout_seconds)
        else:
            proc.wait()
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.kill()
        proc.wait()

    for worker in workers:
        worker.join()

    if timed_out:
        return _TIMEOUT_EXIT

    code = proc.returncode
    if code is None or code < 0:
        return _SIGNAL_EXIT
    return code


def _stream(
    reader: BinaryIO, writer: TextIO, muter: Muter | None, max_lines: int
) -> None:
    count = 0
    truncated = False
    while True:
        raw = reader.readline()
        if not raw:
            return
        line = raw.decode("utf-8", errors="replace")
        if max_lines > 0 and count >= max_lines:
            if not truncated:
                writer.write("[output truncated]\n")
                truncated = True
            continue
        if muter is not None:
            line = muter.apply(line)
        writer.write(line.rstrip("\n") + "\n")
        count += 1


def _drain(reader: BinaryIO) -> None:
    while reader.readline():
        pass
