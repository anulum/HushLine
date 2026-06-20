# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# HUSHLINE — Python core package

"""Standalone Python core for the Hushline command contract.

This package is one of four independent cores (Go, Rust, Python, Node). It
shares no runtime artefacts with the others and depends only on the standard
library. Its observable behaviour — default profile, configuration merge order,
redaction, ANSI stripping, line truncation, and exit codes — matches the Go
reference core exactly.
"""

from hushline_core.engine import run
from hushline_core.version import VERSION

__all__ = ["run", "__version__"]

__version__ = VERSION
