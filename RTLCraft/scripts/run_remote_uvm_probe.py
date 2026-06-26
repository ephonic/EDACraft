"""Generate and run one remote VCS/UVM probe from a Python module class."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rtlgen_x.verify.remote_uvm import (
    load_uvm_sequence_steps_json,
    default_remote_dir,
    load_module_instance,
    run_remote_uvm_probe,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a generated UVM/VCS probe on a remote host.")
    parser.add_argument("--module-file", required=True, help="Python file that defines the DUT class")
    parser.add_argument("--module-class", required=True, help="Class name to instantiate from --module-file")
    parser.add_argument("--clock", default="clk", help="Clock signal name")
    parser.add_argument("--host", required=True, help="Remote SSH host")
    parser.add_argument("--remote-dir", help="Remote working directory shell path")
    parser.add_argument("--source-script", default="/apps/EDAs/syn.bash", help="Remote environment setup script")
    parser.add_argument("--local-bundle-dir", help="Optional local output directory for generated bundle")
    parser.add_argument(
        "--directed-sequence-json",
        help="Optional JSON file describing directed steps; supports step objects with inputs/label/active_domains",
    )
    args = parser.parse_args()

    module = load_module_instance(args.module_file, args.module_class)
    directed_sequence = (
        load_uvm_sequence_steps_json(args.directed_sequence_json)
        if args.directed_sequence_json
        else None
    )
    result = run_remote_uvm_probe(
        module,
        clock_name=args.clock,
        host=args.host,
        remote_dir=args.remote_dir or default_remote_dir(getattr(module, "name", args.module_class)),
        source_script=args.source_script,
        local_bundle_dir=Path(args.local_bundle_dir) if args.local_bundle_dir else None,
        directed_sequence=directed_sequence,
    )

    print(f"host={result.host}")
    print(f"remote_dir={result.remote_dir}")
    print(f"local_bundle_dir={result.local_bundle_dir}")
    print(f"returncode={result.returncode}")
    for severity, count in result.summary.severity_counts.items():
        print(f"{severity}={count}")
    for line in result.summary.scoreboard_lines:
        print(line)
    if result.summary.passed:
        print("remote_uvm=PASS")
        return 0
    print("remote_uvm=FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
