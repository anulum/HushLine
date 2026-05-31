// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// HUSHLINE — pipeline conduit

package pipeline

import (
	"bufio"
	"context"
	"fmt"
	"io"
	"os/exec"
	"strings"
	"sync"
	"time"

	"github.com/local/hushline/pkg/hushline/muter"
)

type PipeOutcome struct {
	ExitCode int
}

func Through(ctx context.Context, command string, args []string, outWriter io.Writer, errWriter io.Writer, muterEngine *muter.Muter, maxOutputLines int, preserveErrors bool, timeoutSeconds int) (PipeOutcome, error) {
	ctx2 := ctx
	cancel := func() {}
	if timeoutSeconds > 0 {
		ctx2, cancel = context.WithTimeout(ctx, time.Duration(timeoutSeconds)*time.Second)
	}
	defer cancel()

	cmd := exec.CommandContext(ctx2, command, args...)
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return PipeOutcome{ExitCode: 2}, fmt.Errorf("stdout pipe: %w", err)
	}
	stderr, err := cmd.StderrPipe()
	if err != nil {
		return PipeOutcome{ExitCode: 2}, fmt.Errorf("stderr pipe: %w", err)
	}

	if err := cmd.Start(); err != nil {
		return PipeOutcome{ExitCode: 2}, fmt.Errorf("start command: %w", err)
	}

	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
		stream(stdout, outWriter, muterEngine, maxOutputLines)
	}()
	if preserveErrors {
		wg.Add(1)
		go func() {
			defer wg.Done()
			stream(stderr, errWriter, muterEngine, 0)
		}()
	} else {
		go io.Copy(io.Discard, stderr)
	}

	wg.Wait()
	waitErr := cmd.Wait()

	if waitErr == nil {
		return PipeOutcome{ExitCode: 0}, nil
	}
	exitErr, ok := waitErr.(*exec.ExitError)
	if ok {
		if status := exitErr.ExitCode(); status >= 0 {
			return PipeOutcome{ExitCode: status}, nil
		}
	}
	if ctx2.Err() == context.DeadlineExceeded {
		return PipeOutcome{ExitCode: 124}, ctx2.Err()
	}
	return PipeOutcome{ExitCode: 1}, waitErr
}

func stream(r io.Reader, w io.Writer, muterEngine *muter.Muter, maxLines int) {
	reader := bufio.NewReader(r)
	count := 0
	truncated := false
	for {
		line, err := reader.ReadString('\n')
		if err != nil && err != io.EOF {
			fmt.Fprintf(w, "[hushline stream error: %v]\n", err)
			return
		}
		if line == "" && err == io.EOF {
			return
		}
		if maxLines > 0 && count >= maxLines {
			if !truncated {
				fmt.Fprintln(w, "[output truncated]")
				truncated = true
			}
			if err == io.EOF {
				return
			}
			continue
		}
		if muterEngine != nil {
			line = muterEngine.Apply(line)
		}
		fmt.Fprintln(w, strings.TrimRight(line, "\n"))
		count++
		if err == io.EOF {
			return
		}
	}
}
