#!/usr/bin/env python3
"""
PG Network Planning CLI

Provides command-line interface for PG network planning, including:
- PG pad count calculation
- PG pad placement strategy
- I/O pad placement
- Bond pad placement
- IR-drop estimation

Usage:
    python -m src.pg_network --power 1.0 --voltage 0.9 --die 2900 1900
    python -m src.pg_network --config project.yaml --output-dir ./pg_output
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .analysis.pg_network_advisor import (
    PGNetworkAdvisor,
    PowerConfig,
    PadSpec,
    PadType,
    PlacementStrategy,
)
from .config.loader import load_config


def main():
    parser = argparse.ArgumentParser(
        description="PG Network Planning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    # Input options
    parser.add_argument(
        "--config",
        type=str,
        help="Design configuration file (YAML)",
    )
    parser.add_argument(
        "--power",
        type=float,
        default=1.0,
        help="Total power consumption in watts (default: 1.0W)",
    )
    parser.add_argument(
        "--voltage",
        type=float,
        default=0.9,
        help="Core supply voltage in volts (default: 0.9V)",
    )
    parser.add_argument(
        "--io-voltage",
        type=float,
        help="I/O supply voltage in volts (optional)",
    )
    
    # Die size
    parser.add_argument(
        "--die",
        type=float,
        nargs=2,
        metavar=("WIDTH", "HEIGHT"),
        default=[2900.0, 1900.0],
        help="Die size in micrometers (default: 2900 1900)",
    )
    
    # Pad specifications
    parser.add_argument(
        "--pad-size",
        type=float,
        nargs=2,
        metavar=("WIDTH", "HEIGHT"),
        default=[80.0, 80.0],
        help="PG pad size in micrometers (default: 80 80)",
    )
    parser.add_argument(
        "--pad-pitch",
        type=float,
        default=100.0,
        help="PG pad pitch in micrometers (default: 100)",
    )
    parser.add_argument(
        "--max-current",
        type=float,
        default=0.1,
        help="Maximum current per PG pad in amperes (default: 0.1A)",
    )
    
    # Placement options
    parser.add_argument(
        "--strategy",
        type=str,
        choices=["uniform", "clustered", "peripheral", "corner"],
        default="uniform",
        help="PG pad placement strategy (default: uniform)",
    )
    parser.add_argument(
        "--num-io-pads",
        type=int,
        default=100,
        help="Number of I/O pads (default: 100)",
    )
    parser.add_argument(
        "--num-bond-pads",
        type=int,
        default=0,
        help="Number of bond pads (default: 0, no bond pads)",
    )
    
    # Output options
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./pg_output",
        help="Output directory (default: ./pg_output)",
    )
    parser.add_argument(
        "--generate-script",
        action="store_true",
        help="Generate ICC2 PG creation script",
    )
    
    # Advanced options
    parser.add_argument(
        "--power-domains",
        type=int,
        default=1,
        help="Number of power domains (default: 1)",
    )
    parser.add_argument(
        "--current-density-limit",
        type=float,
        default=0.001,
        help="Current density limit in A/um for EM checking (default: 0.001)",
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
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 70)
    logger.info("PG Network Planning")
    logger.info("=" * 70)
    
    # Load configuration if provided
    if args.config:
        logger.info(f"Loading configuration from: {args.config}")
        config, flow_opts = load_config(args.config)
        
        # Extract power info from config
        power_config = PowerConfig(
            vdd_voltage=args.voltage,
            vddq_voltage=args.io_voltage,
            total_power_w=args.power,
            core_power_w=args.power * 0.7,  # Assume 70% core, 30% I/O
            io_power_w=args.power * 0.3,
            num_power_domains=args.power_domains,
            current_density_limit_a_um=args.current_density_limit,
        )
        
        die_width = config.die_width_um
        die_height = config.die_height_um
    else:
        # Use command-line parameters
        power_config = PowerConfig(
            vdd_voltage=args.voltage,
            vddq_voltage=args.io_voltage,
            total_power_w=args.power,
            core_power_w=args.power * 0.7,
            io_power_w=args.power * 0.3,
            num_power_domains=args.power_domains,
            current_density_limit_a_um=args.current_density_limit,
        )
        
        die_width = args.die[0]
        die_height = args.die[1]
    
    # Create pad specification
    pad_spec = PadSpec(
        pad_type=PadType.PG_PAD,
        width_um=args.pad_size[0],
        height_um=args.pad_size[1],
        pitch_um=args.pad_pitch,
        max_current_a=args.max_current,
    )
    
    # Map strategy string to enum
    strategy_map = {
        "uniform": PlacementStrategy.UNIFORM,
        "clustered": PlacementStrategy.CLUSTERED,
        "peripheral": PlacementStrategy.PERIPHERAL,
        "corner": PlacementStrategy.CORNER,
    }
    strategy = strategy_map[args.strategy]
    
    # Create advisor and plan
    logger.info(f"\nDesign parameters:")
    logger.info(f"  Power: {args.power}W @ {args.voltage}V")
    logger.info(f"  Die size: {die_width} x {die_height} um")
    logger.info(f"  Placement strategy: {args.strategy}")
    logger.info(f"  I/O pads: {args.num_io_pads}")
    logger.info(f"  Bond pads: {args.num_bond_pads}")
    logger.info("")
    
    advisor = PGNetworkAdvisor()
    plan = advisor.plan_pg_network(
        power_config=power_config,
        pad_spec=pad_spec,
        die_width_um=die_width,
        die_height_um=die_height,
        num_io_pads=args.num_io_pads,
        num_bond_pads=args.num_bond_pads,
        placement_strategy=strategy,
    )
    
    # Print summary
    print(plan.summary)
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save report
    report_path = output_dir / "pg_network_report.txt"
    with open(report_path, "w") as f:
        f.write(plan.summary)
    logger.info(f"Report saved to: {report_path}")
    
    # Save detailed JSON
    json_path = output_dir / "pg_network_plan.json"
    plan_dict = {
        "design_name": plan.design_name,
        "die_size": {
            "width_um": plan.die_width_um,
            "height_um": plan.die_height_um,
        },
        "pg_requirements": {
            "total_pads": plan.total_pg_pads_needed,
            "vdd_pads": plan.vdd_pads_needed,
            "vss_pads": plan.vss_pads_needed,
        },
        "placement": {
            "strategy": plan.placement_strategy.value,
            "pg_pads": [
                {
                    "id": p.pad_id,
                    "type": p.pad_type.value,
                    "x_um": p.x_um,
                    "y_um": p.y_um,
                    "net": p.net_name,
                }
                for p in plan.pg_pad_placements
            ],
            "io_pads": [
                {
                    "id": p.pad_id,
                    "type": p.pad_type.value,
                    "x_um": p.x_um,
                    "y_um": p.y_um,
                    "net": p.net_name,
                }
                for p in plan.io_pad_placements
            ],
            "bond_pads": [
                {
                    "id": p.pad_id,
                    "type": p.pad_type.value,
                    "x_um": p.x_um,
                    "y_um": p.y_um,
                    "net": p.net_name,
                }
                for p in plan.bond_pad_placements
            ],
        },
        "analysis": {
            "ir_drop_mv": plan.estimated_ir_drop_mv,
            "max_current_density_a_um": plan.max_current_density_a_um,
            "em_violations": plan.em_violations,
        },
        "recommendations": plan.recommendations,
        "warnings": plan.warnings,
    }
    
    import json
    with open(json_path, "w") as f:
        json.dump(plan_dict, f, indent=2)
    logger.info(f"JSON plan saved to: {json_path}")
    
    # Generate ICC2 script if requested
    if args.generate_script:
        script_path = output_dir / "pg_network.tcl"
        advisor.generate_pg_script(plan, str(script_path), tool="icc2")
        logger.info(f"ICC2 script saved to: {script_path}")
    
    logger.info("\n" + "=" * 70)
    logger.info("PG Network Planning Complete")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
