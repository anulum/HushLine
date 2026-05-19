# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# HUSHLINE — Python core notes

# Hushline Python Core

This folder contains a publishable Python implementation of the Hushline contract.

## Install from PyPI

```bash
python -m pip install --upgrade hushline
hushline
```

The package also installs a compatibility script:

```bash
hushline-python-core --help
```

## Build locally

```bash
cd cores/core-python
python -m pip install --upgrade build twine
python -m build
```

## Publish

From a tag or release workflow, packages are published by the repository workflow
`publish-python-core`. Configure a repository secret:

- `PYPI_API_TOKEN`

and then trigger manually or publish with a GitHub release.

## Command surface

- `hushline mute -- <command> ...`
- `hushline manifest init [--global|--local]`
- `hushline manifest show`
- `hushline permit status`
- `hushline permit allow [path]`
- `hushline version`

## Implementation

`--pipe-errors` controls stderr shaping; `--raw` bypasses the regex filters.
