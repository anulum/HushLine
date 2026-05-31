// SPDX-License-Identifier: AGPL-3.0-or-later
// Commercial license available
// © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
// © Code 2020–2026 Miroslav Šotek. All rights reserved.
// ORCID: 0009-0009-3560-0851
// Contact: www.anulum.li | protoscience@anulum.li
// HUSHLINE — command entry point tests

package main

import "testing"

func TestRunDelegatesArgumentsToEngine(t *testing.T) {
	if exitCode := run([]string{"version"}); exitCode != 0 {
		t.Fatalf("run(version) = %d, want 0", exitCode)
	}
}
