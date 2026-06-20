<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
<!-- Commercial license available -->
<!-- © Concepts 1996–2026 Miroslav Šotek. All rights reserved. -->
<!-- © Code 2020–2026 Miroslav Šotek. All rights reserved. -->
<!-- ORCID: 0009-0009-3560-0851 -->
<!-- Contact: www.anulum.li | protoscience@anulum.li -->
<!-- HUSHLINE — public documentation -->

# Core benchmarks

Hushline ships four independent cores behind one command contract. You deploy a
single core in the language that suits your stack; this page measures what each
one costs so the choice can be made on data.

## What is measured

Every core runs the identical command:

```bash
hushline mute -- cat <workload>
```

The workload is a generated 20,000-line (~1.04 MB) log mixing ANSI escapes,
`sk-…` and `AKIA…` secrets, and doubled whitespace, so each core exercises ANSI
stripping, redaction, and the silence rules on the same bytes. The harness
records the wall-clock median of 7 repetitions per core and verifies that all
four cores produce **byte-identical output** before reporting any timing.

Reproduce locally:

```bash
bash benchmarks/run_core_benchmarks.sh
```

Results are written to `benchmarks/results/core_latency.json`.

## Results

Measured on an 11th Gen Intel Core i5-11600K @ 3.90 GHz (12 logical cores),
20,000-line workload, 7 repetitions, median wall-clock time. Cross-core output
parity: **identical**.

| Core   | Median  | Throughput | Relative |
|--------|--------:|-----------:|---------:|
| Rust   | 5.07 ms | 204.7 MB/s | 1.0×     |
| Go     | 12.85 ms |  80.7 MB/s | 2.5×     |
| Node   | 52.94 ms |  19.6 MB/s | 10.4×    |
| Python | 59.85 ms |  17.3 MB/s | 11.8×    |

"Relative" is the median time divided by the fastest core's median.

## Reading the numbers honestly

- This is an end-to-end measurement of the whole command, including process
  startup and the child `cat`. For the Node and Python cores, interpreter
  startup is a large fixed cost and dominates at this workload size; their
  steady-state shaping throughput on long-lived input is higher than the table
  implies. Rust and Go start in well under a millisecond, so their figures are
  closer to pure shaping cost.
- The numbers are hardware-specific. Re-run the harness on your target machine
  before drawing conclusions for your deployment.
- All four cores are byte-for-byte equivalent in output, so the choice is purely
  about latency, runtime footprint, and the language your stack already uses.
