#!/usr/bin/env python3
"""
Design Partition Analysis CLI.

Usage:
    python -m src.partition --area-report synthesis/DC/report/area.rpt
    python -m src.partition --rtl rtl/top.v rtl/sub.v
    python -m src.partition --area-report area.rpt --rtl top.v --gate-limit 3000000
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .analysis.partition_orchestrator import PartitionOrchestrator


def main():
    parser = argparse.ArgumentParser(
        description="Design Partition Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--area-report",
        type=str,
        help="Path to DC hierarchical area report",
    )
    parser.add_argument(
        "--rtl",
        type=str,
        nargs="+",
        help="RTL Verilog files",
    )
    parser.add_argument(
        "--timing-report",
        type=str,
        help="Path to timing report (optional)",
    )
    parser.add_argument(
        "--gate-limit",
        type=int,
        default=4_000_000,
        help="Gate count limit per block (default: 4,000,000)",
    )
    parser.add_argument(
        "--min-harden",
        type=int,
        default=100_000,
        help="Minimum gates to justify hardening (default: 100,000)",
    )
    parser.add_argument(
        "--die-width",
        type=float,
        default=2900.0,
        help="Die width in um (default: 2900)",
    )
    parser.add_argument(
        "--die-height",
        type=float,
        default=1900.0,
        help="Die height in um (default: 1900)",
    )
    parser.add_argument(
        "--utilization",
        type=float,
        default=0.7,
        help="Target utilization (default: 0.7)",
    )
    parser.add_argument(
        "--design-name",
        type=str,
        default="top",
        help="Top-level design name",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./partition_output",
        help="Output directory for scripts and reports",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        stream=sys.stdout,
    )

    # Check inputs
    if not args.area_report and not args.rtl:
        parser.error("At least one of --area-report or --rtl is required")

    # Run partition analysis
    orchestrator = PartitionOrchestrator(
        gate_limit=args.gate_limit,
        min_harden_gates=args.min_harden,
        die_width_um=args.die_width,
        die_height_um=args.die_height,
        target_utilization=args.utilization,
    )

    report = orchestrator.run(
        dc_area_report=args.area_report,
        rtl_files=args.rtl,
        timing_report=args.timing_report,
        design_name=args.design_name,
    )

    # Print summary
    print("\n" + report.summary)

    # Generate scripts
    output_dir = Path(args.output_dir)
    orchestrator.generate_scripts(report, output_dir)

    print(f"\nScripts and reports saved to: {output_dir}/")
    print(f"  - partition_report.rpt")
    print(f"  - partition_report.json")
    if report.partition_result and report.partition_result.hardened_blocks:
        print(f"  - partition_synthesis.tcl")
    if report.floorplan_advice:
        print(f"  - partition_floorplan.tcl")


if __name__ == "__main__":
    main()
