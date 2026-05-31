<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<!-- Commercial license available -->
<!-- © Concepts 1996–2026 Miroslav Šotek. All rights reserved. -->
<!-- © Code 2020–2026 Miroslav Šotek. All rights reserved. -->
<!-- ORCID: 0009-0009-3560-0851 -->
<!-- Contact: www.anulum.li | protoscience@anulum.li -->
<!-- HUSHLINE — public documentation -->

# Core Selection Policy

To prevent runtime mix-up, each deployment package must declare one explicit active
core:

- `ACTIVE_CORE=core-go`  (reference)
- `ACTIVE_CORE=core-rust`
- `ACTIVE_CORE=core-python`
- `ACTIVE_CORE=core-node`

Rules:

- one and only one `ACTIVE_CORE` value is allowed
- build pipelines must fail if multiple core outputs are emitted
- evidence logs must include the active core value per release
