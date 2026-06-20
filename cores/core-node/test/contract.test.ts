// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// HUSHLINE — Node core contract tests

import test from "node:test";
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";

import * as config from "../src/config";
import * as muter from "../src/muter";
import * as pipeline from "../src/pipeline";
import { run, VERSION } from "../src/engine";

const SECRET = "sk-" + "abcdefghijklmnopqrstuvwxyz";

function workspace(): string {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), "hushline-node-"));
  process.env.XDG_CONFIG_HOME = path.join(base, "xdg");
  fs.mkdirSync(process.env.XDG_CONFIG_HOME, { recursive: true });
  const work = path.join(base, "work");
  fs.mkdirSync(work, { recursive: true });
  return work;
}

function call(args: string[], cwd: string): { code: number; out: string; err: string } {
  let out = "";
  let err = "";
  const code = run(
    args,
    (s) => {
      out += s;
    },
    (s) => {
      err += s;
    },
    cwd,
  );
  return { code, out, err };
}

function writeLocalProfile(work: string, json: string): void {
  const target = path.join(work, ".hushline", "profile.json");
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, json);
}

// ----- dispatch -----

test("version prints in lockstep", () => {
  const work = workspace();
  const r = call(["version"], work);
  assert.equal(r.code, 0);
  assert.equal(r.out, `hushline ${VERSION}\n`);
  assert.equal(VERSION, "0.1.5");
});

test("help and empty show usage", () => {
  const work = workspace();
  for (const args of [[], ["help"], ["-h"], ["--help"]]) {
    const r = call(args as string[], work);
    assert.equal(r.code, 0);
    assert.ok(r.out.includes("local command output shaping utility"));
  }
});

test("unknown command is one", () => {
  const work = workspace();
  const r = call(["wat"], work);
  assert.equal(r.code, 1);
  assert.ok(r.out.includes("unknown command: wat"));
});

// ----- manifest -----

test("manifest show lists paths", () => {
  const work = workspace();
  const r = call(["manifest"], work);
  assert.equal(r.code, 0);
  assert.ok(r.out.includes("global profile:"));
  assert.ok(r.out.includes("local profile:"));
  assert.equal(call(["manifest", "show"], work).out, r.out);
});

test("manifest init global and local", () => {
  const work = workspace();
  assert.equal(call(["manifest", "init", "--global"], work).code, 0);
  assert.ok(fs.existsSync(config.globalProfilePath()));
  assert.equal(call(["manifest", "init", "--local"], work).code, 0);
  assert.ok(fs.existsSync(config.localProfilePath(work)));
});

test("manifest init default and both are global", () => {
  const work = workspace();
  call(["manifest", "init"], work);
  assert.ok(fs.existsSync(config.globalProfilePath()));
  assert.ok(!fs.existsSync(config.localProfilePath(work)));
  call(["manifest", "init", "--global", "--local"], work);
  assert.ok(!fs.existsSync(config.localProfilePath(work)));
});

test("manifest unknown action and bad flag", () => {
  const work = workspace();
  assert.equal(call(["manifest", "huh"], work).code, 2);
  assert.equal(call(["manifest", "init", "--bogus"], work).code, 2);
});

// ----- permit -----

test("permit status allow status round trip", () => {
  const work = workspace();
  let r = call(["permit", "status"], work);
  assert.equal(r.code, 2);
  assert.equal(r.out, "permitted: false\n");
  r = call(["permit", "allow"], work);
  assert.equal(r.code, 0);
  r = call(["permit"], work);
  assert.equal(r.code, 0);
  assert.equal(r.out, "permitted: true\n");
});

test("permit allow explicit path and unknown action", () => {
  const work = workspace();
  const target = path.join(work, "elsewhere");
  const r = call(["permit", "allow", target], work);
  assert.equal(r.code, 0);
  assert.ok(r.out.includes(target));
  assert.ok(config.isPermitted(target));
  assert.equal(call(["permit", "wat"], work).code, 2);
});

// ----- mute -----

test("mute missing command is two", () => {
  const work = workspace();
  const r = call(["mute"], work);
  assert.equal(r.code, 2);
  assert.ok(r.err.includes("missing command"));
});

test("mute redacts secret", () => {
  const work = workspace();
  const r = call(["mute", "--", "printf", `${SECRET}\\n`], work);
  assert.equal(r.code, 0);
  assert.ok(!r.out.includes(SECRET));
  assert.ok(r.out.includes("***"));
});

test("mute raw keeps secret", () => {
  const work = workspace();
  const r = call(["mute", "--raw", "--", "printf", `${SECRET}\\n`], work);
  assert.equal(r.code, 0);
  assert.ok(r.out.includes(SECRET));
});

test("mute pipe-errors false discards stderr", () => {
  const work = workspace();
  const r = call(["mute", "--pipe-errors=false", "--", "sh", "-c", "printf boom 1>&2"], work);
  assert.equal(r.code, 0);
  assert.ok(!r.err.includes("boom"));
});

test("mute max-lines marker", () => {
  const work = workspace();
  const r = call(["mute", "--max-lines", "1", "--raw", "--", "printf", "a\\nb\\nc\\n"], work);
  assert.equal(r.code, 0);
  assert.deepEqual(r.out.split("\n").filter((l) => l.length > 0), ["a", "[output truncated]"]);
});

test("mute max-width truncates", () => {
  const work = workspace();
  const r = call(["mute", "--max-width=3", "--", "printf", "abcdef\\n"], work);
  assert.equal(r.code, 0);
  assert.equal(r.out, "abc\n");
});

test("mute timeout is 124", () => {
  const work = workspace();
  const r = call(["mute", "--timeout", "1", "--", "sh", "-c", "sleep 5"], work);
  assert.equal(r.code, 124);
  assert.ok(r.err.includes("timed out"));
});

test("mute require permit gate and satisfied", () => {
  const work = workspace();
  writeLocalProfile(work, '{"require_permit": true}');
  const gated = call(["mute", "--", "printf", "hi\\n"], work);
  assert.equal(gated.code, 3);
  assert.ok(gated.err.includes("not permitted"));
  config.markPermitted(work);
  const ok = call(["mute", "--raw", "--", "printf", "hi\\n"], work);
  assert.equal(ok.code, 0);
  assert.equal(ok.out, "hi\n");
});

test("mute invalid mask pattern is one", () => {
  const work = workspace();
  writeLocalProfile(work, '{"mask_patterns": ["(unclosed"]}');
  const r = call(["mute", "--", "printf", "x\\n"], work);
  assert.equal(r.code, 1);
  assert.ok(r.err.includes("mute:"));
});

test("mute profile load error is one", () => {
  const work = workspace();
  writeLocalProfile(work, "{bad");
  const r = call(["mute", "--", "printf", "x\\n"], work);
  assert.equal(r.code, 1);
  assert.ok(r.err.includes("profile:"));
});

test("mute flag errors", () => {
  const work = workspace();
  assert.equal(call(["mute", "--raw=maybe", "--", "printf", "x"], work).code, 2);
  assert.equal(call(["mute", "--nope", "--", "printf", "x"], work).code, 2);
  assert.equal(call(["mute", "--timeout"], work).code, 2);
  assert.equal(call(["mute", "--timeout=x", "--", "printf", "x"], work).code, 2);
});

test("mute non-flag stops parsing", () => {
  const work = workspace();
  const r = call(["mute", "printf", "hi\\n"], work);
  assert.equal(r.code, 0);
  assert.ok(r.out.includes("hi"));
});

// ----- config -----

test("default profile matches reference", () => {
  const cfg = config.defaultProfile();
  assert.equal(cfg.maxOutputLines, 2000);
  assert.equal(cfg.stripAnsi, true);
  assert.equal(cfg.maskPatterns.length, 2);
  assert.equal(cfg.quietRules[0].name, "ci-trim");
});

test("merge overrides and appends", () => {
  const work = workspace();
  writeLocalProfile(
    work,
    '{"max_lines": 50, "strip_ansi": false, "mask_patterns": ["X"], "silence_rules": [{"name":"n","pattern":"a","replacement":"b"}]}',
  );
  const cfg = config.loadProfile(work);
  assert.equal(cfg.maxOutputLines, 50);
  assert.equal(cfg.stripAnsi, false);
  assert.equal(cfg.maskPatterns.length, 3);
  assert.equal(cfg.quietRules.length, 3);
});

test("merge ignores zero negative and empty lists", () => {
  const work = workspace();
  writeLocalProfile(work, '{"max_lines": 0, "line_width": -5, "mask_patterns": [], "silence_rules": []}');
  const cfg = config.loadProfile(work);
  assert.equal(cfg.maxOutputLines, 2000);
  assert.equal(cfg.maxLineWidth, 0);
  assert.equal(cfg.maskPatterns.length, 2);
});

test("strict parse rejects unknown key", () => {
  const work = workspace();
  writeLocalProfile(work, '{"unknown": 1}');
  assert.throws(() => config.loadProfile(work), config.ProfileError);
});

// ----- muter -----

test("muter redacts and strips ansi", () => {
  const m = muter.compose(config.defaultProfile());
  const out = m.apply(`\x1b[31mtoken ${SECRET}\x1b[0m   tail`);
  assert.ok(!out.includes(SECRET));
  assert.ok(out.includes("***"));
  assert.ok(!out.includes("\x1b"));
  assert.ok(!out.includes("   "));
});

test("muter order and truncation", () => {
  const cfg = config.defaultProfile();
  cfg.stripAnsi = false;
  cfg.maskPatterns = [];
  cfg.quietRules = [
    { name: "a", pattern: "a", replacement: "b" },
    { name: "b", pattern: "b", replacement: "c" },
  ];
  assert.equal(muter.compose(cfg).apply("a"), "c");
});

test("muter truncates plain ascii and respects char boundary", () => {
  const ascii = config.defaultProfile();
  ascii.stripAnsi = false;
  ascii.maskPatterns = [];
  ascii.quietRules = [];
  ascii.maxLineWidth = 4;
  assert.equal(muter.compose(ascii).apply("abcdef"), "abcd");

  const multibyte = config.defaultProfile();
  multibyte.stripAnsi = false;
  multibyte.maskPatterns = [];
  multibyte.quietRules = [];
  multibyte.maxLineWidth = 2;
  assert.equal(muter.compose(multibyte).apply("aéb"), "a");
});

test("muter invalid pattern throws", () => {
  const cfg = config.defaultProfile();
  cfg.maskPatterns = ["("];
  assert.throws(() => muter.compose(cfg), muter.MuterError);
});

// ----- pipeline -----

function pipe(
  command: string,
  args: string[],
  opts: { maxLines?: number; preserve?: boolean; timeout?: number; redact?: boolean } = {},
): { code: number; out: string; err: string } {
  let out = "";
  let err = "";
  const m = opts.redact ? muter.compose(config.defaultProfile()) : null;
  const code = pipeline.through(
    command,
    args,
    (s) => {
      out += s;
    },
    (s) => {
      err += s;
    },
    m,
    opts.maxLines ?? 2000,
    opts.preserve ?? true,
    opts.timeout ?? 0,
  );
  return { code, out, err };
}

test("pipeline passthrough and exit code", () => {
  const r = pipe("printf", ["one\\ntwo\\n"]);
  assert.equal(r.code, 0);
  assert.equal(r.out, "one\ntwo\n");
  assert.equal(r.err, "");
  assert.equal(pipe("sh", ["-c", "exit 7"]).code, 7);
});

test("pipeline start failure and signal", () => {
  assert.equal(pipe("hushline-no-such-binary-xyz", []).code, 2);
  assert.equal(pipe("sh", ["-c", "kill -9 $$"]).code, 1);
});

test("pipeline timeout", () => {
  assert.equal(pipe("sh", ["-c", "sleep 5"], { timeout: 1 }).code, 124);
});

test("pipeline stderr modes", () => {
  assert.ok(pipe("sh", ["-c", "printf oops 1>&2"]).err.includes("oops"));
  assert.equal(pipe("sh", ["-c", "printf oops 1>&2"], { preserve: false }).err, "");
});

test("pipeline redacts stdout", () => {
  const r = pipe("printf", [`${SECRET}\\n`], { redact: true });
  assert.ok(!r.out.includes(SECRET));
  assert.ok(r.out.includes("***"));
});
