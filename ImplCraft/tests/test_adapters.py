"""Tests for tool adapters — Tcl script generation."""
import tempfile
from pathlib import Path

from src.db.design_state import DesignState, DesignConfig, PDKConfig, LibraryConfig
from src.tools.dc_adapter import DCAdapter
from src.tools.icc2_adapter import ICC2Adapter
from src.tools.calibre_adapter import CalibreAdapter
from src.tools.innovus_adapter import InnovusAdapter


def _make_test_state() -> DesignState:
    """Create a test design state."""
    state = DesignState()
    state.config = DesignConfig(
        design_name="test_chip",
        top_module="test_chip",
        clock_period_ns=2.0,
        clock_name="clk",
        die_width_um=500.0,
        die_height_um=500.0,
        core_offset_um=[50, 50, 50, 50],
        scenario="func_slow",
        pdk=PDKConfig(
            name="tsmc28hpcp",
            tech_file="/path/to/tech.tf",
            min_routing_layer="M2",
            max_routing_layer="M9",
            lef_files=["/path/to/tech.lef", "/path/to/stdcell.lef"],
        ),
        libraries=LibraryConfig(
            tap_cell="TAPCELL_BWP30P140",
            std_cell_libs=["/path/to/stdcell.db", "/path/to/stdcell.lib"],
            ndm_libs=["/path/to/stdcell.ndm", "/path/to/ram.ndm"],
        ),
        rtl_files=["/path/to/top.v", "/path/to/sub.v"],
    )
    state.work_root = tempfile.mkdtemp()
    return state


def test_dc_script_generation():
    """Test DC Tcl script generation."""
    state = _make_test_state()
    adapter = DCAdapter(state)
    adapter.setup_work_dir()

    script = adapter.generate_script()

    assert "DESIGN_NAME" in script
    assert "test_chip" in script
    assert "CLOCK_PERIOD" in script
    assert "2.0" in script
    assert "read_verilog" in script
    assert "compile_ultra" in script
    assert "report_qor" in script
    assert "write_sdc" in script
    assert "exit" in script


def test_dc_script_with_sdc():
    """Test DC script with SDC file."""
    state = _make_test_state()
    # Create a dummy SDC file
    sdc_path = Path(state.work_root) / "test.sdc"
    sdc_path.write_text("create_clock -period 2.0 clk\n")
    state.config.sdc_file = str(sdc_path)

    adapter = DCAdapter(state)
    adapter.setup_work_dir()
    script = adapter.generate_script()

    assert "source" in script
    assert str(sdc_path) in script


def test_icc2_create_lib_script():
    """Test ICC2 library creation script."""
    state = _make_test_state()
    adapter = ICC2Adapter(state, sub_stage="create_lib")
    adapter.setup_work_dir()

    script = adapter.generate_script()

    assert "create_lib" in script
    assert "test_chip" in script
    assert "read_verilog" in script
    assert "link_block" in script


def test_icc2_floorplan_script():
    """Test ICC2 floorplan script."""
    state = _make_test_state()
    adapter = ICC2Adapter(state, sub_stage="floorplan")
    adapter.setup_work_dir()

    script = adapter.generate_script()

    assert "initialize_floorplan" in script
    assert "500" in script  # die dimension
    assert "create_boundary_cells" in script
    assert "create_tap_cells" in script


def test_icc2_placement_script():
    """Test ICC2 placement script without TLUPlus falls back to create_placement."""
    state = _make_test_state()
    adapter = ICC2Adapter(state, sub_stage="placement")
    adapter.setup_work_dir()

    script = adapter.generate_script()

    assert "create_placement" in script
    assert "group_path" in script
    assert "M2" in script
    assert "M9" in script
    assert "report_timing" in script


def test_icc2_placement_with_tluplus(tmp_path):
    """Test ICC2 placement script uses place_opt when TLUPlus files exist."""
    state = _make_test_state()
    tlu_max = tmp_path / "max.tluplus"
    tlu_min = tmp_path / "min.tluplus"
    t2i = tmp_path / "tech2itf.map"
    tlu_max.write_text("tluplus")
    tlu_min.write_text("tluplus")
    t2i.write_text("map")
    state.config.pdk.tlu_plus_max = str(tlu_max)
    state.config.pdk.tlu_plus_min = str(tlu_min)
    state.config.pdk.tech2itf_map = str(t2i)

    adapter = ICC2Adapter(state, sub_stage="placement")
    adapter.setup_work_dir()

    script = adapter.generate_script()

    assert "place_opt" in script
    assert "read_parasitic_tech" in script


def test_icc2_cts_script():
    """Test ICC2 CTS script."""
    state = _make_test_state()
    adapter = ICC2Adapter(state, sub_stage="cts")
    adapter.setup_work_dir()

    script = adapter.generate_script()

    assert "clock_opt" in script
    assert "build_clock" in script
    assert "route_clock" in script
    assert "final_opto" in script


def test_icc2_routing_script():
    """Test ICC2 routing script."""
    state = _make_test_state()
    adapter = ICC2Adapter(state, sub_stage="routing")
    adapter.setup_work_dir()

    script = adapter.generate_script()

    assert "route_global" in script
    assert "route_track" in script
    assert "route_detail" in script
    assert "add_redundant_vias" in script
    assert "timing_driven" in script


def test_icc2_route_opt_script():
    """Test ICC2 route optimization script."""
    state = _make_test_state()
    adapter = ICC2Adapter(state, sub_stage="route_opt")
    adapter.setup_work_dir()

    script = adapter.generate_script()

    assert "route_opt" in script
    assert "write_verilog" in script
    assert "write_parasitics" in script
    assert "SPEF" in script


def test_calibre_drc_script():
    """Test Calibre DRC deck generation."""
    state = _make_test_state()
    adapter = CalibreAdapter(state, sub_stage="drc")
    adapter.setup_work_dir()

    script = adapter.generate_script()

    assert "DRC" in script or "LAYOUT" in script
    assert "test_chip" in script


def test_calibre_lvs_script():
    """Test Calibre LVS deck generation."""
    state = _make_test_state()
    adapter = CalibreAdapter(state, sub_stage="lvs")
    adapter.setup_work_dir()

    script = adapter.generate_script()

    assert "LVS" in script or "LAYOUT" in script
    assert "SOURCE" in script
    assert "test_chip" in script


def test_innovus_create_lib_script():
    """Test Innovus create_lib script generation."""
    state = _make_test_state()
    adapter = InnovusAdapter(state, sub_stage="create_lib")
    adapter.setup_work_dir()

    script = adapter.generate_script()

    assert "init_verilog" in script
    assert "init_design" in script
    assert "test_chip" in script
    assert "innovus -batch" in adapter._get_shell_cmd()
    assert adapter.tcl_flag == "-files"
    assert "set init_lef_file" in script
    assert "set library" in script


def test_innovus_floorplan_script():
    """Test Innovus floorplan script generation."""
    state = _make_test_state()
    adapter = InnovusAdapter(state, sub_stage="floorplan")
    adapter.setup_work_dir()

    script = adapter.generate_script()

    assert "floorPlan" in script
    assert "init_design" in script
    assert "addRing" in script
    assert "addStripe" in script


def test_innovus_placement_script():
    """Test Innovus placement script generation."""
    state = _make_test_state()
    adapter = InnovusAdapter(state, sub_stage="placement")
    adapter.setup_work_dir()

    script = adapter.generate_script()

    assert "place_opt_design" in script
    assert "restoreDesign" in script
    assert "timeDesign -prePlace" in script
    assert "setPlaceMode" in script


def test_innovus_cts_script():
    """Test Innovus CTS script generation."""
    state = _make_test_state()
    adapter = InnovusAdapter(state, sub_stage="cts")
    adapter.setup_work_dir()

    script = adapter.generate_script()

    assert "clockOptDesign" in script
    assert "restoreDesign" in script


def test_innovus_routing_script():
    """Test Innovus routing script generation."""
    state = _make_test_state()
    adapter = InnovusAdapter(state, sub_stage="routing")
    adapter.setup_work_dir()

    script = adapter.generate_script()

    assert "routeDesign" in script
    assert "restoreDesign" in script


def test_innovus_route_opt_script():
    """Test Innovus route_opt script generation."""
    state = _make_test_state()
    adapter = InnovusAdapter(state, sub_stage="route_opt")
    adapter.setup_work_dir()

    script = adapter.generate_script()

    assert "optDesign -postRoute" in script
    assert "defOut" in script
    assert "rcOut -spef" in script
