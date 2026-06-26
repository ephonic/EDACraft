"""Tests for flow orchestrator and design state."""
import json
import tempfile
from pathlib import Path

from src.db.design_state import (
    DesignState, DesignConfig, FlowStage, StageResult, StageStatus,
    TimingMetrics, AreaMetrics, PDKConfig, LibraryConfig,
)
from src.flow.orchestrator import FlowOrchestrator
from src.flow.stages import DEFAULT_FLOW_STAGES
from src.analysis.qor_analyzer import QoRAnalyzer


def test_design_state_creation():
    state = DesignState()
    assert state.current_stage == FlowStage.INIT
    assert state.config.design_name == "top"


def test_design_state_stage_results():
    state = DesignState()
    result = state.get_stage_result(FlowStage.SYNTHESIS)
    assert result.stage == FlowStage.SYNTHESIS
    assert result.status == StageStatus.PENDING

    result.timing.wns = -0.1
    result.status = StageStatus.PASSED

    # Re-fetch should return same object
    result2 = state.get_stage_result(FlowStage.SYNTHESIS)
    assert result2.timing.wns == -0.1


def test_design_state_artifacts():
    state = DesignState()
    state.record_artifact("syn_v", "/path/to/netlist.v")
    assert state.get_artifact("syn_v") == "/path/to/netlist.v"
    assert state.get_artifact("nonexistent") is None


def test_design_state_save_load():
    state = DesignState()
    state.config.design_name = "save_test"
    state.config.clock_period_ns = 3.0
    state.record_artifact("test_key", "/test/path")

    result = state.get_stage_result(FlowStage.SYNTHESIS)
    result.status = StageStatus.PASSED
    result.timing.wns = -0.05

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        json_path = f.name

    state.save(json_path)

    loaded = DesignState.load(json_path)
    assert loaded.config.design_name == "save_test"
    assert loaded.config.clock_period_ns == 3.0
    assert loaded.artifacts["test_key"] == "/test/path"

    Path(json_path).unlink()


def test_flow_orchestrator_dry_run():
    """Test orchestrator in dry-run mode (no EDA tools needed)."""
    config = DesignConfig(
        design_name="dry_test",
        clock_period_ns=2.0,
        pdk=PDKConfig(tech_file="/path/to/tech.tf"),
        libraries=LibraryConfig(
            std_cell_libs=["/path/to/lib.db"],
            ndm_libs=["/path/to/lib.ndm"],
        ),
        rtl_files=["/path/to/top.v"],
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        orch = FlowOrchestrator(
            config=config,
            work_root=tmpdir,
            dry_run=True,
        )

        state = orch.run()
        status = orch.get_flow_status()

        assert status["total_stages"] == len(DEFAULT_FLOW_STAGES)
        assert len(status["completed"]) == len(DEFAULT_FLOW_STAGES)
        assert len(status["failed"]) == 0


def test_flow_orchestrator_stop_at():
    """Test orchestrator stopping at a specific stage."""
    config = DesignConfig(design_name="stop_test")

    with tempfile.TemporaryDirectory() as tmpdir:
        orch = FlowOrchestrator(
            config=config,
            work_root=tmpdir,
            dry_run=True,
        )

        state = orch.run(stop_at="floorplan")
        status = orch.get_flow_status()

        assert "synthesis" in status["completed"]
        assert "create_lib" in status["completed"]
        assert "floorplan" in status["completed"]
        assert "placement" not in status["completed"]


def test_flow_orchestrator_run_single():
    """Test running a single stage."""
    config = DesignConfig(design_name="single_test")

    with tempfile.TemporaryDirectory() as tmpdir:
        orch = FlowOrchestrator(
            config=config,
            work_root=tmpdir,
            dry_run=True,
        )

        result = orch.run_single("synthesis")
        assert result.status == StageStatus.PASSED


def test_qor_analyzer():
    """Test QoR analysis."""
    state = DesignState()
    state.config.design_name = "qor_test"

    # Add synthesis results
    syn = state.get_stage_result(FlowStage.SYNTHESIS)
    syn.status = StageStatus.PASSED
    syn.timing.wns = -0.05
    syn.timing.tns = -0.5
    syn.area.cell_area = 10000.0

    # Add placement results (slightly worse timing)
    place = state.get_stage_result(FlowStage.PLACEMENT)
    place.status = StageStatus.PASSED
    place.timing.wns = -0.12
    place.timing.tns = -1.2
    place.area.utilization = 0.65

    analyzer = QoRAnalyzer(state)
    report = analyzer.report()

    assert "qor_test" in report
    assert "SYNTHESIS" in report or "synthesis" in report.lower()


def test_qor_analyzer_regression_detection():
    """Test that QoR analyzer detects regressions."""
    state = DesignState()

    syn = state.get_stage_result(FlowStage.SYNTHESIS)
    syn.status = StageStatus.PASSED
    syn.timing.wns = -0.01

    place = state.get_stage_result(FlowStage.PLACEMENT)
    place.status = StageStatus.PASSED
    place.timing.wns = -0.50  # big regression

    analyzer = QoRAnalyzer(state)
    diagnosis = analyzer.analyze()

    assert len(diagnosis.recommendations) > 0
    regressions = [d for d in diagnosis.deltas if d.is_regression]
    assert len(regressions) > 0
