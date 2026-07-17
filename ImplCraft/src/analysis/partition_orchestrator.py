"""
Partition Orchestrator — end-to-end design partition workflow.

Workflow:
1. Analyze hierarchy (DC area report + RTL)
2. Check if design exceeds tool capacity
3. If yes, run partition engine to make harden/flatten/split decisions
4. For split modules, run sub-partition advisor
5. For hardened blocks, run floorplan advisor
6. Generate comprehensive partition report

Usage:
    orchestrator = PartitionOrchestrator(config)
    report = orchestrator.run(
        dc_area_report="synthesis/DC/report/area.rpt",
        rtl_files=["rtl/top.v"],
    )
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .module_graph import ModuleGraph, ModuleNode, PartitionDecision
from .hierarchy_analyzer import HierarchyAnalyzer
from .partition_engine import PartitionEngine, PartitionConfig, PartitionResult
from .floorplan_advisor import FloorplanAdvisor, FloorplanAdvice
from .sub_partition_advisor import SubPartitionAdvisor, SubPartitionAdvice

logger = logging.getLogger("ic_backend")


@dataclass
class PartitionReport:
    """Complete partition report."""
    design_name: str
    needs_partition: bool = False
    total_gates: int = 0
    gate_limit: int = 0
    module_graph: ModuleGraph | None = None
    partition_result: PartitionResult | None = None
    floorplan_advice: FloorplanAdvice | None = None
    sub_partition_advice: list[SubPartitionAdvice] = field(default_factory=list)
    summary: str = ""

    def save(self, output_path: str | Path):
        """Save full report to file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.summary)

        # Also save module graph as JSON
        graph_path = output_path.with_suffix(".json")
        if self.module_graph:
            self.module_graph.save(graph_path)


class PartitionOrchestrator:
    """
    End-to-end design partition orchestrator.

    Usage:
        orch = PartitionOrchestrator(gate_limit=4_000_000)
        report = orch.run(
            dc_area_report="synthesis/DC/report/area.rpt",
            rtl_files=["rtl/top.v"],
            die_width_um=2900,
            die_height_um=1900,
        )
        print(report.summary)
    """

    def __init__(
        self,
        gate_limit: int = 4_000_000,
        min_harden_gates: int = 100_000,
        die_width_um: float = 2900.0,
        die_height_um: float = 1900.0,
        target_utilization: float = 0.7,
    ):
        self.gate_limit = gate_limit
        self.min_harden_gates = min_harden_gates
        self.die_width_um = die_width_um
        self.die_height_um = die_height_um
        self.target_utilization = target_utilization

        self.hierarchy_analyzer = HierarchyAnalyzer(gate_limit=gate_limit)
        self.partition_engine = PartitionEngine(
            PartitionConfig(
                gate_limit=gate_limit,
                min_harden_gates=min_harden_gates,
            )
        )
        self.floorplan_advisor = FloorplanAdvisor()
        self.sub_partition_advisor = SubPartitionAdvisor(gate_limit=gate_limit)

    def run(
        self,
        dc_area_report: str | Path | None = None,
        rtl_files: list[str | Path] | None = None,
        timing_report: str | Path | None = None,
        design_name: str = "top",
    ) -> PartitionReport:
        """
        Run complete partition analysis.

        Args:
            dc_area_report: Path to DC hierarchical area report
            rtl_files: List of RTL Verilog files
            timing_report: Path to timing report (optional)
            design_name: Top-level design name

        Returns:
            PartitionReport with all analysis results
        """
        report = PartitionReport(
            design_name=design_name,
            gate_limit=self.gate_limit,
        )

        # Step 1: Analyze hierarchy
        logger.info("=" * 60)
        logger.info("Step 1: Analyzing design hierarchy")
        logger.info("=" * 60)

        graph = self.hierarchy_analyzer.analyze(
            dc_area_report=dc_area_report,
            rtl_files=rtl_files,
            timing_report=timing_report,
            design_name=design_name,
        )
        report.module_graph = graph
        report.total_gates = graph.total_gate_count()
        report.needs_partition = graph.needs_partition()

        logger.info(f"Total gates: {report.total_gates:,}")
        logger.info(f"Gate limit: {self.gate_limit:,}")
        logger.info(f"Needs partition: {report.needs_partition}")

        # Step 2: Run partition engine
        logger.info("")
        logger.info("=" * 60)
        logger.info("Step 2: Making partition decisions")
        logger.info("=" * 60)

        partition_result = self.partition_engine.partition(graph)
        report.partition_result = partition_result

        logger.info(f"Hardened blocks: {len(partition_result.hardened_blocks)}")
        logger.info(f"Split modules: {len(partition_result.split_modules)}")
        logger.info(f"Flattened modules: {len(partition_result.flattened_modules)}")

        # Step 3: Sub-partition oversized modules
        if partition_result.split_modules:
            logger.info("")
            logger.info("=" * 60)
            logger.info("Step 3: Sub-partitioning oversized modules")
            logger.info("=" * 60)

            for module in partition_result.split_modules:
                advice = self.sub_partition_advisor.advise(module)
                report.sub_partition_advice.append(advice)
                logger.info(
                    f"  {module.name}: {advice.num_splits_needed} splits needed"
                )

        # Step 4: Floorplan hardened blocks
        if partition_result.hardened_blocks:
            logger.info("")
            logger.info("=" * 60)
            logger.info("Step 4: Generating floorplan advice")
            logger.info("=" * 60)

            floorplan_advice = self.floorplan_advisor.advise(
                partition_result,
                die_width_um=self.die_width_um,
                die_height_um=self.die_height_um,
                target_utilization=self.target_utilization,
            )
            report.floorplan_advice = floorplan_advice
            logger.info(f"Block placements: {len(floorplan_advice.block_placements)}")

        # Step 5: Generate comprehensive summary
        report.summary = self._generate_summary(report)

        logger.info("")
        logger.info("=" * 60)
        logger.info("Partition analysis complete")
        logger.info("=" * 60)

        return report

    def _generate_summary(self, report: PartitionReport) -> str:
        """Generate comprehensive summary."""
        lines = [
            "=" * 70,
            f"DESIGN PARTITION REPORT: {report.design_name}",
            "=" * 70,
            "",
            f"Total gates: {report.total_gates:,}",
            f"Gate limit: {report.gate_limit:,}",
            f"Needs partition: {'YES' if report.needs_partition else 'NO'}",
            "",
        ]

        if not report.needs_partition:
            lines.append("Design fits within tool capacity. No partitioning needed.")
            lines.append("Proceed with flat synthesis.")
            return "\n".join(lines)

        # Module hierarchy
        if report.module_graph:
            lines.append("-" * 70)
            lines.append("MODULE HIERARCHY")
            lines.append("-" * 70)
            lines.append(report.module_graph.summary())
            lines.append("")

        # Partition decisions
        if report.partition_result:
            lines.append("-" * 70)
            lines.append("PARTITION DECISIONS")
            lines.append("-" * 70)
            lines.append(report.partition_result.summary)
            lines.append("")

        # Sub-partition advice
        if report.sub_partition_advice:
            lines.append("-" * 70)
            lines.append("SUB-PARTITION ADVICE")
            lines.append("-" * 70)
            for advice in report.sub_partition_advice:
                lines.append(advice.summary)
                lines.append("")

        # Floorplan advice
        if report.floorplan_advice:
            lines.append("-" * 70)
            lines.append("FLOORPLAN ADVICE")
            lines.append("-" * 70)
            lines.append(report.floorplan_advice.summary)
            lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)

    def generate_scripts(
        self, report: PartitionReport, output_dir: str | Path
    ):
        """Generate all partition-related scripts."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Partition synthesis script
        if report.partition_result:
            script_path = output_dir / "partition_synthesis.tcl"
            self.partition_engine.generate_partition_script(
                report.partition_result, script_path
            )
            logger.info(f"Generated: {script_path}")

        # Floorplan constraints script
        if report.floorplan_advice:
            script_path = output_dir / "partition_floorplan.tcl"
            self.floorplan_advisor.generate_floorplan_script(
                report.floorplan_advice, script_path
            )
            logger.info(f"Generated: {script_path}")

        # Main report
        report_path = output_dir / "partition_report.rpt"
        report.save(report_path)
        logger.info(f"Generated: {report_path}")
