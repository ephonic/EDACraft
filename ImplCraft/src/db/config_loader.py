"""
Design Config Loader — reads per-design YAML configs into DesignConfig.

Supports two modes:
  1. Single-file mode: Load from a single YAML file (backward compatible)
  2. Multi-file mode: Load from a directory containing separate YAML files:
     - common.yaml (required): Basic design info, libraries, PDK
     - synthesis.yaml (optional): DC synthesis options
     - primetime.yaml (optional): PrimeTime STA options
     - icc2.yaml (optional): ICC2 physical implementation options
     - calibre.yaml (optional): Calibre physical verification options
     - innovus.yaml (optional): Innovus physical implementation options
     - tempus.yaml (optional): Tempus timing signoff options
     - pegasus.yaml (optional): Pegasus physical verification options

Usage:
    # Single-file mode (backward compatible)
    state = load_design_config("configs/FullSystem.yaml")
    
    # Multi-file mode (new)
    state = load_design_config("configs/FullSystem/")
"""
from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any

from .design_state import (
    DesignConfig, DesignState,
    LibraryConfig, PDKConfig, SynthesisConfig, PTConfig,
    TimingDerateConfig, CTSConfig, PlacementConfig, RoutingConfig,
    ClockDefinition, MCMMScenario, EDAEnvironment,
)


def load_design_config(path: str | Path) -> DesignState:
    """
    Load design config from file or directory.
    
    Args:
        path: Path to YAML file or directory containing YAML files
        
    Returns:
        Fully populated DesignState
        
    Raises:
        FileNotFoundError: If path doesn't exist
        ValueError: If directory mode and common.yaml is missing
    """
    path = Path(path)
    
    if path.is_dir():
        return _load_from_directory(path)
    elif path.is_file():
        return _load_from_file(path)
    else:
        raise FileNotFoundError(f"Design config not found: {path}")


def _load_from_directory(dir_path: Path) -> DesignState:
    """Load from directory with separate YAML files."""
    
    # Load common.yaml (required)
    common_file = dir_path / "common.yaml"
    if not common_file.exists():
        raise ValueError(f"common.yaml not found in {dir_path}")
    
    raw = _load_yaml(common_file)
    cfg = _build_design_config(raw)
    
    # Load tool-specific configs (optional)
    tool_configs = {
        "synthesis.yaml": "_merge_synthesis",
        "primetime.yaml": "_merge_primetime",
        "icc2.yaml": "_merge_icc2",
        "calibre.yaml": "_merge_calibre",
        "innovus.yaml": "_merge_innovus",
        "tempus.yaml": "_merge_tempus",
        "pegasus.yaml": "_merge_pegasus",
    }
    
    for filename, merge_func in tool_configs.items():
        file_path = dir_path / filename
        if file_path.exists():
            tool_raw = _load_yaml(file_path)
            getattr(cfg, merge_func)(tool_raw)
    
    state = DesignState(config=cfg)
    return state


def _load_from_file(yaml_path: Path) -> DesignState:
    """Load from single YAML file (backward compatible)."""
    
    raw = _load_yaml(yaml_path)
    cfg = _build_design_config(raw)
    
    # Merge tool-specific sections if present
    if "synthesis" in raw:
        cfg._merge_synthesis(raw)
    if "primetime" in raw or "pt" in raw:
        cfg._merge_primetime(raw)
    if "icc2" in raw:
        cfg._merge_icc2(raw)
    if "calibre" in raw:
        cfg._merge_calibre(raw)
    if "innovus" in raw:
        cfg._merge_innovus(raw)
    if "tempus" in raw:
        cfg._merge_tempus(raw)
    if "pegasus" in raw:
        cfg._merge_pegasus(raw)
    
    state = DesignState(config=cfg)
    return state


def _load_yaml(path: Path) -> dict:
    """Load YAML file and return dict."""
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _build_design_config(raw: dict) -> 'DesignConfig':
    """Build DesignConfig from raw YAML dict."""
    
    cfg = DesignConfig()
    
    # ---- Basic info ----
    cfg.design_name = raw.get("design_name", "top")
    cfg.top_module = raw.get("top_module", "top")
    cfg.clock_period_ns = float(raw.get("clock_period_ns", 10.0))
    cfg.clock_name = raw.get("clock_name", "clk")
    cfg.scenario = raw.get("scenario", "")
    
    # ---- Die size ----
    die = raw.get("die", {})
    cfg.die_width_um = float(die.get("width_um", 2900.0))
    cfg.die_height_um = float(die.get("height_um", 1900.0))
    cfg.core_offset_um = die.get("core_offset_um", [180, 180, 180, 180])
    cfg.target_utilization = float(die.get("target_utilization", 0.7))
    
    # ---- RTL sources ----
    rtl = raw.get("rtl", {})
    cfg.rtl_dir = rtl.get("dir", "")
    cfg.rtl_filelist = rtl.get("filelist", "")
    cfg.rtl_files = rtl.get("files", [])
    
    # ---- SDC ----
    cfg.sdc_file = raw.get("sdc_file", "")
    
    # ---- Libraries ----
    libs = raw.get("libraries", {})
    cfg.libraries = LibraryConfig(
        std_cell_libs=libs.get("std_cell", []),
        macro_libs=libs.get("macro", []),
        io_libs=libs.get("io", []),
        ndm_libs=libs.get("ndm", []),
        dont_use_cells=libs.get("dont_use_cells", []),
        vt_libs=libs.get("vt_libs", {}),
        main_lib_name=libs.get("main_lib_name", ""),
        eco_lib=libs.get("eco_lib", ""),
        driver_cell=libs.get("driver_cell", ""),
        delay_cell=libs.get("delay_cell", ""),
        antenna_cell=libs.get("antenna_cell", ""),
        tap_cell=libs.get("tap_cell", ""),
        endcap_cell=libs.get("endcap_cell", ""),
        decap_cells=libs.get("decap_cells", []),
        filler_cells=libs.get("filler_cells", []),
        vt_percentage_constraint=libs.get("vt_percentage", {}),
        boundary_cells=libs.get("boundary_cells", {}),
    )
    
    # ---- PDK ----
    pdk = raw.get("pdk", {})
    cfg.pdk = PDKConfig(
        name=pdk.get("name", "tsmc28hpcp"),
        tech_file=pdk.get("tech_file", ""),
        metal_stack=pdk.get("metal_stack", ["M1","M2","M3","M4","M5","M6","M7","M8","M9","AP"]),
        min_routing_layer=pdk.get("min_routing_layer", "M2"),
        max_routing_layer=pdk.get("max_routing_layer", "M9"),
        gds_map_file=pdk.get("gds_map_file", ""),
        lef_files=pdk.get("lef_files", []),
        antenna_rule_file=pdk.get("antenna_rule_file", ""),
        icv_drc_runset=pdk.get("icv_drc_runset", ""),
        icv_fill_runset=pdk.get("icv_fill_runset", ""),
    )
    
    # ---- EDA Environment ----
    eda = raw.get("eda", {})
    cfg.eda = EDAEnvironment(
        synopsys_script=eda.get("synopsys", ""),
        primetime_script=eda.get("primetime", ""),
        mentor_script=eda.get("mentor", ""),
        cadence_script=eda.get("cadence", ""),
    )
    
    # ---- Clocks ----
    cfg.clocks = []
    for clk_raw in raw.get("clocks", []):
        cfg.clocks.append(ClockDefinition(
            name=clk_raw.get("name", ""),
            period_ns=float(clk_raw.get("period_ns", 10.0)),
            setup_uncertainty_ns=float(clk_raw.get("setup_uncertainty_ns", 0.1)),
            hold_uncertainty_ns=float(clk_raw.get("hold_uncertainty_ns", 0.05)),
            transition_ns=float(clk_raw.get("transition_ns", 0.1)),
            clock_type=clk_raw.get("clock_type", "CTS"),
            pin_or_port=clk_raw.get("pin_or_port", ""),
            top_metal=clk_raw.get("top_metal", "M7"),
            mesh_region=clk_raw.get("mesh_region", []),
            mesh_trunk_multiple=int(clk_raw.get("mesh_trunk_multiple", 8)),
            mesh_trunk_spacing=clk_raw.get("mesh_trunk_spacing", [40.0, 40.0]),
        ))
    
    # ---- Timing derate ----
    derate = raw.get("timing_derate", {})
    cfg.timing_derate = TimingDerateConfig(
        late_factor=float(derate.get("late", 1.0)),
        early_factor=float(derate.get("early", 1.0)),
        late_clock_factor=derate.get("late_clock", None),
        early_clock_factor=derate.get("early_clock", None),
    )
    
    # Initialize tool-specific configs with defaults
    cfg.synthesis = SynthesisConfig()
    cfg.pt = PTConfig()
    cfg.cts = CTSConfig()
    cfg.placement = PlacementConfig()
    cfg.routing = RoutingConfig()
    
    # Tool-specific configs will be merged later
    cfg.innovus = {}
    cfg.tempus = {}
    cfg.icc2 = {}
    cfg.calibre = {}
    cfg.pegasus = {}
    
    return cfg


# Add merge methods to DesignConfig
def _merge_synthesis(self, raw: dict):
    """Merge synthesis config."""
    syn = raw.get("synthesis", {})
    self.synthesis = _parse_synthesis_config(syn)


def _merge_primetime(self, raw: dict):
    """Merge PrimeTime config."""
    pt = raw.get("primetime", raw.get("pt", {}))
    self.pt = _parse_pt_config(pt)


def _merge_icc2(self, raw: dict):
    """Merge ICC2 config."""
    self.icc2 = raw.get("icc2", {})


def _merge_calibre(self, raw: dict):
    """Merge Calibre config."""
    self.calibre = raw.get("calibre", {})


def _merge_innovus(self, raw: dict):
    """Merge Innovus config."""
    self.innovus = raw.get("innovus", {})


def _merge_tempus(self, raw: dict):
    """Merge Tempus config."""
    self.tempus = raw.get("tempus", {})


def _merge_pegasus(self, raw: dict):
    """Merge Pegasus config."""
    self.pegasus = raw.get("pegasus", {})


# Attach merge methods to DesignConfig
DesignConfig._merge_synthesis = _merge_synthesis
DesignConfig._merge_primetime = _merge_primetime
DesignConfig._merge_icc2 = _merge_icc2
DesignConfig._merge_calibre = _merge_calibre
DesignConfig._merge_innovus = _merge_innovus
DesignConfig._merge_tempus = _merge_tempus
DesignConfig._merge_pegasus = _merge_pegasus


def _parse_synthesis_config(syn: dict) -> SynthesisConfig:
    """Parse synthesis section with all industrial-grade options."""
    sc = SynthesisConfig()
    
    # Basic
    sc.compile_ultra = syn.get("compile_ultra", True)
    sc.no_autoungroup = syn.get("no_autoungroup", True)
    sc.timing_high_effort = syn.get("timing_high_effort", True)
    sc.incremental_compile = syn.get("incremental_compile", False)
    sc.max_incremental_loops = int(syn.get("max_incremental_loops", 0))
    sc.tns_effort = syn.get("tns_effort", "high")
    sc.high_resistance = syn.get("high_resistance", False)
    sc.num_cores = int(syn.get("num_cores", 64))
    
    # Physical awareness (DC-T)
    physical = syn.get("physical", {})
    sc.topographical_mode = physical.get("enabled", False)
    sc.tlu_plus_file = physical.get("tlu_plus_file", "")
    sc.tech2itf_map = physical.get("tech2itf_map", "")
    sc.floorplan_file = physical.get("floorplan_file", "")
    sc.def_file = physical.get("def_file", "")
    sc.physical_constraints_file = physical.get("constraints_file", "")
    sc.dc_obs_file = physical.get("obs_file", "")
    sc.floorplan_exploration = physical.get("floorplan_exploration", False)
    
    # MCMM
    mcmm = syn.get("mcmm", {})
    sc.mcmm_enabled = mcmm.get("enabled", False)
    sc.mcmm_default_scenario = mcmm.get("default_scenario", "")
    sc.mcmm_scenarios = []
    for s in mcmm.get("scenarios", []):
        sc.mcmm_scenarios.append(MCMMScenario(
            name=s.get("name", ""),
            corner=s.get("corner", "tt"),
            analysis_type=s.get("analysis_type", "bc_wc"),
            setup=s.get("setup", True),
            hold=s.get("hold", True),
            leakage_power=s.get("leakage_power", False),
            dynamic_power=s.get("dynamic_power", False),
            sdc_file=s.get("sdc_file", ""),
            clock_file=s.get("clock_file", ""),
            tlu_plus_file=s.get("tlu_plus_file", ""),
            operating_condition=s.get("operating_condition", ""),
        ))
    
    # Power
    power = syn.get("power", {})
    sc.power_optimization = power.get("enabled", True)
    sc.power_effort = power.get("effort", "high")
    sc.leakage_optimization = power.get("leakage", True)
    sc.dynamic_optimization = power.get("dynamic", True)
    sc.power_prediction = power.get("prediction", False)
    
    # Clock gating
    cg = syn.get("clock_gating", {})
    sc.clock_gating = cg.get("enabled", True)
    sc.self_gating = cg.get("self_gating", False)
    sc.clock_gating_style = cg.get("style", "integrated")
    sc.clock_gating_positive_edge = cg.get("positive_edge", True)
    sc.clock_gating_control_point = cg.get("control_point", "before")
    sc.physically_aware_cg = cg.get("physically_aware", True)
    sc.flatten_cg = cg.get("flatten", True)
    
    # Timing
    timing = syn.get("timing", {})
    sc.critical_range_ns = float(timing.get("critical_range_ns", 0.0))
    sc.max_transition_dc = float(timing.get("max_transition", 0.5))
    sc.max_fanout_dc = int(timing.get("max_fanout", 20))
    sc.max_capacitance_dc = float(timing.get("max_capacitance", 0.5))
    sc.awe_effort = int(timing.get("awe_effort", 10))
    sc.arnoldi_effort = int(timing.get("arnoldi_effort", 10))
    sc.enable_register_merging = timing.get("register_merging", False)
    
    # Congestion
    sc.congestion_optimization = syn.get("congestion_optimization", False)
    
    # DFT / Scan
    dft = syn.get("dft", {})
    sc.scan_insertion = dft.get("scan_insertion", False)
    sc.scan_style = dft.get("scan_style", "multiplexed")
    sc.scan_coverage = dft.get("scan_coverage", False)
    
    # SVF / ECO
    sc.svf_enabled = syn.get("svf_enabled", True)
    
    # VT control
    vt = syn.get("vt_control", {})
    sc.vt_dont_use_patterns = vt.get("dont_use", {})
    sc.vt_release_patterns = vt.get("release", {})
    
    # Hierarchy
    hier = syn.get("hierarchy", {})
    sc.keep_hierarchies = hier.get("keep", [])
    sc.flatten_all = hier.get("flatten_all", False)
    sc.flatten_start_level = int(hier.get("flatten_start_level", 2))
    sc.size_only_patterns = hier.get("size_only_patterns", [])
    
    # NDR / Constraints files
    sc.ndr_constraints_file = syn.get("ndr_constraints_file", "")
    sc.compile_constraints_file = syn.get("compile_constraints_file", "")
    sc.place_constraints_file = syn.get("place_constraints_file", "")
    
    # Auto-weight
    sc.auto_weight_adjustment = syn.get("auto_weight_adjustment", False)
    
    # Port buffers
    sc.insert_port_buffers = syn.get("insert_port_buffers", [])
    
    return sc


def _parse_pt_config(pt: dict) -> PTConfig:
    """Parse PrimeTime config."""
    cfg = PTConfig()
    
    cfg.num_cores = int(pt.get("num_cores", 8))
    cfg.significant_digits = int(pt.get("significant_digits", 3))
    
    # Analysis
    analysis = pt.get("analysis", {})
    cfg.enable_cppr = analysis.get("enable_cppr", True)
    cfg.enable_si_analysis = analysis.get("enable_si", True)
    cfg.cppr_threshold_ps = float(analysis.get("cppr_credit_threshold", 0.01))
    cfg.timing_derate_late = float(analysis.get("timing_derate_late", 1.0))
    cfg.timing_derate_early = float(analysis.get("timing_derate_early", 1.0))
    
    # Reporting
    reporting = pt.get("reporting", {})
    cfg.max_paths = int(reporting.get("max_paths", 100))
    cfg.nworst = int(reporting.get("nworst", 10))
    cfg.slack_lesser_than = float(reporting.get("slack_lesser_than", 0.0))
    
    return cfg
