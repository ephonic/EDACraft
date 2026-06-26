#!/usr/bin/env python3
"""
IC Backend Flow — Main CLI Entry Point.

Usage:
    python -m src.run_flow --config project.yaml
    python -m src.run_flow --config project.yaml --dry-run
    python -m src.run_flow --config project.yaml --stage synthesis
    python -m src.run_flow --config project.yaml --resume-from placement
    python -m src.run_flow --config project.yaml --analyze-only
    python -m src.run_flow --init project.yaml   # generate template config
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from src.config.loader import load_config, save_config
from src.db.design_state import DesignConfig, DesignState
from src.flow.orchestrator import FlowOrchestrator
from src.flow.stages import DEFAULT_FLOW_STAGES, FlowStageDefinition
from src.analysis.qor_analyzer import QoRAnalyzer

logger = logging.getLogger("ic_backend")


def main():
    parser = argparse.ArgumentParser(
        description="IC Backend Design Flow Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config", "-c", type=str, help="Path to project YAML config")
    parser.add_argument("--work-root", "-w", type=str, default=None,
                        help="Override work root directory")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate scripts without running tools")
    parser.add_argument("--stage", "-s", type=str, default=None,
                        help="Run only this specific stage")
    parser.add_argument("--stop-at", type=str, default=None,
                        help="Stop flow after this stage")
    parser.add_argument("--resume-from", type=str, default=None,
                        help="Resume flow from this stage (skip earlier stages)")
    parser.add_argument("--analyze-only", action="store_true",
                        help="Only analyze existing design_state.json")
    parser.add_argument("--init", type=str, default=None, metavar="OUTPUT",
                        help="Generate a template config file")

    args = parser.parse_args()

    # Generate template config
    if args.init:
        _generate_template(args.init)
        return

    if not args.config:
        parser.error("--config is required (unless using --init)")

    # Load config
    config, flow_options = load_config(args.config)

    # Override work root
    work_root = args.work_root or flow_options.get("work_root", "./work")
    dry_run = args.dry_run or flow_options.get("dry_run", False)

    # Analyze existing state
    if args.analyze_only:
        state_path = Path(work_root) / "design_state.json"
        if not state_path.exists():
            logger.error(f"No design state found at {state_path}")
            sys.exit(1)
        state = DesignState.load(state_path)
        analyzer = QoRAnalyzer(state)
        report = analyzer.report(Path(work_root) / "qor_report.txt")
        print(report)
        return

    # Build stage list
    stage_names = flow_options.get("stages")
    if stage_names:
        stages = [s for s in DEFAULT_FLOW_STAGES if s.name in stage_names]
    else:
        stages = list(DEFAULT_FLOW_STAGES)

    # Create orchestrator
    orchestrator = FlowOrchestrator(
        config=config,
        work_root=work_root,
        stages=stages,
        dry_run=dry_run,
    )

    # Run
    if args.stage:
        result = orchestrator.run_single(args.stage)
        print(f"Stage '{args.stage}': {result.status.value}")
    elif args.resume_from:
        state = orchestrator.run_from(args.resume_from)
    elif args.stop_at:
        state = orchestrator.run(stop_at=args.stop_at)
    else:
        state = orchestrator.run()

    # Print QoR analysis
    analyzer = QoRAnalyzer(orchestrator.state)
    report = analyzer.report(Path(work_root) / "qor_report.txt")
    print("\n" + report)


def _generate_template(output_path: str):
    """Generate a template project config."""
    config = DesignConfig()
    config.design_name = "my_design"
    config.top_module = "top"
    config.clock_period_ns = 2.0
    config.clock_name = "clk"
    config.die_width_um = 2900.0
    config.die_height_um = 1900.0
    config.pdk.tech_file = "/path/to/tech.tf"
    config.rtl_files = ["/path/to/rtl/top.v"]

    flow_options = {
        "work_root": "./work",
        "dry_run": False,
        "stages": None,
    }

    save_config(config, output_path, flow_options)
    print(f"Template config generated: {output_path}")
    print("Edit the file and run: python -m src.run_flow --config " + output_path)


if __name__ == "__main__":
    main()
