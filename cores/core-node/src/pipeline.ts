// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// HUSHLINE — pipeline conduit

// Run a child command and shape its output through the muter. Exit codes mirror
// the Go core: child code is propagated, a start failure is 2, a signal kill is
// 1, and a timeout is 124.

import { spawnSync } from "node:child_process";

import { Muter } from "./muter";

export type Writer = (text: string) => void;

const TIMEOUT_EXIT = 124;
const START_FAILURE_EXIT = 2;
const SIGNAL_EXIT = 1;
const MAX_BUFFER = 64 * 1024 * 1024;

export function through(
  command: string,
  args: string[],
  out: Writer,
  err: Writer,
  muter: Muter | null,
  maxOutputLines: number,
  preserveErrors: boolean,
  timeoutSeconds: number,
): number {
  const result = spawnSync(command, args, {
    timeout: timeoutSeconds > 0 ? timeoutSeconds * 1000 : undefined,
    maxBuffer: MAX_BUFFER,
  });

  const errorCode = (result.error as NodeJS.ErrnoException | undefined)?.code;
  const timedOut = timeoutSeconds > 0 && result.error !== undefined && errorCode === "ETIMEDOUT";

  if (result.error && !timedOut) {
    return START_FAILURE_EXIT;
  }

  stream(result.stdout, out, muter, maxOutputLines);
  if (preserveErrors) {
    stream(result.stderr, err, muter, 0);
  }

  if (timedOut) {
    return TIMEOUT_EXIT;
  }
  if (result.status === null) {
    return SIGNAL_EXIT;
  }
  return result.status;
}

function splitLines(text: string): string[] {
  const lines: string[] = [];
  let start = 0;
  for (let i = 0; i < text.length; i += 1) {
    if (text[i] === "\n") {
      lines.push(text.slice(start, i + 1));
      start = i + 1;
    }
  }
  if (start < text.length) {
    lines.push(text.slice(start));
  }
  return lines;
}

function stream(buffer: Buffer | null, write: Writer, muter: Muter | null, maxLines: number): void {
  if (!buffer || buffer.length === 0) {
    return;
  }
  const text = buffer.toString("utf8");
  let count = 0;
  let truncated = false;
  for (const line of splitLines(text)) {
    if (maxLines > 0 && count >= maxLines) {
      if (!truncated) {
        write("[output truncated]\n");
        truncated = true;
      }
      continue;
    }
    const shaped = muter ? muter.apply(line) : line;
    write(shaped.replace(/\n+$/, "") + "\n");
    count += 1;
  }
}
