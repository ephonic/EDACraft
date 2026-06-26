"""Probe remote SSH/VCS environment readiness for rtlgen_x UVM runs."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rtlgen_x.verify.remote_uvm import probe_remote_uvm_environment


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe remote VCS/UVM environment readiness.")
    parser.add_argument("--host", required=True, help="Remote SSH host")
    parser.add_argument("--source-script", default="/apps/EDAs/syn.bash", help="Remote environment setup script")
    args = parser.parse_args()

    report = probe_remote_uvm_environment(
        host=args.host,
        source_script=args.source_script,
    )

    print(f"host={report.host}")
    print(f"source_script={report.source_script}")
    print(f"returncode={report.returncode}")
    print(f"environment_ok={int(report.environment_ok)}")
    print(f"vcs_path={report.vcs_path or ''}")
    if report.stdout:
        print("stdout<<")
        print(report.stdout)
        print(">>")
    if report.stderr:
        print("stderr<<")
        print(report.stderr)
        print(">>")
    return 0 if report.environment_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
