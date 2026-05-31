// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// HUSHLINE — pipeline conduit tests

package pipeline

import (
	"bytes"
	"context"
	"errors"
	"io"
	"runtime"
	"strings"
	"testing"

	"github.com/local/hushline/internal/config"
	"github.com/local/hushline/internal/muter"
)

type failingReader struct{}

func (failingReader) Read([]byte) (int, error) {
	return 0, errors.New("forced read failure")
}

func TestThroughRedactsAndTruncatesStdout(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("shell command contract is POSIX-specific")
	}
	var stdout bytes.Buffer
	var stderr bytes.Buffer
	instance, err := muter.Compose(config.DefaultProfile())
	if err != nil {
		t.Fatalf("Compose returned error: %v", err)
	}
	secret := "sk-" + "abcdefghijklmnopqrstuvwxyz"
	command := "printf '" + secret + "\\nsecond\\nthird\\n'"

	result, err := Through(context.Background(), "sh", []string{"-c", command}, &stdout, &stderr, instance, 2, true, 0)
	if err != nil {
		t.Fatalf("Through returned error: %v", err)
	}
	if result.ExitCode != 0 {
		t.Fatalf("ExitCode = %d, want 0", result.ExitCode)
	}
	got := stdout.String()
	if strings.Contains(got, secret) {
		t.Fatalf("stdout leaked secret: %q", got)
	}
	if !strings.Contains(got, "[output truncated]") {
		t.Fatalf("stdout missing truncation marker: %q", got)
	}
}

func TestThroughPreservesStderrWhenRequested(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("shell command contract is POSIX-specific")
	}
	var stdout bytes.Buffer
	var stderr bytes.Buffer

	result, err := Through(context.Background(), "sh", []string{"-c", "printf visible >&2"}, &stdout, &stderr, nil, 0, true, 0)
	if err != nil {
		t.Fatalf("Through returned error: %v", err)
	}
	if result.ExitCode != 0 {
		t.Fatalf("ExitCode = %d, want 0", result.ExitCode)
	}
	if got := stderr.String(); got != "visible\n" {
		t.Fatalf("stderr = %q, want visible newline", got)
	}
}

func TestThroughReturnsChildExitCode(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("shell command contract is POSIX-specific")
	}
	var stdout bytes.Buffer
	var stderr bytes.Buffer

	result, err := Through(context.Background(), "sh", []string{"-c", "exit 7"}, &stdout, &stderr, nil, 0, true, 0)
	if err != nil {
		t.Fatalf("Through returned error for child exit status: %v", err)
	}
	if result.ExitCode != 7 {
		t.Fatalf("ExitCode = %d, want 7", result.ExitCode)
	}
}

func TestThroughReturnsStartCommandError(t *testing.T) {
	var stdout bytes.Buffer
	var stderr bytes.Buffer

	result, err := Through(context.Background(), "__hushline_missing_command__", nil, &stdout, &stderr, nil, 0, true, 0)
	if err == nil {
		t.Fatalf("Through returned nil error for missing command")
	}
	if result.ExitCode != 2 {
		t.Fatalf("ExitCode = %d, want 2", result.ExitCode)
	}
}

func TestThroughDiscardsStderrWhenPreserveErrorsFalse(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("shell command contract is POSIX-specific")
	}
	var stdout bytes.Buffer
	var stderr bytes.Buffer

	result, err := Through(context.Background(), "sh", []string{"-c", "printf 'visible'; printf 'hidden' >&2"}, &stdout, &stderr, nil, 0, false, 0)
	if err != nil {
		t.Fatalf("Through returned error: %v", err)
	}
	if result.ExitCode != 0 {
		t.Fatalf("ExitCode = %d, want 0", result.ExitCode)
	}
	if got := stdout.String(); got != "visible\n" {
		t.Fatalf("stdout = %q, want visible newline", got)
	}
	if got := stderr.String(); got != "" {
		t.Fatalf("stderr = %q, want discarded", got)
	}
}

func TestThroughReturnsTimeoutExitCode(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("shell command contract is POSIX-specific")
	}
	var stdout bytes.Buffer
	var stderr bytes.Buffer

	result, err := Through(context.Background(), "sh", []string{"-c", "sleep 2"}, &stdout, &stderr, nil, 0, true, 1)
	if err == nil {
		t.Fatalf("Through returned nil error for timeout")
	}
	if result.ExitCode != 124 {
		t.Fatalf("ExitCode = %d, want 124", result.ExitCode)
	}
}

func TestThroughHandlesLinesAboveScannerTokenLimit(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("shell command contract is POSIX-specific")
	}
	var stdout bytes.Buffer
	var stderr bytes.Buffer

	result, err := Through(context.Background(), "sh", []string{"-c", "python3 - <<'PY'\nprint('x' * (17 * 1024 * 1024))\nPY"}, &stdout, &stderr, nil, 0, true, 0)
	if err != nil {
		t.Fatalf("Through returned command error: %v", err)
	}
	if result.ExitCode != 0 {
		t.Fatalf("ExitCode = %d, want 0", result.ExitCode)
	}
	line := strings.TrimSpace(stdout.String())
	if len(line) != 17*1024*1024 {
		t.Fatalf("oversized line length = %d, want %d", len(line), 17*1024*1024)
	}
}

func TestStreamReportsReaderErrors(t *testing.T) {
	var out bytes.Buffer

	stream(failingReader{}, &out, nil, 0)

	if !strings.Contains(out.String(), "forced read failure") {
		t.Fatalf("stream output = %q, want read failure marker", out.String())
	}
}

func TestStreamHandlesEOFWithoutOutput(t *testing.T) {
	var out bytes.Buffer

	stream(strings.NewReader(""), &out, nil, 0)

	if out.String() != "" {
		t.Fatalf("stream output = %q, want empty", out.String())
	}
}

func TestStreamWritesPartialLineAtEOF(t *testing.T) {
	var out bytes.Buffer

	stream(io.NopCloser(strings.NewReader("partial")), &out, nil, 0)

	if out.String() != "partial\n" {
		t.Fatalf("stream output = %q, want partial line", out.String())
	}
}

func TestStreamWritesTruncationMarkerAtEOF(t *testing.T) {
	var out bytes.Buffer

	stream(strings.NewReader("first\nsecond"), &out, nil, 1)

	if out.String() != "first\n[output truncated]\n" {
		t.Fatalf("stream output = %q, want truncation marker at EOF", out.String())
	}
}

func TestThroughHandlesLongLinesBeyondScannerDefault(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("shell command contract is POSIX-specific")
	}
	var stdout bytes.Buffer
	var stderr bytes.Buffer

	result, err := Through(context.Background(), "sh", []string{"-c", "python3 - <<'PY'\nprint('x' * 70000)\nPY"}, &stdout, &stderr, nil, 0, true, 0)
	if err != nil {
		t.Fatalf("Through returned error: %v", err)
	}
	if result.ExitCode != 0 {
		t.Fatalf("ExitCode = %d, want 0", result.ExitCode)
	}
	line := strings.TrimSpace(stdout.String())
	if len(line) != 70000 {
		t.Fatalf("long line length = %d, want 70000", len(line))
	}
}
