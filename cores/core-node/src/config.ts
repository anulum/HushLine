// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// HUSHLINE — profile config module

// Profile configuration: defaults, strict JSON parsing, and the
// defaults -> global -> local merge that the Go reference core performs.

import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";

export interface QuietRule {
  name: string;
  pattern: string;
  replacement: string;
}

export interface Config {
  maxOutputLines: number;
  maxLineWidth: number;
  stripAnsi: boolean;
  preserveErrors: boolean;
  requirePermit: boolean;
  maskPatterns: string[];
  quietRules: QuietRule[];
}

export class ProfileError extends Error {}

const PROFILE_KEYS = new Set([
  "max_lines",
  "line_width",
  "strip_ansi",
  "preserve_errors",
  "require_permit",
  "mask_patterns",
  "silence_rules",
]);
const RULE_KEYS = new Set(["name", "pattern", "replacement"]);

export function defaultProfile(): Config {
  return {
    maxOutputLines: 2000,
    maxLineWidth: 0,
    stripAnsi: true,
    preserveErrors: true,
    requirePermit: false,
    maskPatterns: ["AKIA[0-9A-Z]{16}", "sk-[a-zA-Z0-9]{20,}"],
    quietRules: [
      { name: "ci-trim", pattern: "\\n+", replacement: " " },
      { name: "collapse-space", pattern: "[ \\t]{2,}", replacement: " " },
    ],
  };
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseRule(raw: unknown, source: string): QuietRule {
  if (!isPlainObject(raw)) {
    throw new ProfileError(`${source}: silence rule must be an object`);
  }
  for (const key of Object.keys(raw)) {
    if (!RULE_KEYS.has(key)) {
      throw new ProfileError(`${source}: unknown silence rule field: ${key}`);
    }
  }
  const { name = "", pattern = "", replacement = "" } = raw as Record<string, unknown>;
  if (
    typeof name !== "string" ||
    typeof pattern !== "string" ||
    typeof replacement !== "string"
  ) {
    throw new ProfileError(`${source}: silence rule fields must be strings`);
  }
  return { name, pattern, replacement };
}

function isInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value);
}

function applyPatch(base: Config, raw: Record<string, unknown>, source: string): void {
  for (const key of Object.keys(raw)) {
    if (!PROFILE_KEYS.has(key)) {
      throw new ProfileError(`${source}: unknown field: ${key}`);
    }
  }

  if ("max_lines" in raw) {
    if (!isInteger(raw.max_lines)) {
      throw new ProfileError(`${source}: max_lines must be an integer`);
    }
    if (raw.max_lines > 0) {
      base.maxOutputLines = raw.max_lines;
    }
  }
  if ("line_width" in raw) {
    if (!isInteger(raw.line_width)) {
      throw new ProfileError(`${source}: line_width must be an integer`);
    }
    if (raw.line_width >= 0) {
      base.maxLineWidth = raw.line_width;
    }
  }
  for (const [key, field] of [
    ["strip_ansi", "stripAnsi"],
    ["preserve_errors", "preserveErrors"],
    ["require_permit", "requirePermit"],
  ] as const) {
    if (key in raw) {
      if (typeof raw[key] !== "boolean") {
        throw new ProfileError(`${source}: ${key} must be a boolean`);
      }
      (base as unknown as Record<string, boolean>)[field] = raw[key] as boolean;
    }
  }
  if ("mask_patterns" in raw) {
    const masks = raw.mask_patterns;
    if (!Array.isArray(masks) || !masks.every((m) => typeof m === "string")) {
      throw new ProfileError(`${source}: mask_patterns must be a list of strings`);
    }
    if (masks.length > 0) {
      base.maskPatterns = base.maskPatterns.concat(masks as string[]);
    }
  }
  if ("silence_rules" in raw) {
    const rules = raw.silence_rules;
    if (!Array.isArray(rules)) {
      throw new ProfileError(`${source}: silence_rules must be a list`);
    }
    const parsed = rules.map((r) => parseRule(r, source));
    if (parsed.length > 0) {
      base.quietRules = base.quietRules.concat(parsed);
    }
  }
}

function readProfileFile(filePath: string): Record<string, unknown> {
  const text = fs.readFileSync(filePath, "utf8");
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch (error) {
    throw new ProfileError(`failed reading config '${filePath}': ${(error as Error).message}`);
  }
  if (!isPlainObject(data)) {
    throw new ProfileError(`failed reading config '${filePath}': not an object`);
  }
  return data;
}

export function loadProfile(cwd: string): Config {
  const cfg = defaultProfile();
  const paths = [globalProfilePath(), localProfilePath(cwd)];
  for (const filePath of paths) {
    if (!filePath || !fs.existsSync(filePath)) {
      continue;
    }
    applyPatch(cfg, readProfileFile(filePath), filePath);
  }
  return cfg;
}

function profileObject(cfg: Config): Record<string, unknown> {
  return {
    max_lines: cfg.maxOutputLines,
    line_width: cfg.maxLineWidth,
    strip_ansi: cfg.stripAnsi,
    preserve_errors: cfg.preserveErrors,
    require_permit: cfg.requirePermit,
    mask_patterns: cfg.maskPatterns,
    silence_rules: cfg.quietRules,
  };
}

export function writeProfile(filePath: string): void {
  fs.mkdirSync(path.dirname(filePath), { recursive: true, mode: 0o700 });
  const blob = JSON.stringify(profileObject(defaultProfile()), null, 2) + "\n";
  fs.writeFileSync(filePath, blob, { mode: 0o600 });
}

export function userConfigDir(): string | undefined {
  if (process.platform === "win32") {
    return process.env.AppData || undefined;
  }
  if (process.platform === "darwin") {
    const home = process.env.HOME || os.homedir();
    return home ? path.join(home, "Library", "Application Support") : undefined;
  }
  if (process.env.XDG_CONFIG_HOME) {
    return process.env.XDG_CONFIG_HOME;
  }
  const home = process.env.HOME || os.homedir();
  return home ? path.join(home, ".config") : undefined;
}

export function globalProfilePath(): string {
  const base = userConfigDir();
  return base ? path.join(base, "hushline", "profile.json") : "";
}

export function localProfilePath(cwd: string): string {
  return path.join(cwd, ".hushline", "profile.json");
}

export function permitMarkerPath(cwd: string): string {
  return path.join(cwd, ".hushline", "permitted");
}

export function isPermitted(cwd: string): boolean {
  return fs.existsSync(permitMarkerPath(cwd));
}

export function markPermitted(cwd: string): void {
  const marker = permitMarkerPath(cwd);
  fs.mkdirSync(path.dirname(marker), { recursive: true, mode: 0o700 });
  fs.writeFileSync(marker, "ok\n", { mode: 0o600 });
}
