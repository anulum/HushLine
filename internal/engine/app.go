// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// HUSHLINE — core engine bootstrap

package engine

import (
	"context"
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	"github.com/local/hushline/internal/config"
	"github.com/local/hushline/internal/muter"
	"github.com/local/hushline/internal/pipeline"
	"github.com/local/hushline/internal/version"
)

const usage = `hushline - local command output shaping utility

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
`

func Run(argv []string) int {
	if len(argv) == 0 || argv[0] == "help" || argv[0] == "-h" || argv[0] == "--help" {
		fmt.Print(usage)
		return 0
	}

	switch argv[0] {
	case "mute":
		return muteCommand(argv[1:])
	case "manifest":
		return manifestCommand(argv[1:])
	case "permit":
		return permitCommand(argv[1:])
	case "version":
		fmt.Printf("hushline %s\n", version.Version)
		return 0
	default:
		fmt.Printf("unknown command: %s\n\n", argv[0])
		fmt.Print(usage)
		return 1
	}
}

func manifestCommand(argv []string) int {
	cwd, err := os.Getwd()
	if err != nil {
		fmt.Fprintf(os.Stderr, "cwd lookup: %v\n", err)
		return 1
	}
	if len(argv) == 0 || argv[0] == "show" {
		fmt.Printf("global profile: %s\n", config.GlobalProfilePath())
		fmt.Printf("local profile:  %s\n", config.LocalProfilePath(cwd))
		return 0
	}
	if argv[0] != "init" {
		fmt.Fprintf(os.Stderr, "manifest: unknown action %q\n", argv[0])
		return 2
	}

	fs := flag.NewFlagSet("manifest init", flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	useGlobal := fs.Bool("global", false, "write global profile")
	useLocal := fs.Bool("local", false, "write local profile")
	_ = fs.Parse(argv[1:])

	if err := emitProfile(*useGlobal, *useLocal, cwd); err != nil {
		fmt.Fprintf(os.Stderr, "manifest init: %v\n", err)
		return 1
	}
	return 0
}

func permitCommand(argv []string) int {
	if len(argv) == 0 {
		argv = []string{"status"}
	}
	cwd, err := os.Getwd()
	if err != nil {
		fmt.Fprintf(os.Stderr, "cwd lookup: %v\n", err)
		return 1
	}

	switch argv[0] {
	case "status":
		if config.IsPermitted(cwd) {
			fmt.Println("permitted: true")
			return 0
		}
		fmt.Println("permitted: false")
		return 2
	case "allow":
		target := cwd
		if len(argv) > 1 {
			target = argv[1]
		}
		if err := config.MarkPermitted(target); err != nil {
			fmt.Fprintf(os.Stderr, "permit allow: %v\n", err)
			return 1
		}
		fmt.Printf("permitted: %s\n", target)
		return 0
	default:
		fmt.Fprintf(os.Stderr, "permit: unknown action %q\n", argv[0])
		return 2
	}
}

func muteCommand(argv []string) int {
	fs := flag.NewFlagSet("mute", flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	keepRaw := fs.Bool("raw", false, "bypass silence muting")
	pipeErrors := fs.Bool("pipe-errors", true, "forward stderr through pipeline")
	maxLines := fs.Int("max-lines", 0, "override max output lines")
	maxWidth := fs.Int("max-width", 0, "override max line width")
	timeout := fs.Int("timeout", 0, "timeout in seconds")
	if err := fs.Parse(argv); err != nil {
		fmt.Fprintf(os.Stderr, "mute options: %v\n", err)
		return 2
	}

	args := fs.Args()
	if len(args) > 0 && args[0] == "--" {
		args = args[1:]
	}
	if len(args) == 0 {
		fmt.Fprintf(os.Stderr, "mute: missing command\n")
		return 2
	}

	cwd, err := os.Getwd()
	if err != nil {
		fmt.Fprintf(os.Stderr, "cwd lookup: %v\n", err)
		return 1
	}
	profile, err := config.LoadProfile(cwd)
	if err != nil {
		fmt.Fprintf(os.Stderr, "profile: %v\n", err)
		return 1
	}

	if *maxLines > 0 {
		profile.MaxOutputLines = *maxLines
	}
	if *maxWidth > 0 {
		profile.MaxLineWidth = *maxWidth
	}
	profile.PreserveErrors = *pipeErrors

	if profile.RequirePermit && !config.IsPermitted(cwd) {
		fmt.Fprintln(os.Stderr, "hushline: current directory not permitted. run `hushline permit allow` first or set require_permit: false")
		return 3
	}

	command := args[0]
	commandArgs := args[1:]
	var silence *muter.Muter
	if *keepRaw {
		silence = nil
	} else {
		instance, err := muter.Compose(profile)
		if err != nil {
			fmt.Fprintf(os.Stderr, "mute: %v\n", err)
			return 1
		}
		silence = instance
	}

	result, err := pipeline.Through(context.Background(), command, commandArgs, os.Stdout, os.Stderr, silence, profile.MaxOutputLines, profile.PreserveErrors, *timeout)
	if err != nil && result.ExitCode == 124 {
		fmt.Fprintf(os.Stderr, "hushline: command timed out\n")
		return 124
	}
	if err != nil {
		if strings.TrimSpace(err.Error()) != "" {
			fmt.Fprintf(os.Stderr, "%s\n", strings.TrimSpace(err.Error()))
		}
	}
	return result.ExitCode
}

func emitProfile(writeGlobal bool, writeLocal bool, cwd string) error {
	target := ""
	switch {
	case writeGlobal && writeLocal, !writeGlobal && !writeLocal:
		target = config.GlobalProfilePath()
	case writeGlobal:
		target = config.GlobalProfilePath()
	case writeLocal:
		target = config.LocalProfilePath(cwd)
	}
	if target == "" {
		return fmt.Errorf("could not resolve profile path")
	}
	if err := os.MkdirAll(filepath.Dir(target), 0o700); err != nil {
		return err
	}
	if err := config.WriteProfile(target); err != nil {
		return err
	}
	fmt.Printf("profile written: %s\n", target)
	return nil
}
