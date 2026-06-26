"""
Flow Orchestrator — chains backend stages with data passing and error checking.

Features:
- Sequential execution of DC → ICC2 → PT → Calibre pipeline
- DesignState passed between stages via artifacts and metrics
- Error/Warning checking after each stage
- RTL suggestions after PT analysis
- Dry-run mode for script generation without tool execution
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from ..db.design_state import (
    DesignConfig, DesignState, FlowStage, StageResult, StageStatus,
)
from ..tools.dc_adapter import DCAdapter
from ..tools.icc2_adapter import ICC2Adapter
from ..tools.pt_adapter import PTAdapter
from ..tools.calibre_adapter import CalibreAdapter
from ..tools.starrc_adapter import StarRCAdapter
from ..tools.innovus_adapter import InnovusAdapter
from ..tools.tempus_adapter import TempusAdapter
from ..tools.pegasus_adapter import PegasusAdapter
from ..analysis.error_checker import ErrorChecker, ToolName
from ..analysis.rtl_advisor import RTLAdvisor
from .stages import FlowStageDefinition, DEFAULT_FLOW_STAGES

logger = logging.getLogger("ic_backend")


class FlowOrchestrator:
    """
    Orchestrates the complete backend flow.

    Usage:
        config = load_config("project.yaml")
        orch = FlowOrchestrator(config, work_root="./work")
        state = orch.run()
        print(orch.get_flow_summary())
    """

    def __init__(
        self,
        config: DesignConfig,
        work_root: str | Path = "./work",
        stages: list[FlowStageDefinition] | None = None,
        dry_run: bool = False,
    ):
        self.state = DesignState(config=config, work_root=str(work_root))
        self.work_root = Path(work_root)
        self.stages = stages or DEFAULT_FLOW_STAGES
        self.dry_run = dry_run
        self._completed: set[str] = set()
        self._failed: set[str] = set()
        self._skipped: set[str] = set()
        self._stage_times: dict[str, float] = {}
        self.error_checker = ErrorChecker()

    def run(
        self,
        stop_at: str | None = None,
        resume_from: str | None = None,
        skip_stages: list[str] | None = None,
    ) -> DesignState:
        """
        Run the complete flow.

        Args:
            stop_at: Stop after this stage name
            resume_from: Skip all stages before this one
            skip_stages: List of stage names to skip
        """
        skip_stages = skip_stages or []
        resuming = resume_from is not None

        logger.info("=" * 70)
        logger.info(f"IC Backend Flow — Design: {self.state.config.design_name}")
        logger.info(f"Work root: {self.work_root}")
        logger.info(f"Stages: {[s.name for s in self.stages]}")
        if self.dry_run:
            logger.info("MODE: DRY-RUN (script generation only)")
        logger.info("=" * 70)

        for stage_def in self.stages:
            # Skip logic
            if resuming and stage_def.name != resume_from:
                self._skipped.add(stage_def.name)
                logger.info(f"  [SKIP] {stage_def.name} (before resume point)")
                continue
            elif resuming and stage_def.name == resume_from:
                resuming = False

            if stage_def.name in skip_stages:
                self._skipped.add(stage_def.name)
                logger.info(f"  [SKIP] {stage_def.name} (in skip list)")
                continue

            # Check dependencies
            missing_deps = [d for d in stage_def.dependencies if d not in self._completed]
            if missing_deps:
                logger.warning(f"  [SKIP] {stage_def.name}: missing dependencies {missing_deps}")
                self._skipped.add(stage_def.name)
                continue

            # Run stage
            success = self._run_stage(stage_def)

            if not success:
                self._failed.add(stage_def.name)
                if not self.dry_run:
                    logger.error(f"  Stage {stage_def.name} FAILED. Stopping flow.")
                    break

            # Stop-at logic
            if stage_def.name == stop_at:
                logger.info(f"  [STOP] Reached stop-at stage: {stop_at}")
                break

        # Generate final reports
        self._generate_flow_summary()

        return self.state

    def run_single(self, stage_name: str) -> StageResult:
        """Run a single stage by name."""
        for stage_def in self.stages:
            if stage_def.name == stage_name:
                self._run_stage(stage_def)
                return self.state.get_stage_result(stage_def.flow_stage)
        raise ValueError(f"Unknown stage: {stage_name}")

    def _run_stage(self, stage_def: FlowStageDefinition) -> bool:
        """Run a single flow stage."""
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"  Stage: {stage_def.name} ({stage_def.tool})")
        logger.info(f"  Description: {stage_def.description}")
        logger.info("=" * 60)

        start_time = time.time()

        # Create adapter
        try:
            adapter = self._create_adapter(stage_def)
        except Exception as e:
            logger.error(f"  Failed to create adapter: {e}")
            return False

        # Handle script-only stages (e.g., DFT) that don't have adapters
        if adapter is None:
            if self.dry_run:
                result = self.state.get_stage_result(stage_def.flow_stage)
                result.status = StageStatus.PASSED
                logger.info(f"  [DRY-RUN] {stage_def.tool} is script-only, marked as PASSED")
                self._completed.add(stage_def.name)
                return True
            else:
                logger.error(f"  {stage_def.tool} requires script generation, not supported in live mode")
                return False

        # Setup work directory
        adapter.setup_work_dir(stage_def.name)

        # Generate script
        try:
            script = adapter.generate_script()
            tcl_path = adapter.write_tcl(script)
            logger.info(f"  Script generated: {tcl_path}")
        except Exception as e:
            logger.error(f"  Script generation failed: {e}")
            return False

        # Execute tool (or dry-run)
        if self.dry_run:
            result = self.state.get_stage_result(stage_def.flow_stage)
            result.status = StageStatus.PASSED
            result.work_dir = str(adapter.work_dir)
            logger.info(f"  [DRY-RUN] Skipped tool execution")
        else:
            # Execute
            exit_code = adapter.execute()
            result = self.state.get_stage_result(stage_def.flow_stage)

            # Parse results
            adapter.parse_results()

            # Check for errors/warnings
            self._check_stage_errors(stage_def, adapter)

            if exit_code == 0:
                result.status = StageStatus.PASSED
                logger.info(f"  Stage PASSED")
            else:
                result.status = StageStatus.FAILED
                logger.error(f"  Stage FAILED (exit code {exit_code})")

        elapsed = time.time() - start_time
        self._stage_times[stage_def.name] = elapsed

        result = self.state.get_stage_result(stage_def.flow_stage)
        result.elapsed_seconds = elapsed

        self._completed.add(stage_def.name)

        # Run RTL advisor after PT
        if stage_def.name == "primetime" and not self.dry_run:
            self._run_rtl_advisor(adapter)

        return result.status == StageStatus.PASSED

    def _create_adapter(self, stage_def: FlowStageDefinition):
        """Create the appropriate tool adapter for a stage."""
        # Synopsys tools
        if stage_def.tool == "DesignCompiler":
            return DCAdapter(self.state)
        elif stage_def.tool == "ICC2":
            return ICC2Adapter(self.state, sub_stage=stage_def.sub_stage or "placement")
        elif stage_def.tool == "PrimeTime":
            return PTAdapter(self.state)
        elif stage_def.tool == "StarRC":
            return StarRCAdapter(self.state, sub_stage=stage_def.sub_stage or "spef")
        # Cadence tools
        elif stage_def.tool == "Innovus":
            return InnovusAdapter(self.state, sub_stage=stage_def.sub_stage or "placement")
        elif stage_def.tool == "Tempus":
            return TempusAdapter(self.state)
        # Siemens tools
        elif stage_def.tool == "Calibre":
            return CalibreAdapter(self.state, sub_stage=stage_def.sub_stage or "drc")
        elif stage_def.tool == "Pegasus":
            return PegasusAdapter(self.state, sub_stage=stage_def.sub_stage or "drc")
        # DFT tools
        elif stage_def.tool == "DFTCompiler":
            # DFT is handled by scripts, not an adapter
            # Return a dummy adapter for dry-run mode
            return None
        else:
            raise ValueError(f"Unknown tool: {stage_def.tool}")

    def _check_stage_errors(self, stage_def: FlowStageDefinition, adapter: Any):
        """Check for errors/warnings after a stage completes."""
        if adapter.work_dir is None:
            return

        log_file = adapter.work_dir / "log" / "run.log"
        if not log_file.exists():
            return

        # Determine tool type
        tool_map = {
            "DesignCompiler": ToolName.DC,
            "ICC2": ToolName.ICC2,
            "PrimeTime": ToolName.PT,
            "Calibre": ToolName.CALIBRE,
        }
        tool = tool_map.get(stage_def.tool)
        if tool is None:
            return

        result = self.error_checker.check_log(log_file, tool)

        if result.fatal_count > 0:
            logger.error(f"  *** {result.fatal_count} FATAL errors in {stage_def.name} ***")
            for msg in result.messages[:5]:
                if msg.severity.value == "fatal":
                    logger.error(f"    {msg.code}: {msg.message[:100]}")
        elif result.error_count > 0:
            logger.warning(f"  {result.error_count} errors in {stage_def.name}")
        elif result.warning_count > 0:
            logger.info(f"  {result.warning_count} warnings in {stage_def.name} (review recommended)")

    def _run_rtl_advisor(self, pt_adapter: Any):
        """Run RTL advisor after PrimeTime analysis."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("  Running RTL Modification Advisor")
        logger.info("=" * 60)

        try:
            advisor = RTLAdvisor(self.state)
            report = advisor.analyze(pt_adapter.work_dir / "PT" / "report")

            if report.suggestions:
                logger.info(f"  Generated {len(report.suggestions)} RTL suggestions")
                report_path = Path(self.state.work_root) / "rtl_suggestions.rpt"
                advisor.save_report(report, report_path)
                logger.info(f"  Suggestions saved to: {report_path}")
            else:
                logger.info("  No RTL suggestions (timing clean or no violations)")

        except Exception as e:
            logger.warning(f"  RTL advisor failed: {e}")

    def _generate_flow_summary(self):
        """Generate final flow summary."""
        logger.info("")
        logger.info("=" * 70)
        logger.info("FLOW SUMMARY")
        logger.info("=" * 70)

        for stage_def in self.stages:
            name = stage_def.name
            if name in self._completed:
                result = self.state.get_stage_result(stage_def.flow_stage)
                status = result.status.value.upper()
                time_str = f"{self._stage_times.get(name, 0):.1f}s"
                logger.info(f"  [✓] {name:20s} {status:10s} {time_str}")
            elif name in self._failed:
                logger.info(f"  [✗] {name:20s} FAILED")
            elif name in self._skipped:
                logger.info(f"  [-] {name:20s} SKIPPED")
            else:
                logger.info(f"  [ ] {name:20s} PENDING")

        logger.info("")

        # Error checker summary
        if self.error_checker.all_results:
            error_report = self.error_checker.generate_report()
            logger.info(error_report)

        # Save design state
        state_file = Path(self.state.work_root) / "design_state.json"
        self.state.save(state_file)
        logger.info(f"Design state saved: {state_file}")

    def get_flow_summary(self) -> str:
        """Get a summary of the flow status."""
        lines = [
            f"Design: {self.state.config.design_name}",
            f"Work root: {self.work_root}",
            "",
            "Stages:",
        ]

        for stage_def in self.stages:
            name = stage_def.name
            if name in self._completed:
                result = self.state.get_stage_result(stage_def.flow_stage)
                status = result.status.value.upper()
                lines.append(f"  ✓ {name:20s} {status}")
            elif name in self._failed:
                lines.append(f"  ✗ {name:20s} FAILED")
            elif name in self._skipped:
                lines.append(f"  - {name:20s} SKIPPED")
            else:
                lines.append(f"    {name:20s} PENDING")

        return "\n".join(lines)

    def get_flow_status(self) -> dict[str, Any]:
        """Get detailed flow status."""
        return {
            "design_name": self.state.config.design_name,
            "total_stages": len(self.stages),
            "completed": list(self._completed),
            "failed": list(self._failed),
            "skipped": list(self._skipped),
            "stage_times": self._stage_times,
            "has_fatal_errors": self.error_checker.has_fatal(),
        }
