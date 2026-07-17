"""Tests for industrial-grade features: error checker, RTL advisor, PT adapter."""
import tempfile
from pathlib import Path

from src.db.design_state import (
    PTConfig,
    DesignState, DesignConfig, PDKConfig, LibraryConfig,
    ClockDefinition, TimingDerateConfig, CTSConfig,
    PlacementConfig, RoutingConfig, SynthesisConfig, FlowStage,
)
from src.tools.pt_adapter import PTAdapter
from src.analysis.error_checker import ErrorChecker, ToolName, MessageSeverity
from src.analysis.rtl_advisor import RTLAdvisor, SuggestionType, Severity
from src.config.loader import load_config, save_config


def _make_industrial_state() -> DesignState:
    """Create a test state with full industrial features."""
    state = DesignState()
    state.config = DesignConfig(
        design_name="test_soc",
        top_module="test_soc",
        clock_period_ns=4.0,
        clock_name="clk",
        die_width_um=1000.0,
        die_height_um=800.0,
        core_offset_um=[100, 100, 100, 100],
        scenario="func.tt0p9v.wc.cmax_25c.setup",
        pdk=PDKConfig(
            name="tsmc28hpcp",
            tech_file="/path/to/tech.tf",
            min_routing_layer="M2",
            max_routing_layer="M9",
            min_layer_mode="allow_pin_connection",
            max_layer_mode="hard",
        ),
        libraries=LibraryConfig(
            std_cell_libs=["/path/to/rvt.db", "/path/to/lvt.db"],
            ndm_libs=["/path/to/stdcell.ndm"],
            dont_use_cells=["CLKGATE_*", "FILL*"],
            vt_libs={"RVT": ["/path/to/rvt.db"], "LVT": ["/path/to/lvt.db"]},
            vt_percentage_constraint={"LVT": 5.0},
            driver_cell="BUFFD2BWP30P140",
            tap_cell="TAPCELL_BWP30P140",
            endcap_cell="ENDCAP_BWP30P140",
            decap_cells=["DCAP4_BWP30P140", "DCAP8_BWP30P140"],
            filler_cells=["FILL1_BWP30P140", "FILL2_BWP30P140"],
            antenna_cell="ANTENNA_BWP30P140",
            boundary_cells={"left": "BOUNDARY_LEFTBWP30P140", "right": "BOUNDARY_RIGHTBWP30P140"},
        ),
        rtl_files=["/path/to/top.v", "/path/to/sub.v"],
        clocks=[
            ClockDefinition(
                name="clk",
                period_ns=4.0,
                setup_uncertainty_ns=0.5,
                hold_uncertainty_ns=0.15,
                transition_ns=0.1,
                clock_type="CTS",
                top_metal="M7",
            ),
        ],
        timing_derate=TimingDerateConfig(
            late_factor=1.02,
            early_factor=0.98,
        ),
        cts=CTSConfig(
            target_skew_ns=0.1,
            inter_clock_balance=False,
            ocv_clustering=True,
        ),
        placement=PlacementConfig(
            target_utilization=0.7,
            congestion_effort="medium",
            insert_endcap=True,
            insert_welltap=True,
            insert_predecap=True,
            insert_postdecap=True,
            power_net="VDD",
            ground_net="VSS",
        ),
        routing=RoutingConfig(
            timing_driven=True,
            crosstalk_driven=True,
            antenna_fixing=True,
            si_delta_delay=True,
            si_static_noise=True,
            redundant_via_insertion="medium",
            search_repair_loop=40,
        ),
        synthesis=SynthesisConfig(
            compile_ultra=True,
            tns_effort="high",
            power_optimization=True,
            max_transition_dc=0.5,
            max_fanout_dc=20,
            num_cores=64,
        ),
        pt=PTConfig(
            spef_file="/path/to/test_soc.spef",
            timing_derate_late=1.02,
            timing_derate_early=0.98,
        ),
    )
    state.work_root = tempfile.mkdtemp()
    return state


def test_pt_script_generation():
    """Test PrimeTime script generation with SPEF back-annotation."""
    state = _make_industrial_state()
    adapter = PTAdapter(state)
    adapter.setup_work_dir()

    script = adapter.generate_script()

    assert "test_soc" in script
    assert "read_parasitics" in script
    assert "SPEF" in script
    assert "report_timing" in script
    assert "report_timing" in script
    assert "report_power" in script
    assert "report_constraint" in script
    assert "set_timing_derate" in script
    assert "1.02" in script  # late_factor
    assert "0.98" in script  # early_factor
    assert "exit" in script


def test_dc_script_industrial_features():
    """Test DC script with industrial features."""
    state = _make_industrial_state()
    from src.tools.dc_adapter import DCAdapter
    adapter = DCAdapter(state)
    adapter.setup_work_dir()

    script = adapter.generate_script()

    # Multi-VT
    assert "RVT_libs" in script
    assert "LVT_libs" in script

    # VT constraints (using set_dont_use)
    assert "set_dont_use" in script

    # Timing derate
    assert "set_timing_derate" in script
    assert "1.02" in script

    # Power optimization (new modular commands)
    assert "set_leakage_optimization" in script or "set_dynamic_optimization" in script

    # Clock gating
    assert "set_clock_gating_style" in script

    # Design rules
    assert "set_max_fanout" in script
    assert "set_max_transition" in script

    # Compile
    assert "compile_ultra" in script

    # Reports
    assert "report_qor" in script
    assert "report_timing" in script
    assert "report_area" in script


def test_icc2_routing_si_analysis():
    """Test ICC2 routing with SI analysis options."""
    state = _make_industrial_state()
    from src.tools.icc2_adapter import ICC2Adapter
    adapter = ICC2Adapter(state, sub_stage="routing")
    adapter.setup_work_dir()

    script = adapter.generate_script()

    # SI options use ICC2 app options
    assert "time.si_enable_analysis" in script

    # Route options use ICC2 app options
    assert "route.global.timing_driven" in script
    assert "route.track.timing_driven" in script
    assert "route.detail.timing_driven" in script

    # Route commands
    assert "route_global" in script
    assert "route_track" in script
    assert "route_detail" in script


def test_icc2_cts_industrial():
    """Test ICC2 CTS with industrial clock tree options."""
    state = _make_industrial_state()
    from src.tools.icc2_adapter import ICC2Adapter
    adapter = ICC2Adapter(state, sub_stage="cts")
    adapter.setup_work_dir()

    script = adapter.generate_script()

    assert "set_clock_tree_options" in script
    assert "target_skew" in script
    assert "clock_opt" in script
    assert "report_clock_timing" in script


def test_error_checker_basic():
    """Test error checker with synthetic log."""
    checker = ErrorChecker()

    tmpdir = tempfile.mkdtemp()
    log_file = Path(tmpdir) / "run.log"
    log_file.write_text("""
Starting Design Compiler...
Loading design...
Warning: PSYN-074: Cannot find cell XYZ in library.
Warning: TIM-052: Clock period is too tight for the design.
Information: OPT-001: Cell ABC replaced with DEF.
Error: PSYN-523: Unresolved reference in design.
Compile complete.
""")

    result = checker.check_log(log_file, ToolName.DC)

    assert result.fatal_count == 1  # PSYN-523 (Error: = fatal)
    assert result.warning_count >= 2  # PSYN-074, TIM-052
    assert result.info_count == 1  # OPT-001


def test_error_checker_report():
    """Test error checker report generation."""
    checker = ErrorChecker()

    tmpdir = tempfile.mkdtemp()
    log_file = Path(tmpdir) / "run.log"
    log_file.write_text("Warning: TIM-052: Timing issue.\n")

    results = checker.check_log(log_file, ToolName.DC)
    report = checker.generate_report([results])

    assert "TIM-052" in report
    assert "W" in report  # WARNING tag


def test_error_checker_has_fatal():
    """Test fatal error detection."""
    checker = ErrorChecker()

    tmpdir = tempfile.mkdtemp()
    log_file = Path(tmpdir) / "run.log"
    log_file.write_text("Error: LIB-001: Library not found.\n")

    results = checker.check_log(log_file, ToolName.DC)
    assert checker.has_fatal([results])


def test_rtl_advisor_no_reports():
    """Test RTL advisor when no PT reports exist."""
    state = _make_industrial_state()
    advisor = RTLAdvisor(state)
    report = advisor.analyze("/nonexistent/path")

    assert report.design_name == "test_soc"
    assert report.total_setup_violations == 0
    assert len(report.suggestions) == 0


def test_rtl_advisor_with_violations():
    """Test RTL advisor with synthetic timing paths."""
    state = _make_industrial_state()

    tmpdir = tempfile.mkdtemp()
    report_dir = Path(tmpdir)

    # Create synthetic PT timing report with violations
    timing_report = """
Startpoint: u_cpu/alu_reg_0_reg[0] (rising edge-triggered flip-flop)
Endpoint: u_cpu/alu_reg_1_reg[15] (rising edge-triggered flip-flop)
Path Group: clk
Path Type: max

  Point                                    Incr       Path
  --------------------------------------------------------------
  clock clk (rise edge)                   0.000      0.000
  u_cpu/alu_reg_0_reg[0]/CK (DFFX1)      0.100      0.100
  u_cpu/alu_reg_0_reg[0]/Q (DFFX1)       0.200      0.300
  u_cpu/adder_0/U1/Z (AND2X1)            0.050      0.350
  u_cpu/adder_0/U2/Z (OR2X1)             0.060      0.410
  u_cpu/adder_0/U3/Z (XOR2X1)            0.070      0.480
  u_cpu/adder_0/U4/Z (AND2X1)            0.050      0.530
  u_cpu/adder_0/U5/Z (OR2X1)             0.060      0.590
  u_cpu/adder_0/U6/Z (XOR2X1)            0.070      0.660
  u_cpu/adder_0/U7/Z (AND2X1)            0.050      0.710
  u_cpu/adder_0/U8/Z (OR2X1)             0.060      0.770
  u_cpu/alu_reg_1_reg[15]/D (DFFX1)      0.000      0.770
  data arrival time                                  0.770

  clock clk (rise edge)                   0.500      0.500
  data required time                                 0.500
  --------------------------------------------------------------
  slack (VIOLATED)                                  -0.270

Startpoint: u_mem/cnt_reg[0] (rising edge-triggered flip-flop)
Endpoint: u_mem/cnt_reg[7] (rising edge-triggered flip-flop)
Path Group: clk
Path Type: max

  Point                                    Incr       Path
  --------------------------------------------------------------
  clock clk (rise edge)                   0.000      0.000
  u_mem/cnt_reg[0]/CK (DFFX1)            0.100      0.100
  u_mem/cnt_reg[0]/Q (DFFX1)             0.200      0.300
  u_mem/add_0/U1/Z (XOR2X1)              0.070      0.370
  u_mem/add_0/U2/Z (AND2X1)              0.050      0.420
  u_mem/add_0/U3/Z (OR2X1)               0.060      0.480
  u_mem/add_0/U4/Z (XOR2X1)              0.070      0.550
  u_mem/add_0/U5/Z (AND2X1)              0.050      0.600
  u_mem/add_0/U6/Z (OR2X1)               0.060      0.660
  u_mem/add_0/U7/Z (XOR2X1)              0.070      0.730
  u_mem/add_0/U8/Z (AND2X1)              0.050      0.780
  u_mem/add_0/U9/Z (OR2X1)               0.060      0.840
  u_mem/cnt_reg[7]/D (DFFX1)             0.000      0.840
  data arrival time                                  0.840

  clock clk (rise edge)                   0.500      0.500
  data required time                                 0.500
  --------------------------------------------------------------
  slack (VIOLATED)                                  -0.340
"""
    (report_dir / "critical_paths_setup.rpt").write_text(timing_report)

    advisor = RTLAdvisor(state)
    report = advisor.analyze(report_dir)

    assert report.total_setup_violations == 2
    assert report.worst_slack_ns < 0
    assert len(report.suggestions) > 0

    # Check that pipeline suggestion exists
    pipeline_suggestions = [s for s in report.suggestions if s.suggestion_type == SuggestionType.PIPELINE]
    assert len(pipeline_suggestions) >= 1

    # Check severity
    critical_or_high = [s for s in report.suggestions if s.severity in (Severity.CRITICAL, Severity.HIGH)]
    assert len(critical_or_high) > 0


def test_rtl_advisor_format_report():
    """Test RTL advisor report formatting."""
    state = _make_industrial_state()

    tmpdir = tempfile.mkdtemp()
    report_dir = Path(tmpdir)

    # Minimal timing report
    timing_report = """
Startpoint: u_cpu/reg0 (rising edge-triggered flip-flop)
Endpoint: u_cpu/reg1 (rising edge-triggered flip-flop)
Path Group: clk
  slack (VIOLATED)                                  -0.100
"""
    (report_dir / "critical_paths_setup.rpt").write_text(timing_report)

    advisor = RTLAdvisor(state)
    report = advisor.analyze(report_dir)
    formatted = advisor.format_report(report)

    assert "RTL Modification Suggestions" in formatted
    assert "test_soc" in formatted


def test_config_with_industrial_features():
    """Test config save/load with industrial features."""
    state = _make_industrial_state()

    tmpdir = tempfile.mkdtemp()
    config_path = Path(tmpdir) / "project.yaml"

    save_config(state.config, config_path)
    assert config_path.exists()

    # Load back
    loaded_config, flow_opts = load_config(config_path)

    assert loaded_config.design_name == "test_soc"
    assert loaded_config.timing_derate.late_factor == 1.02
    assert loaded_config.timing_derate.early_factor == 0.98
    assert loaded_config.cts.target_skew_ns == 0.1
    assert loaded_config.placement.insert_endcap is True
    assert loaded_config.routing.si_delta_delay is True
    assert loaded_config.synthesis.num_cores == 64
    assert len(loaded_config.clocks) >= 1
    assert loaded_config.clocks[0].name == "clk"
