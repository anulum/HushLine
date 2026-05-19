// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// HUSHLINE — Command entry point

package main

import (
	"os"

	"github.com/local/hushline/internal/engine"
)

func main() {
	os.Exit(engine.Run(os.Args[1:]))
}
