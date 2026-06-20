# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# HUSHLINE — core benchmark harness

"""Measure and compare the four cores on one identical mute workload.

Each core runs ``hushline mute -- cat <workload>`` so it shapes the same bytes
through the same rule chain. The harness records wall-clock medians, checks that
every core produces byte-identical output (cross-core parity), and writes a
results JSON. Numbers are measured here, never estimated.
"""

from __future__ import annotations

import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def cores() -> list[dict[str, object]]:
    """Return each core's invocation prefix and environment overlay."""
    py_src = REPO / "cores" / "core-python" / "src"
    return [
        {"name": "go", "prefix": [str(REPO / "benchmarks" / "bin" / "hushline-go")], "env": {}},
        {"name": "rust", "prefix": [str(REPO / "benchmarks" / "bin" / "hushline-rust")], "env": {}},
        {
            "name": "python",
            "prefix": [sys.executable, "-m", "hushline_core"],
            "env": {"PYTHONPATH": str(py_src)},
        },
        {
            "name": "node",
            "prefix": ["node", str(REPO / "cores" / "core-node" / "dist" / "src" / "cli.js")],
            "env": {},
        },
    ]


def run_once(core: dict[str, object], workload: Path, capture: bool) -> tuple[float, bytes]:
    import os

    env = os.environ.copy()
    env.update(core["env"])  # type: ignore[arg-type]
    argv = list(core["prefix"]) + ["mute", "--", "cat", str(workload)]  # type: ignore[operator]
    stdout_target = subprocess.PIPE if capture else subprocess.DEVNULL
    start = time.perf_counter()
    proc = subprocess.run(argv, stdout=stdout_target, stderr=subprocess.DEVNULL, env=env, check=False)
    elapsed = time.perf_counter() - start
    return elapsed, (proc.stdout if capture else b"")


def hardware() -> dict[str, object]:
    model = "unknown"
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                model = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    import os

    return {"cpu": model, "logical_cores": os.cpu_count()}


def main() -> int:
    workload = REPO / "benchmarks" / "bin" / "workload.txt"
    if not workload.exists():
        print(f"workload not found: {workload}", file=sys.stderr)
        return 1
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 7

    workload_bytes = workload.stat().st_size
    workload_lines = sum(1 for _ in workload.open("rb"))

    reference_output: bytes | None = None
    parity_ok = True
    results = []

    for core in cores():
        # One captured run for the parity check, then timed runs to DEVNULL.
        _, output = run_once(core, workload, capture=True)
        if reference_output is None:
            reference_output = output
        elif output != reference_output:
            parity_ok = False

        samples = [run_once(core, workload, capture=False)[0] for _ in range(reps)]
        median = statistics.median(samples)
        results.append(
            {
                "core": core["name"],
                "median_seconds": round(median, 6),
                "min_seconds": round(min(samples), 6),
                "throughput_mb_s": round((workload_bytes / 1_000_000) / median, 3),
            }
        )

    report = {
        "hardware": hardware(),
        "workload": {"lines": workload_lines, "bytes": workload_bytes},
        "repetitions": reps,
        "parity": {"identical": parity_ok, "reference_core": "go"},
        "results": results,
    }

    out_path = REPO / "benchmarks" / "results" / "core_latency.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"parity identical across cores: {parity_ok}")
    print(f"{'core':<8} {'median (ms)':>12} {'throughput (MB/s)':>18}")
    for row in sorted(results, key=lambda r: r["median_seconds"]):
        print(f"{row['core']:<8} {row['median_seconds'] * 1000:>12.2f} {row['throughput_mb_s']:>18.2f}")
    print(f"written: {out_path}")
    return 0 if parity_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
