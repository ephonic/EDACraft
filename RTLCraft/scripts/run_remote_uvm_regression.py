"""Run a batch remote VCS/UVM regression from Python module classes."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rtlgen_x.verify.remote_uvm import (
    RemoteUvmTarget,
    run_remote_uvm_regression,
    write_remote_uvm_regression_report,
)


def _parse_target(spec: str) -> RemoteUvmTarget:
    parts = spec.split(":")
    if len(parts) not in {2, 3}:
        raise ValueError("target must be MODULE_FILE:CLASS[:CLOCK]")
    module_file, module_class = parts[:2]
    clock_name = parts[2] if len(parts) == 3 else "clk"
    path = Path(module_file)
    stem = path.stem
    path_parts = path.parts
    if "modules" in path_parts:
        idx = path_parts.index("modules")
        if idx + 1 < len(path_parts):
            stem = path_parts[idx + 1]
    return RemoteUvmTarget(
        name=stem,
        module_file=path,
        module_class=module_class,
        clock_name=clock_name,
    )


def _earphone_l5_targets() -> tuple[RemoteUvmTarget, ...]:
    return (
        _parse_target("earphone/modules/apb_bridge/layer_L5_dsl/src/dsl.py:EarphoneAPBBridge"),
        _parse_target("earphone/modules/sram256k/layer_L5_dsl/src/dsl.py:EarphoneSRAM256K"),
        _parse_target("earphone/modules/i2c/layer_L5_dsl/src/dsl.py:EarphoneI2C"),
        _parse_target("earphone/modules/qspi/layer_L5_dsl/src/dsl.py:EarphoneQSPI"),
        _parse_target("earphone/modules/rv32/layer_L5_dsl/src/dsl.py:EarphoneRV32"),
        _parse_target("earphone/modules/fft256/layer_L5_dsl/src/dsl.py:EarphoneFFT256"),
        _parse_target("earphone/modules/simd16/layer_L5_dsl/src/dsl.py:EarphoneSIMD16"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run multiple generated UVM/VCS probes on a remote host.")
    parser.add_argument("--host", required=True, help="Remote SSH host")
    parser.add_argument(
        "--target",
        action="append",
        default=[],
        help="MODULE_FILE:CLASS[:CLOCK], repeatable",
    )
    parser.add_argument(
        "--preset",
        choices=("earphone-l5",),
        help="Predefined regression target set",
    )
    parser.add_argument("--source-script", default="/apps/EDAs/syn.bash", help="Remote environment setup script")
    parser.add_argument("--local-root", help="Optional local directory for generated bundles")
    parser.add_argument("--json-out", help="Optional JSON report path")
    args = parser.parse_args()

    targets = []
    if args.preset == "earphone-l5":
        targets.extend(_earphone_l5_targets())
    for spec in args.target:
        targets.append(_parse_target(spec))
    if not targets:
        parser.error("at least one --target or --preset is required")

    report = run_remote_uvm_regression(
        targets,
        host=args.host,
        source_script=args.source_script,
        local_root=Path(args.local_root) if args.local_root else None,
    )
    if args.json_out:
        write_remote_uvm_regression_report(report, args.json_out)

    for entry in report.entries:
        if entry.result is not None:
            counts = entry.result.summary.severity_counts
            print(
                f"{entry.target.name}: {entry.status} "
                f"(rc={entry.result.returncode}, "
                f"UVM_ERROR={counts['UVM_ERROR']}, UVM_FATAL={counts['UVM_FATAL']})"
            )
            for line in entry.result.summary.scoreboard_lines:
                print(f"  {line}")
        else:
            print(f"{entry.target.name}: {entry.status} ({entry.error})")

    print(f"passed={len(report.passed)} failed={len(report.failed)} total={len(report.entries)}")
    return 0 if not report.failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
