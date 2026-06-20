"""Run a larger rtlgen_x simulator stress sweep and save the report."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rtlgen_x.sim import run_stress_sweep, write_stress_sweep_report


def _parse_int_list(raw: str) -> tuple[int, ...]:
    values = tuple(int(part) for part in raw.split(",") if part.strip())
    if not values:
        raise ValueError("expected at least one integer")
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a stress sweep across rtlgen_x compiled simulator benchmarks.")
    parser.add_argument("--widths", default="16,32,64", help="Comma-separated stress module widths")
    parser.add_argument("--cycles", default="256,4096,16384", help="Comma-separated cycle counts")
    parser.add_argument("--chunk-cycles", type=int, default=1024, help="Chunk size for streaming runs")
    parser.add_argument("--repeats", type=int, default=1, help="Benchmark repeats")
    parser.add_argument("--warmup", type=int, default=0, help="Warmup iterations")
    parser.add_argument("--build-root", help="Optional build root for generated simulator artifacts")
    parser.add_argument("--json-out", help="Optional JSON output path")
    args = parser.parse_args()

    report = run_stress_sweep(
        widths=_parse_int_list(args.widths),
        cycles_list=_parse_int_list(args.cycles),
        chunk_cycles=args.chunk_cycles,
        repeats=args.repeats,
        warmup=args.warmup,
        build_root=args.build_root,
    )

    print(f"points={len(report.points)}")
    print(f"widths={report.widths}")
    print(f"max_cycles={report.max_cycles}")
    print(f"max_step_speedup={report.max_step_speedup:.3f}")
    print(f"max_batch_speedup={report.max_batch_speedup:.3f}")
    print(f"max_stream_speedup={report.max_stream_speedup:.3f}")
    for point in report.points:
        print(
            f"w={point.width} cycles={point.cycles} "
            f"step={point.simulator.step_speedup:.3f} "
            f"batch={point.simulator.batch_speedup:.3f} "
            f"stream={point.streaming.stream_speedup:.3f}"
        )

    if args.json_out:
        out_path = write_stress_sweep_report(report, args.json_out)
        print(f"json={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
