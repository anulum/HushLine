// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// HUSHLINE — muter support utilities

// Line shaping: ANSI stripping, secret redaction, and silence rewrites.
// Rules run in the same order as the Go core: ANSI removal first (when enabled),
// then each mask pattern replaced with "***", then the configured silence rules.
// Finally, a positive line width truncates the line to that many UTF-8 bytes.

import { Config } from "./config";

const ANSI_PATTERN = "\\x1b\\[[0-9;]*[a-zA-Z]";
const MASK_REPLACEMENT = "***";

interface Rule {
  pattern: RegExp;
  replacement: string;
}

export class MuterError extends Error {}

export class Muter {
  private readonly rules: Rule[];
  private readonly maxLineWidth: number;

  constructor(rules: Rule[], maxLineWidth: number) {
    this.rules = rules;
    this.maxLineWidth = maxLineWidth;
  }

  apply(line: string): string {
    let out = line;
    for (const rule of this.rules) {
      out = out.replace(rule.pattern, rule.replacement);
    }
    if (this.maxLineWidth > 0) {
      out = truncateBytes(out, this.maxLineWidth);
    }
    return out;
  }
}

export function compose(cfg: Config): Muter {
  const rules: Rule[] = [];

  if (cfg.stripAnsi) {
    rules.push({ pattern: compile(ANSI_PATTERN, "invalid redact pattern"), replacement: "" });
  }
  for (const pattern of cfg.maskPatterns) {
    rules.push({ pattern: compile(pattern, "invalid redact pattern"), replacement: MASK_REPLACEMENT });
  }
  for (const rule of cfg.quietRules) {
    rules.push({ pattern: compile(rule.pattern, "invalid silence pattern"), replacement: rule.replacement });
  }

  return new Muter(rules, cfg.maxLineWidth);
}

function compile(pattern: string, label: string): RegExp {
  try {
    return new RegExp(pattern, "g");
  } catch (error) {
    throw new MuterError(`${label} '${pattern}': ${(error as Error).message}`);
  }
}

// Truncate to at most maxBytes UTF-8 bytes, stepping back to a rune boundary so
// a cut inside a multi-byte character never yields a replacement char.
function truncateBytes(text: string, maxBytes: number): string {
  const buffer = Buffer.from(text, "utf8");
  if (buffer.length <= maxBytes) {
    return text;
  }
  let end = maxBytes;
  while (end > 0 && (buffer[end] & 0xc0) === 0x80) {
    end -= 1;
  }
  return buffer.subarray(0, end).toString("utf8");
}
