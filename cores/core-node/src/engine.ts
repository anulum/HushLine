// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// HUSHLINE — core engine bootstrap

// Command dispatch for the Node core. Flags are parsed with the same semantics
// as Go's flag package: parsing stops at the first non-flag token or "--", and
// boolean flags take no following argument. Output writers and the working
// directory are injected so the behaviour is fully testable.

import * as config from "./config";
import * as muter from "./muter";
import * as pipeline from "./pipeline";
import { Writer } from "./pipeline";

export const VERSION = "0.1.5";

const USAGE = `hushline - local command output shaping utility

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
`;

const TRUE_TOKENS = new Set(["1", "t", "T", "TRUE", "true", "True"]);
const FALSE_TOKENS = new Set(["0", "f", "F", "FALSE", "false", "False"]);

class FlagError extends Error {}

type FlagValue = boolean | number;

export function run(args: string[], out: Writer, err: Writer, cwd: string): number {
  if (args.length === 0 || ["help", "-h", "--help"].includes(args[0])) {
    out(USAGE);
    return 0;
  }
  switch (args[0]) {
    case "mute":
      return mute(args.slice(1), out, err, cwd);
    case "manifest":
      return manifest(args.slice(1), out, err, cwd);
    case "permit":
      return permit(args.slice(1), out, err, cwd);
    case "version":
      out(`hushline ${VERSION}\n`);
      return 0;
    default:
      out(`unknown command: ${args[0]}\n\n`);
      out(USAGE);
      return 1;
  }
}

function manifest(args: string[], out: Writer, err: Writer, cwd: string): number {
  if (args.length === 0 || args[0] === "show") {
    out(`global profile: ${config.globalProfilePath()}\n`);
    out(`local profile:  ${config.localProfilePath(cwd)}\n`);
    return 0;
  }
  if (args[0] !== "init") {
    err(`manifest: unknown action "${args[0]}"\n`);
    return 2;
  }

  let flags: Map<string, FlagValue>;
  try {
    [flags] = parseFlags(args.slice(1), ["global", "local"], []);
  } catch (error) {
    err(`manifest options: ${(error as Error).message}\n`);
    return 2;
  }

  try {
    emitProfile(flagBool(flags, "global"), flagBool(flags, "local"), cwd, out);
  } catch (error) {
    err(`manifest init: ${(error as Error).message}\n`);
    return 1;
  }
  return 0;
}

function permit(args: string[], out: Writer, err: Writer, cwd: string): number {
  const action = args.length > 0 ? args[0] : "status";
  if (action === "status") {
    if (config.isPermitted(cwd)) {
      out("permitted: true\n");
      return 0;
    }
    out("permitted: false\n");
    return 2;
  }
  if (action === "allow") {
    const target = args.length > 1 ? args[1] : cwd;
    try {
      config.markPermitted(target);
    } catch (error) {
      err(`permit allow: ${(error as Error).message}\n`);
      return 1;
    }
    out(`permitted: ${target}\n`);
    return 0;
  }
  err(`permit: unknown action "${action}"\n`);
  return 2;
}

function mute(args: string[], out: Writer, err: Writer, cwd: string): number {
  let flags: Map<string, FlagValue>;
  let rest: string[];
  try {
    [flags, rest] = parseFlags(args, ["raw", "pipe-errors"], ["max-lines", "max-width", "timeout"]);
  } catch (error) {
    err(`mute options: ${(error as Error).message}\n`);
    return 2;
  }

  if (rest.length === 0) {
    err("mute: missing command\n");
    return 2;
  }

  let profile: config.Config;
  try {
    profile = config.loadProfile(cwd);
  } catch (error) {
    err(`profile: ${(error as Error).message}\n`);
    return 1;
  }

  const maxLines = flagInt(flags, "max-lines");
  const maxWidth = flagInt(flags, "max-width");
  if (maxLines > 0) {
    profile.maxOutputLines = maxLines;
  }
  if (maxWidth > 0) {
    profile.maxLineWidth = maxWidth;
  }
  profile.preserveErrors = flagBoolDefault(flags, "pipe-errors", true);

  if (profile.requirePermit && !config.isPermitted(cwd)) {
    err(
      "hushline: current directory not permitted. run `hushline permit allow` first or set require_permit: false\n",
    );
    return 3;
  }

  let silence: muter.Muter | null = null;
  if (!flagBool(flags, "raw")) {
    try {
      silence = muter.compose(profile);
    } catch (error) {
      err(`mute: ${(error as Error).message}\n`);
      return 1;
    }
  }

  const code = pipeline.through(
    rest[0],
    rest.slice(1),
    out,
    err,
    silence,
    profile.maxOutputLines,
    profile.preserveErrors,
    flagInt(flags, "timeout"),
  );
  if (code === 124) {
    err("hushline: command timed out\n");
  }
  return code;
}

function emitProfile(writeGlobal: boolean, writeLocal: boolean, cwd: string, out: Writer): void {
  const target =
    writeLocal && !writeGlobal ? config.localProfilePath(cwd) : config.globalProfilePath();
  if (!target) {
    throw new Error("could not resolve profile path");
  }
  config.writeProfile(target);
  out(`profile written: ${target}\n`);
}

function parseFlags(
  args: string[],
  boolFlags: string[],
  intFlags: string[],
): [Map<string, FlagValue>, string[]] {
  const flags = new Map<string, FlagValue>();
  let index = 0;
  while (index < args.length) {
    const token = args[index];
    if (token === "--") {
      return [flags, args.slice(index + 1)];
    }
    if (!(token.length > 1 && token.startsWith("-"))) {
      return [flags, args.slice(index)];
    }

    const body = token.replace(/^-+/, "");
    const equals = body.indexOf("=");
    const name = equals >= 0 ? body.slice(0, equals) : body;
    let value = equals >= 0 ? body.slice(equals + 1) : "";
    const hasValue = equals >= 0;

    if (boolFlags.includes(name)) {
      flags.set(name, hasValue ? parseBool(name, value) : true);
    } else if (intFlags.includes(name)) {
      if (!hasValue) {
        index += 1;
        if (index >= args.length) {
          throw new FlagError(`flag needs an argument: -${name}`);
        }
        value = args[index];
      }
      flags.set(name, parseInteger(name, value));
    } else {
      throw new FlagError(`flag provided but not defined: -${name}`);
    }
    index += 1;
  }
  return [flags, []];
}

function parseBool(name: string, value: string): boolean {
  if (TRUE_TOKENS.has(value)) {
    return true;
  }
  if (FALSE_TOKENS.has(value)) {
    return false;
  }
  throw new FlagError(`invalid boolean value '${value}' for -${name}`);
}

function parseInteger(name: string, value: string): number {
  if (!/^[+-]?\d+$/.test(value)) {
    throw new FlagError(`invalid value '${value}' for -${name}`);
  }
  return Number.parseInt(value, 10);
}

function flagBool(flags: Map<string, FlagValue>, name: string): boolean {
  return flagBoolDefault(flags, name, false);
}

function flagBoolDefault(flags: Map<string, FlagValue>, name: string, fallback: boolean): boolean {
  const value = flags.get(name);
  return typeof value === "boolean" ? value : fallback;
}

function flagInt(flags: Map<string, FlagValue>, name: string): number {
  const value = flags.get(name);
  return typeof value === "number" ? value : 0;
}
