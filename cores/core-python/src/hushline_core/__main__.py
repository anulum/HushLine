# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# HUSHLINE — Python core entry point

"""Console-script entry point for the Hushline Python core."""

from __future__ import annotations

import sys

from hushline_core.engine import run


def main() -> int:
    """Run Hushline with process argv and return the process exit code."""
    return run(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
