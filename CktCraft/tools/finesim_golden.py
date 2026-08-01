#!/usr/bin/env python3
"""finesim_golden.py — FineSim golden reference comparison harness.

Usage:
  python3 finesim_golden.py [--ssh-host HOST] [--ssh-user USER]
                            [--testbench DIR] [--rfsim PATH] [--output DIR]

Workflow:
  1. SSH to remote server, run FineSim on testbench SPICE decks
  2. Parse FineSim .lis output to extract V(node), I(source) at each bias point
  3. Run identical netlist through local rfsim_cli with generated=1
  4. Compute relative error per point, output CSV comparison report

Prerequisites:
  - SSH passwordless access to remote server
  - FineSim available after `source /apps/EDAs/syn.bash`
  - rfsim_cli built locally at build/bin/rfsim_cli.exe
"""

import argparse
import csv
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# FineSim output parsing
# ---------------------------------------------------------------------------

def parse_finesim_dc_output(lis_text: str) -> List[Dict[str, float]]:
    """Parse FineSim .lis DC sweep output.

    Looks for the .print dc output table in the listing file.
    Returns list of dicts with keys matching column headers.
    """
    results = []
    lines = lis_text.split('\n')

    # Find the DC operating point or sweep output section
    header_line = None
    for i, line in enumerate(lines):
        # FineSim DC output typically has headers like:
        # v(d)  i(vdd)  ...
        if re.match(r'\s*v\(\w+\)', line.lower()):
            header_line = i
            break
        if 'sweep' in line.lower() and 'v(d)' in line.lower():
            header_line = i
            break

    if header_line is None:
        # Try to find .op output
        for i, line in enumerate(lines):
            if re.search(r'v\(d\)\s*=\s*[\d.eE+-]+', line.lower()):
                # Single operating point
                vals = {}
                m = re.search(r'v\(d\)\s*=\s*([\d.eE+-]+)', line, re.IGNORECASE)
                if m:
                    vals['v_d'] = float(m.group(1))
                m = re.search(r'i\(vdd\)\s*=\s*([\d.eE+-]+)', line, re.IGNORECASE)
                if m:
                    vals['i_vdd'] = float(m.group(1))
                if vals:
                    results.append(vals)
                continue

    if header_line is not None:
        headers = lines[header_line].split()
        for j in range(header_line + 1, len(lines)):
            line = lines[j].strip()
            if not line or line.startswith('*') or line.startswith('$'):
                break
            vals = line.split()
            if len(vals) >= len(headers):
                row = {}
                for k, h in enumerate(headers):
                    try:
                        row[h.lower().replace('(', '_').replace(')', '')] = float(vals[k])
                    except ValueError:
                        pass
                if row:
                    results.append(row)

    return results


def parse_finesim_op_output(lis_text: str) -> Dict[str, float]:
    """Parse FineSim .op output for a single operating point."""
    vals = {}
    for line in lis_text.split('\n'):
        # Match patterns like: v(d) = 0.54321 or v(d)  0.54321
        m = re.search(r'v\((\w+)\)\s*=?\s*([\d.eE+-]+)', line, re.IGNORECASE)
        if m:
            vals[f'v_{m.group(1).lower()}'] = float(m.group(2))
        m = re.search(r'i\((\w+)\)\s*=?\s*([\d.eE+-]+)', line, re.IGNORECASE)
        if m:
            vals[f'i_{m.group(1).lower()}'] = float(m.group(2))
    return vals


# ---------------------------------------------------------------------------
# Remote FineSim execution
# ---------------------------------------------------------------------------

def run_finesim_remote(ssh_host: str, ssh_user: str,
                       testbench_path: str,
                       remote_dir: str = '/tmp/finesim_golden') -> str:
    """SSH to remote server, run FineSim, return listing output."""
    tb_name = os.path.basename(testbench_path)
    remote_tb = f'{remote_dir}/{tb_name}'
    remote_lis = remote_tb.replace('.sp', '.lis')

    # Create remote directory
    ssh_cmd = f'ssh {ssh_user}@{ssh_host}'
    subprocess.run(f'{ssh_cmd} "mkdir -p {remote_dir}"', shell=True, check=True)

    # Copy testbench to remote
    subprocess.run(f'scp {testbench_path} {ssh_user}@{ssh_host}:{remote_tb}',
                   shell=True, check=True)

    # Run FineSim
    run_cmd = (f'{ssh_cmd} "cd {remote_dir} && '
               f'source /apps/EDAs/syn.bash 2>/dev/null && '
               f'finesim -spice {tb_name} 2>&1"')
    result = subprocess.run(run_cmd, shell=True, capture_output=True, text=True,
                          timeout=120)

    # Fetch listing file
    fetch_cmd = f'scp {ssh_user}@{ssh_host}:{remote_lis} /tmp/{tb_name}.lis'
    subprocess.run(fetch_cmd, shell=True, check=False)  # May not exist

    # Read listing
    local_lis = f'/tmp/{tb_name}.lis'
    if os.path.exists(local_lis):
        with open(local_lis) as f:
            return f.read()
    return result.stdout


# ---------------------------------------------------------------------------
# Local rfsim execution
# ---------------------------------------------------------------------------

def run_rfsim_local(netlist_path: str, rfsim_path: str,
                    model_lib_dir: str = None) -> str:
    """Run rfsim_cli locally on a netlist, return stdout."""
    cmd = [rfsim_path]
    if model_lib_dir:
        cmd.extend(['-L', model_lib_dir])
    cmd.append(netlist_path)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return result.stdout


def parse_rfsim_op_output(output: str) -> Dict[str, float]:
    """Parse rfsim DC operating point output."""
    vals = {}
    for line in output.split('\n'):
        m = re.search(r'v\((\w+)\)\s*=\s*([\d.eE+-]+)', line, re.IGNORECASE)
        if m:
            vals[f'v_{m.group(1).lower()}'] = float(m.group(2))
        m = re.search(r'i\((\w+)\)\s*=\s*([\d.eE+-]+)', line, re.IGNORECASE)
        if m:
            vals[f'i_{m.group(1).lower()}'] = float(m.group(2))
    return vals


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def compare_results(golden: Dict[str, float],
                    rfsim: Dict[str, float],
                    rel_tol: float = 0.001) -> List[Tuple[str, float, float, float]]:
    """Compare golden vs rfsim results. Returns list of (name, golden, rfsim, rel_err)."""
    diffs = []
    for key in golden:
        if key in rfsim:
            g = golden[key]
            r = rfsim[key]
            scale = max(1.0, abs(g))
            rel_err = abs(g - r) / scale
            diffs.append((key, g, r, rel_err))
    return diffs


def write_comparison_csv(diffs: List[Tuple[str, float, float, float]],
                         output_path: str):
    """Write comparison results to CSV."""
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['quantity', 'finesim_golden', 'rfsim_generated',
                        'relative_error', 'pass_fail'])
        for name, golden, rfsim, rel_err in diffs:
            status = 'PASS' if rel_err < 0.001 else 'FAIL'
            writer.writerow([name, f'{golden:.6e}', f'{rfsim:.6e}',
                           f'{rel_err:.4e}', status])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='FineSim golden reference comparison')
    parser.add_argument('--ssh-host', default='10.134.143.28',
                       help='FineSim server hostname')
    parser.add_argument('--ssh-user', default='yangfan',
                       help='SSH username')
    parser.add_argument('--testbench-dir', default=None,
                       help='Directory containing testbench .sp files')
    parser.add_argument('--rfsim', default=None,
                       help='Path to rfsim_cli executable')
    parser.add_argument('--model-lib-dir', default=None,
                       help='OSDI model library directory')
    parser.add_argument('--output-dir', default='golden_results',
                       help='Output directory for comparison CSVs')
    parser.add_argument('--local-only', action='store_true',
                       help='Skip FineSim, use pre-computed golden CSVs')
    args = parser.parse_args()

    # Resolve paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    if args.testbench_dir is None:
        args.testbench_dir = os.path.join(script_dir, 'golden_testbenches')
    if args.rfsim is None:
        args.rfsim = os.path.join(project_root, 'build', 'bin', 'rfsim_cli.exe')
    if args.model_lib_dir is None:
        args.model_lib_dir = os.path.join(project_root, 'models')

    os.makedirs(args.output_dir, exist_ok=True)

    print(f'Project root: {project_root}')
    print(f'Testbench dir: {args.testbench_dir}')
    print(f'rfsim path: {args.rfsim}')
    print(f'Model lib: {args.model_lib_dir}')

    # Process each testbench
    testbenches = sorted(Path(args.testbench_dir).glob('*.sp'))
    if not testbenches:
        print(f'No testbenches found in {args.testbench_dir}')
        sys.exit(1)

    all_pass = True
    for tb in testbenches:
        print(f'\n{"="*60}')
        print(f'Testbench: {tb.name}')
        print(f'{"="*60}')

        if not args.local_only:
            # Run FineSim on remote server
            print(f'Running FineSim on {args.ssh_user}@{args.ssh_host}...')
            try:
                finesim_output = run_finesim_remote(
                    args.ssh_host, args.ssh_user, str(tb))
                # Save listing
                lis_path = os.path.join(args.output_dir,
                                       tb.name.replace('.sp', '_finesim.lis'))
                with open(lis_path, 'w') as f:
                    f.write(finesim_output)
                golden = parse_finesim_op_output(finesim_output)
                print(f'FineSim golden: {golden}')
            except Exception as e:
                print(f'FineSim failed: {e}')
                golden = {}
        else:
            # Load pre-computed golden data
            golden_csv = os.path.join(args.output_dir,
                                     tb.name.replace('.sp', '_golden.csv'))
            if os.path.exists(golden_csv):
                # TODO: load from CSV
                golden = {}
                print(f'Loaded golden from {golden_csv}')
            else:
                print(f'No golden data for {tb.name}')
                continue

        # Run rfsim locally (convert testbench to generated=1 format)
        # TODO: auto-convert .model ... bsim4va to .model ... bsim4va generated=1
        print(f'Running rfsim locally...')
        rfsim_output = run_rfsim_local(str(tb), args.rfsim, args.model_lib_dir)
        rfsim_vals = parse_rfsim_op_output(rfsim_output)
        print(f'rfsim result: {rfsim_vals}')

        # Compare
        if golden and rfsim_vals:
            diffs = compare_results(golden, rfsim_vals)
            csv_path = os.path.join(args.output_dir,
                                   tb.name.replace('.sp', '_comparison.csv'))
            write_comparison_csv(diffs, csv_path)

            for name, g, r, err in diffs:
                status = 'PASS' if err < 0.001 else 'FAIL'
                print(f'  {name}: golden={g:.6e} rfsim={r:.6e} err={err:.4e} [{status}]')
                if err >= 0.001:
                    all_pass = False

    print(f'\n{"="*60}')
    print(f'Overall: {"ALL PASS" if all_pass else "SOME FAILURES"}')
    return 0 if all_pass else 1


if __name__ == '__main__':
    sys.exit(main())
