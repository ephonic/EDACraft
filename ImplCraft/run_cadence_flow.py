#!/usr/bin/env python3
"""
Run Cadence flow for bp_pe design: DC → Innovus → StarRC → Tempus → Pegasus.
Executes each stage sequentially with error checking.
"""
import sys
import time
import logging
from pathlib import Path

sys.path.insert(0, "src")

from config.loader import load_config
from db.design_state import DesignState, FlowStage, StageStatus
from tools.innovus_adapter import InnovusAdapter
from tools.starrc_adapter import StarRCAdapter
from tools.tempus_adapter import TempusAdapter
from tools.pegasus_adapter import PegasusAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("cadence_flow")

WORK_ROOT = "./work_bp_pe_cadence"
STAGES = ["create_lib", "floorplan", "placement", "cts", "routing", "route_opt", "finish"]

def run_stage(state, sub_stage, adapter_cls, **kwargs):
    """Run a single stage and return success."""
    log.info(f"\n{'='*60}")
    log.info(f"  STAGE: {sub_stage}")
    log.info(f"{'='*60}")
    t0 = time.time()

    adapter = adapter_cls(state, **kwargs)
    adapter.setup_work_dir(sub_stage)

    # Generate script
    script = adapter.generate_script()
    tcl_path = adapter.write_tcl(script)
    log.info(f"  Script: {tcl_path} ({len(script.splitlines())} lines)")

    # Execute
    log.info(f"  Executing {adapter.tool_name}...")
    result = adapter.execute()

    elapsed = time.time() - t0
    log.info(f"  Status: {result.status.value} ({elapsed:.1f}s)")

    if result.messages:
        for msg in result.messages[:5]:
            log.warning(f"  MSG: {msg}")

    # Parse results
    adapter.parse_results()

    # Save state after each stage
    state.save(Path(WORK_ROOT) / "design_state.json")

    return result.status == StageStatus.PASSED


def main():
    config, raw = load_config("examples/bp_pe/bp_pe.yaml")
    state = DesignState(config=config, work_root=WORK_ROOT)

    log.info(f"Design: {config.design_name} ({config.top_module})")
    log.info(f"Work root: {WORK_ROOT}")
    log.info(f"Stages: {STAGES}")

    # Record synthesis artifacts (from copied DC output)
    wr = Path(WORK_ROOT).resolve()
    state.record_artifact("syn_v", str(wr / "synthesis" / "DC" / "out" / f"{config.design_name}.v"))
    state.record_artifact("syn_sdc", str(wr / "synthesis" / "DC" / "out" / f"{config.design_name}.sdc"))
    state.record_artifact("syn_ddc", str(wr / "synthesis" / "DC" / "out" / f"{config.design_name}.ddc"))

    passed_stages = []
    failed_stage = None

    for sub_stage in STAGES:
        ok = run_stage(state, sub_stage, InnovusAdapter, sub_stage=sub_stage)
        if ok:
            passed_stages.append(sub_stage)
            log.info(f"  ✓ {sub_stage} PASSED")
        else:
            failed_stage = sub_stage
            log.error(f"  ✗ {sub_stage} FAILED")
            # Check log for error details
            log_path = Path(WORK_ROOT) / sub_stage / "log" / "run.log"
            if log_path.exists():
                log_text = log_path.read_text(errors="ignore")
                error_lines = [l for l in log_text.splitlines() if "ERROR" in l.upper() or "Error" in l]
                for el in error_lines[:5]:
                    log.error(f"    {el}")
            break

    # Summary
    log.info(f"\n{'='*60}")
    log.info(f"  FLOW SUMMARY")
    log.info(f"{'='*60}")
    log.info(f"  Passed: {passed_stages}")
    if failed_stage:
        log.info(f"  Failed: {failed_stage}")
        log.info(f"  Result: INCOMPLETE")
    else:
        log.info(f"  Result: ALL STAGES PASSED ✓")

    state.save(Path(WORK_ROOT) / "design_state.json")
    return 0 if not failed_stage else 1


if __name__ == "__main__":
    sys.exit(main())
