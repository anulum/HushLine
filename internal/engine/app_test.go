// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// HUSHLINE — engine command tests

package engine

import (
	"errors"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func captureRun(t *testing.T, argv []string) (int, string, string) {
	t.Helper()
	originalStdout := os.Stdout
	originalStderr := os.Stderr
	stdoutReader, stdoutWriter, err := os.Pipe()
	if err != nil {
		t.Fatalf("create stdout pipe: %v", err)
	}
	stderrReader, stderrWriter, err := os.Pipe()
	if err != nil {
		t.Fatalf("create stderr pipe: %v", err)
	}
	os.Stdout = stdoutWriter
	os.Stderr = stderrWriter
	defer func() {
		os.Stdout = originalStdout
		os.Stderr = originalStderr
	}()

	exitCode := Run(argv)
	if err := stdoutWriter.Close(); err != nil {
		t.Fatalf("close stdout pipe: %v", err)
	}
	if err := stderrWriter.Close(); err != nil {
		t.Fatalf("close stderr pipe: %v", err)
	}
	stdout, err := io.ReadAll(stdoutReader)
	if err != nil {
		t.Fatalf("read stdout: %v", err)
	}
	stderr, err := io.ReadAll(stderrReader)
	if err != nil {
		t.Fatalf("read stderr: %v", err)
	}
	return exitCode, string(stdout), string(stderr)
}

func chdir(t *testing.T, dir string) {
	t.Helper()
	original, err := os.Getwd()
	if err != nil {
		t.Fatalf("get working directory before chdir: %v", err)
	}
	if err := os.Chdir(dir); err != nil {
		t.Fatalf("chdir to %s: %v", dir, err)
	}
	t.Cleanup(func() {
		if err := os.Chdir(original); err != nil {
			t.Fatalf("restore working directory: %v", err)
		}
	})
}

func runFromRemovedWorkingDirectory(t *testing.T, argv []string) (int, string, string) {
	t.Helper()
	original, err := os.Getwd()
	if err != nil {
		t.Fatalf("get original working directory: %v", err)
	}
	deleted := filepath.Join(t.TempDir(), "deleted")
	if err := os.Mkdir(deleted, 0o700); err != nil {
		t.Fatalf("create deleted working directory: %v", err)
	}
	if err := os.Chdir(deleted); err != nil {
		t.Fatalf("enter deleted working directory: %v", err)
	}
	if err := os.Remove(deleted); err != nil {
		t.Fatalf("remove working directory: %v", err)
	}
	t.Cleanup(func() {
		_ = os.Chdir(original)
	})
	return captureRun(t, argv)
}

func TestRunRejectsMuteWithoutCommand(t *testing.T) {
	exitCode, _, stderr := captureRun(t, []string{"mute"})

	if exitCode != 2 {
		t.Fatalf("exit code = %d, want 2", exitCode)
	}
	if !strings.Contains(stderr, "missing command") {
		t.Fatalf("stderr = %q, want missing command", stderr)
	}
}

func TestRunRejectsInvalidMuteOption(t *testing.T) {
	exitCode, _, stderr := captureRun(t, []string{"mute", "--not-a-real-option"})

	if exitCode != 2 {
		t.Fatalf("exit code = %d, want 2", exitCode)
	}
	if !strings.Contains(stderr, "mute options:") {
		t.Fatalf("stderr = %q, want mute options error", stderr)
	}
}

func TestRunHonoursRequirePermit(t *testing.T) {
	t.Setenv("XDG_CONFIG_HOME", filepath.Join(t.TempDir(), "xdg"))
	cwd := t.TempDir()
	chdir(t, cwd)
	if err := os.MkdirAll(filepath.Join(cwd, ".hushline"), 0o700); err != nil {
		t.Fatalf("create profile directory: %v", err)
	}
	if err := os.WriteFile(filepath.Join(cwd, ".hushline", "profile.json"), []byte(`{"require_permit": true}`), 0o600); err != nil {
		t.Fatalf("write profile: %v", err)
	}

	exitCode, _, stderr := captureRun(t, []string{"mute", "--", "sh", "-c", "printf blocked"})

	if exitCode != 3 {
		t.Fatalf("exit code = %d, want 3", exitCode)
	}
	if !strings.Contains(stderr, "current directory not permitted") {
		t.Fatalf("stderr = %q, want permit error", stderr)
	}
}

func TestRunRejectsInvalidProfilePattern(t *testing.T) {
	t.Setenv("XDG_CONFIG_HOME", filepath.Join(t.TempDir(), "xdg"))
	cwd := t.TempDir()
	chdir(t, cwd)
	if err := os.MkdirAll(filepath.Join(cwd, ".hushline"), 0o700); err != nil {
		t.Fatalf("create profile directory: %v", err)
	}
	if err := os.WriteFile(filepath.Join(cwd, ".hushline", "profile.json"), []byte(`{"mask_patterns": ["["]}`), 0o600); err != nil {
		t.Fatalf("write profile: %v", err)
	}

	exitCode, _, stderr := captureRun(t, []string{"mute", "--", "sh", "-c", "printf unreachable"})

	if exitCode != 1 {
		t.Fatalf("exit code = %d, want 1", exitCode)
	}
	if !strings.Contains(stderr, "invalid redact pattern") {
		t.Fatalf("stderr = %q, want invalid redact pattern", stderr)
	}
}

func TestRunReportsProfileLoadError(t *testing.T) {
	t.Setenv("XDG_CONFIG_HOME", filepath.Join(t.TempDir(), "xdg"))
	cwd := t.TempDir()
	chdir(t, cwd)
	if err := os.MkdirAll(filepath.Join(cwd, ".hushline"), 0o700); err != nil {
		t.Fatalf("create profile directory: %v", err)
	}
	if err := os.WriteFile(filepath.Join(cwd, ".hushline", "profile.json"), []byte(`{"unknown": true}`), 0o600); err != nil {
		t.Fatalf("write profile: %v", err)
	}

	exitCode, _, stderr := captureRun(t, []string{"mute", "--", "sh", "-c", "printf unreachable"})

	if exitCode != 1 {
		t.Fatalf("exit code = %d, want 1", exitCode)
	}
	if !strings.Contains(stderr, "profile:") {
		t.Fatalf("stderr = %q, want profile error", stderr)
	}
}

func TestRunRawModeBypassesRedaction(t *testing.T) {
	secret := "sk-" + "abcdefghijklmnopqrstuvwxyz"
	exitCode, stdout, stderr := captureRun(t, []string{"mute", "--raw", "--", "sh", "-c", "printf " + secret})

	if exitCode != 0 {
		t.Fatalf("exit code = %d, want 0", exitCode)
	}
	if !strings.Contains(stdout, secret) {
		t.Fatalf("stdout = %q, want raw secret visible", stdout)
	}
	if stderr != "" {
		t.Fatalf("stderr = %q, want empty", stderr)
	}
}

func TestRunMaxWidthTruncatesOutput(t *testing.T) {
	exitCode, stdout, stderr := captureRun(t, []string{"mute", "--max-width", "4", "--", "sh", "-c", "printf abcdef"})

	if exitCode != 0 {
		t.Fatalf("exit code = %d, want 0", exitCode)
	}
	if stdout != "abcd\n" {
		t.Fatalf("stdout = %q, want truncated output", stdout)
	}
	if stderr != "" {
		t.Fatalf("stderr = %q, want empty", stderr)
	}
}

func TestRunMaxLinesTruncatesOutput(t *testing.T) {
	exitCode, stdout, stderr := captureRun(t, []string{"mute", "--max-lines", "1", "--", "sh", "-c", "printf 'one\\ntwo\\n'"})

	if exitCode != 0 {
		t.Fatalf("exit code = %d, want 0", exitCode)
	}
	if stdout != "one \n[output truncated]\n" {
		t.Fatalf("stdout = %q, want truncation marker", stdout)
	}
	if stderr != "" {
		t.Fatalf("stderr = %q, want empty", stderr)
	}
}

func TestRunPipeErrorsFalseDiscardsStderr(t *testing.T) {
	exitCode, stdout, stderr := captureRun(t, []string{"mute", "--pipe-errors=false", "--", "sh", "-c", "printf out; printf err >&2"})

	if exitCode != 0 {
		t.Fatalf("exit code = %d, want 0", exitCode)
	}
	if stdout != "out\n" {
		t.Fatalf("stdout = %q, want out", stdout)
	}
	if stderr != "" {
		t.Fatalf("stderr = %q, want discarded", stderr)
	}
}

func TestRunReportsTimeout(t *testing.T) {
	exitCode, _, stderr := captureRun(t, []string{"mute", "--timeout", "1", "--", "sh", "-c", "sleep 2"})

	if exitCode != 124 {
		t.Fatalf("exit code = %d, want 124", exitCode)
	}
	if !strings.Contains(stderr, "command timed out") {
		t.Fatalf("stderr = %q, want timeout message", stderr)
	}
}

func TestRunReturnsChildExitCode(t *testing.T) {
	exitCode, _, stderr := captureRun(t, []string{"mute", "--", "sh", "-c", "exit 9"})

	if exitCode != 9 {
		t.Fatalf("exit code = %d, want 9", exitCode)
	}
	if stderr != "" {
		t.Fatalf("stderr = %q, want empty", stderr)
	}
}

func TestRunReportsMissingChildCommand(t *testing.T) {
	exitCode, _, stderr := captureRun(t, []string{"mute", "--", "__hushline_missing_command__"})

	if exitCode != 2 {
		t.Fatalf("exit code = %d, want 2", exitCode)
	}
	if !strings.Contains(stderr, "start command:") {
		t.Fatalf("stderr = %q, want start command error", stderr)
	}
}

func TestRunPrintsVersion(t *testing.T) {
	exitCode, stdout, stderr := captureRun(t, []string{"version"})

	if exitCode != 0 {
		t.Fatalf("exit code = %d, want 0", exitCode)
	}
	if !strings.Contains(stdout, "hushline") {
		t.Fatalf("stdout = %q, want version banner", stdout)
	}
	if stderr != "" {
		t.Fatalf("stderr = %q, want empty", stderr)
	}
}

func TestRunPrintsUsageForHelp(t *testing.T) {
	exitCode, stdout, stderr := captureRun(t, []string{"help"})

	if exitCode != 0 {
		t.Fatalf("exit code = %d, want 0", exitCode)
	}
	if !strings.Contains(stdout, "Usage:") {
		t.Fatalf("stdout = %q, want usage", stdout)
	}
	if stderr != "" {
		t.Fatalf("stderr = %q, want empty", stderr)
	}
}

func TestRunRejectsUnknownCommand(t *testing.T) {
	exitCode, stdout, _ := captureRun(t, []string{"unknown"})

	if exitCode != 1 {
		t.Fatalf("exit code = %d, want 1", exitCode)
	}
	if !strings.Contains(stdout, "unknown command") {
		t.Fatalf("stdout = %q, want unknown command", stdout)
	}
}

func TestManifestShowPrintsProfileLocations(t *testing.T) {
	t.Setenv("XDG_CONFIG_HOME", filepath.Join(t.TempDir(), "xdg"))
	cwd := t.TempDir()
	chdir(t, cwd)

	exitCode, stdout, stderr := captureRun(t, []string{"manifest", "show"})

	if exitCode != 0 {
		t.Fatalf("exit code = %d, want 0", exitCode)
	}
	if !strings.Contains(stdout, "global profile:") || !strings.Contains(stdout, "local profile:") {
		t.Fatalf("stdout = %q, want profile locations", stdout)
	}
	if stderr != "" {
		t.Fatalf("stderr = %q, want empty", stderr)
	}
}

func TestManifestDefaultsToShow(t *testing.T) {
	t.Setenv("XDG_CONFIG_HOME", filepath.Join(t.TempDir(), "xdg"))
	cwd := t.TempDir()
	chdir(t, cwd)

	exitCode, stdout, stderr := captureRun(t, []string{"manifest"})

	if exitCode != 0 {
		t.Fatalf("exit code = %d, want 0", exitCode)
	}
	if !strings.Contains(stdout, "global profile:") || !strings.Contains(stdout, "local profile:") {
		t.Fatalf("stdout = %q, want profile locations", stdout)
	}
	if stderr != "" {
		t.Fatalf("stderr = %q, want empty", stderr)
	}
}

func TestManifestReportsDeletedWorkingDirectory(t *testing.T) {
	exitCode, _, stderr := runFromRemovedWorkingDirectory(t, []string{"manifest", "show"})

	if exitCode != 1 {
		t.Fatalf("exit code = %d, want 1", exitCode)
	}
	if !strings.Contains(stderr, "cwd lookup:") {
		t.Fatalf("stderr = %q, want cwd lookup error", stderr)
	}
}

func TestManifestInitLocalWritesProfile(t *testing.T) {
	t.Setenv("XDG_CONFIG_HOME", filepath.Join(t.TempDir(), "xdg"))
	cwd := t.TempDir()
	chdir(t, cwd)

	exitCode, stdout, stderr := captureRun(t, []string{"manifest", "init", "--local"})

	if exitCode != 0 {
		t.Fatalf("exit code = %d, want 0", exitCode)
	}
	if !strings.Contains(stdout, "profile written:") {
		t.Fatalf("stdout = %q, want written profile path", stdout)
	}
	if stderr != "" {
		t.Fatalf("stderr = %q, want empty", stderr)
	}
	if _, err := os.Stat(filepath.Join(cwd, ".hushline", "profile.json")); err != nil {
		t.Fatalf("local profile not written: %v", err)
	}
}

func TestManifestInitRejectsInvalidFlag(t *testing.T) {
	exitCode, _, stderr := captureRun(t, []string{"manifest", "init", "--bad-flag"})

	if exitCode != 2 {
		t.Fatalf("exit code = %d, want 2", exitCode)
	}
	if !strings.Contains(stderr, "manifest options:") {
		t.Fatalf("stderr = %q, want manifest options error", stderr)
	}
}

func TestManifestInitDefaultWritesGlobalProfile(t *testing.T) {
	xdg := filepath.Join(t.TempDir(), "xdg")
	t.Setenv("XDG_CONFIG_HOME", xdg)
	chdir(t, t.TempDir())

	exitCode, stdout, stderr := captureRun(t, []string{"manifest", "init"})

	if exitCode != 0 {
		t.Fatalf("exit code = %d, want 0", exitCode)
	}
	if !strings.Contains(stdout, "profile written:") {
		t.Fatalf("stdout = %q, want written profile path", stdout)
	}
	if stderr != "" {
		t.Fatalf("stderr = %q, want empty", stderr)
	}
	if _, err := os.Stat(filepath.Join(xdg, "hushline", "profile.json")); err != nil {
		t.Fatalf("global profile not written: %v", err)
	}
}

func TestManifestRejectsUnknownAction(t *testing.T) {
	exitCode, _, stderr := captureRun(t, []string{"manifest", "remove"})

	if exitCode != 2 {
		t.Fatalf("exit code = %d, want 2", exitCode)
	}
	if !strings.Contains(stderr, "unknown action") {
		t.Fatalf("stderr = %q, want unknown action", stderr)
	}
}

func TestPermitStatusAndAllow(t *testing.T) {
	cwd := t.TempDir()
	chdir(t, cwd)

	exitCode, stdout, stderr := captureRun(t, []string{"permit", "status"})
	if exitCode != 2 {
		t.Fatalf("status exit code before allow = %d, want 2", exitCode)
	}
	if !strings.Contains(stdout, "permitted: false") {
		t.Fatalf("stdout before allow = %q, want false", stdout)
	}
	if stderr != "" {
		t.Fatalf("stderr before allow = %q, want empty", stderr)
	}

	exitCode, stdout, stderr = captureRun(t, []string{"permit", "allow"})
	if exitCode != 0 {
		t.Fatalf("allow exit code = %d, want 0", exitCode)
	}
	if !strings.Contains(stdout, "permitted:") {
		t.Fatalf("stdout after allow = %q, want permitted path", stdout)
	}
	if stderr != "" {
		t.Fatalf("stderr after allow = %q, want empty", stderr)
	}

	exitCode, stdout, stderr = captureRun(t, []string{"permit", "status"})
	if exitCode != 0 {
		t.Fatalf("status exit code after allow = %d, want 0", exitCode)
	}
	if !strings.Contains(stdout, "permitted: true") {
		t.Fatalf("stdout after allow = %q, want true", stdout)
	}
	if stderr != "" {
		t.Fatalf("stderr status after allow = %q, want empty", stderr)
	}
}

func TestPermitDefaultsToStatus(t *testing.T) {
	cwd := t.TempDir()
	chdir(t, cwd)

	exitCode, stdout, stderr := captureRun(t, []string{"permit"})

	if exitCode != 2 {
		t.Fatalf("exit code = %d, want 2", exitCode)
	}
	if !strings.Contains(stdout, "permitted: false") {
		t.Fatalf("stdout = %q, want default status output", stdout)
	}
	if stderr != "" {
		t.Fatalf("stderr = %q, want empty", stderr)
	}
}

func TestPermitAllowAcceptsExplicitPath(t *testing.T) {
	cwd := t.TempDir()
	target := t.TempDir()
	chdir(t, cwd)

	exitCode, stdout, stderr := captureRun(t, []string{"permit", "allow", target})

	if exitCode != 0 {
		t.Fatalf("exit code = %d, want 0", exitCode)
	}
	if !strings.Contains(stdout, target) {
		t.Fatalf("stdout = %q, want explicit target", stdout)
	}
	if stderr != "" {
		t.Fatalf("stderr = %q, want empty", stderr)
	}
	if _, err := os.Stat(filepath.Join(target, ".hushline", "permitted")); err != nil {
		t.Fatalf("permit marker not written for explicit path: %v", err)
	}
}

func TestPermitReportsDeletedWorkingDirectory(t *testing.T) {
	exitCode, _, stderr := runFromRemovedWorkingDirectory(t, []string{"permit", "status"})

	if exitCode != 1 {
		t.Fatalf("exit code = %d, want 1", exitCode)
	}
	if !strings.Contains(stderr, "cwd lookup:") {
		t.Fatalf("stderr = %q, want cwd lookup error", stderr)
	}
}

func TestMuteReportsDeletedWorkingDirectory(t *testing.T) {
	exitCode, _, stderr := runFromRemovedWorkingDirectory(t, []string{"mute", "--", "sh", "-c", "printf unreachable"})

	if exitCode != 1 {
		t.Fatalf("exit code = %d, want 1", exitCode)
	}
	if !strings.Contains(stderr, "cwd lookup:") {
		t.Fatalf("stderr = %q, want cwd lookup error", stderr)
	}
}

func TestPermitRejectsUnknownAction(t *testing.T) {
	exitCode, _, stderr := captureRun(t, []string{"permit", "deny"})

	if exitCode != 2 {
		t.Fatalf("exit code = %d, want 2", exitCode)
	}
	if !strings.Contains(stderr, "unknown action") {
		t.Fatalf("stderr = %q, want unknown action", stderr)
	}
}

func TestEmitProfileRejectsUnavailableGlobalConfigPath(t *testing.T) {
	t.Setenv("XDG_CONFIG_HOME", "")
	t.Setenv("HOME", "")

	if err := emitProfile(false, false, t.TempDir()); err == nil {
		t.Fatalf("emitProfile returned nil error without a global config path")
	}
}

func TestEmitProfileWritesLocalWhenRequested(t *testing.T) {
	cwd := t.TempDir()

	if err := emitProfile(false, true, cwd); err != nil {
		t.Fatalf("emitProfile local returned error: %v", err)
	}
	if _, err := os.Stat(filepath.Join(cwd, ".hushline", "profile.json")); err != nil {
		t.Fatalf("local profile not written: %v", err)
	}
}

func TestEmitProfileUsesGlobalWhenBothScopesRequested(t *testing.T) {
	xdg := filepath.Join(t.TempDir(), "xdg")
	t.Setenv("XDG_CONFIG_HOME", xdg)

	if err := emitProfile(true, true, t.TempDir()); err != nil {
		t.Fatalf("emitProfile both scopes returned error: %v", err)
	}
	if _, err := os.Stat(filepath.Join(xdg, "hushline", "profile.json")); err != nil {
		t.Fatalf("global profile not written: %v", err)
	}
}

func TestEmitProfileWritesGlobalWhenRequested(t *testing.T) {
	xdg := filepath.Join(t.TempDir(), "xdg")
	t.Setenv("XDG_CONFIG_HOME", xdg)

	if err := emitProfile(true, false, t.TempDir()); err != nil {
		t.Fatalf("emitProfile global returned error: %v", err)
	}
	if _, err := os.Stat(filepath.Join(xdg, "hushline", "profile.json")); err != nil {
		t.Fatalf("global profile not written: %v", err)
	}
}

func TestEmitProfileReturnsWriteError(t *testing.T) {
	if err := emitProfile(false, true, "/proc/hushline"); err == nil || !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("emitProfile error = %v, want path creation failure", err)
	}
}
