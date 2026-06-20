<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<!-- Commercial license available -->
<!-- © Concepts 1996–2026 Miroslav Šotek. All rights reserved. -->
<!-- © Code 2020–2026 Miroslav Šotek. All rights reserved. -->
<!-- ORCID: 0009-0009-3560-0851 -->
<!-- Contact: www.anulum.li | protoscience@anulum.li -->
<!-- HUSHLINE — public documentation -->

# Hushline Python Core

A standalone, stdlib-only Python implementation of the Hushline command
contract. It is one of four independent cores; it imports nothing from the Go,
Rust, or Node cores and ships with no third-party runtime dependencies, so it
drops into any prompt chain without baggage.

## Install

```bash
python -m pip install --upgrade hushline
hushline version
```

The distribution installs two console scripts that share one entry point:

```bash
hushline mute -- git status
hushline-python-core version
```

## Command surface

- `hushline mute [--raw] [--pipe-errors=BOOL] [--max-lines N] [--max-width N] [--timeout N] -- <command> ...`
- `hushline manifest init [--global|--local]`
- `hushline manifest show`
- `hushline permit [status|allow] [path]`
- `hushline version`

Behaviour matches the Go reference core exactly: identical default profile,
config merge order, redaction, ANSI stripping, line truncation, and exit codes.

## Build locally

```bash
cd cores/core-python
python -m pip install --upgrade build twine
python -m build
```

The built wheel contains the `hushline_core` package; verify before publishing:

```bash
python -c "import zipfile,glob; print(zipfile.ZipFile(glob.glob('dist/*.whl')[0]).namelist())"
```

## Test

```bash
cd cores/core-python
python -m pytest --cov=hushline_core --cov-report=term-missing
```

## Publish

A `python-core-v*` GitHub release triggers the `publish-python-core` workflow,
which builds from `cores/core-python` and uploads to PyPI using the
`PYPI_API_TOKEN` repository secret.
