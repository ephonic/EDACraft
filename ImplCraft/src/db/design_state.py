"""
Design State — unified data model flowing through the backend pipeline.

Each tool stage reads from and writes to this object. The state is serializable
to YAML/JSON so it can be persisted between stages and inspected by analyzers.
"""
from __future__ import annotations

import json
import copy
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from pathlib import Path
from typing import Any


class FlowStage(Enum):
    INIT = auto()
    SYNTHESIS = auto()
    DFT_INSERTION = auto()
    FLOORPLAN = auto()
    PLACEMENT = auto()
    CTS = auto()
    ROUTING = auto()
    ROUTE_OPT = auto()
    PARASITIC_EXTRACTION = auto()
    STA_SIGNOFF = auto()
    PV_DRC = auto()
    PV_LVS = auto()
    TAPEOUT = auto()


class StageStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TimingMetrics:
    wns: float | None = None
    tns: float | None = None
    num_violating_paths: int | None = None
    num_endpoints: int | None = None
    max_transition_violations: int | None = None
    max_capacitance_violations: int | None = None
    max_fanout_violations: int | None = None
    clock_skew: float | None = None


@dataclass
class AreaMetrics:
    total_area: float | None = None
    cell_area: float | None = None
    utilization: float | None = None
    num_std_cells: int | None = None
    num_macros: int | None = None
    num_io_cells: int | None = None


@dataclass
class PowerMetrics:
    total_power_mw: float | None = None
    dynamic_power_mw: float | None = None
    leakage_power_mw: float | None = None
    short_circuit_power_mw: float | None = None


@dataclass
class RouteMetrics:
    drc_errors: int | None = None
    total_wirelength: float | None = None
    num_nets: int | None = None
    num_vias: int | None = None
    congestion_h: float | None = None
    congestion_v: float | None = None


@dataclass
class DRCMetrics:
    total_errors: int | None = None
    errors_by_type: dict[str, int] = field(default_factory=dict)
    is_clean: bool = False


@dataclass
class LVSMetrics:
    is_clean: bool = False
    num_mismatches: int | None = None
    num_errors: int | None = None


@dataclass
class StageResult:
    stage: FlowStage
    status: StageStatus = StageStatus.PENDING
    work_dir: str = ""
    log_file: str = ""
    timing: TimingMetrics = field(default_factory=TimingMetrics)
    area: AreaMetrics = field(default_factory=AreaMetrics)
    power: PowerMetrics = field(default_factory=PowerMetrics)
    route: RouteMetrics = field(default_factory=RouteMetrics)
    drc: DRCMetrics = field(default_factory=DRCMetrics)
    lvs: LVSMetrics = field(default_factory=LVSMetrics)
    output_files: dict[str, str] = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0


@dataclass
class PDKConfig:
    name: str = "tsmc28hpcp"
    tech_file: str = ""
    metal_stack: list[str] = field(default_factory=lambda: [
        "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "AP"
    ])
    min_routing_layer: str = "M2"
    max_routing_layer: str = "M9"
    min_layer_mode: str = "allow_pin_connection"
    max_layer_mode: str = "hard"
    gds_map_file: str = ""
    lef_files: list[str] = field(default_factory=list)
    antenna_rule_file: str = ""
    icv_drc_runset: str = ""
    icv_fill_runset: str = ""
    calibre_drc_runset: str = ""
    calibre_lvs_runset: str = ""
    std_cell_gds: str = ""               # Standard-cell GDS library for Calibre DRC/LVS
    std_cell_spice: str = ""             # Standard-cell SPICE/CDL library for Calibre LVS
    power_nets: list[str] = field(default_factory=lambda: ["VDD"])
    ground_nets: list[str] = field(default_factory=lambda: ["VSS"])
    tlu_plus_max: str = ""              # Worst-case (max) TLU+ parasitic file
    tlu_plus_min: str = ""              # Best-case (min) TLU+ parasitic file
    tech2itf_map: str = ""              # Technology-to-ITF layer mapping file
    setup_voltage_v: float = 0.9          # Voltage for setup corner
    hold_voltage_v: float = 0.88          # Voltage for hold corner
    temperature_c: float = 25.0           # Temperature for both corners
    innovus_site_name: str = "core"       # Innovus floorplan site name (must match tech LEF)
    pegasus_drc_runset: str = ""          # Pegasus DRC rule deck
    pegasus_lvs_runset: str = ""          # Pegasus LVS rule deck
    nxtgrd_max: str = ""                 # StarRC nxtgrd file (max corner)
    nxtgrd_min: str = ""                 # StarRC nxtgrd file (min corner)
    starrc_layer_map: str = ""           # StarRC layer map file
    cell_name_suffix_strip: str = ""     # VT suffix to strip from netlist (e.g. "UHVT")
    liberty_suffix_strip: str = ""       # VT suffix to strip from Liberty (e.g. "HVT")


@dataclass
class EDAEnvironment:
    """EDA tool environment paths — no hardcoded directories."""
    synopsys_script: str = ""        # DC, ICC2 environment setup
    primetime_script: str = ""       # PrimeTime environment setup
    mentor_script: str = ""          # Calibre/Mentor environment setup
    cadence_script: str = ""         # Innovus/Tempus/Pegasus environment setup

    def get_script(self, tool_family: str) -> str:
        """Resolve environment script for a tool family."""
        mapping = {
            "synopsys": self.synopsys_script,
            "dc": self.synopsys_script,
            "icc2": self.synopsys_script,
            "pt": self.primetime_script,
            "primetime": self.primetime_script,
            "mentor": self.mentor_script,
            "calibre": self.mentor_script,
            "mg": self.mentor_script,
        
            "cadence": self.cadence_script,
            "innovus": self.cadence_script,
            "tempus": self.cadence_script,
            "pegasus": self.cadence_script,}
        return mapping.get(tool_family.lower(), "")



@dataclass
class ClockDefinition:
    """Industrial clock definition with full timing parameters."""
    name: str = ""
    period_ns: float = 10.0
    setup_uncertainty_ns: float = 0.1
    hold_uncertainty_ns: float = 0.05
    transition_ns: float = 0.1
    clock_type: str = "CTS"
    top_metal: str = "M7"
    mesh_region: list[float] = field(default_factory=list)
    mesh_trunk_multiple: int = 8
    mesh_trunk_spacing: list[float] = field(default_factory=lambda: [40.0, 40.0])
    pin_or_port: str = ""


@dataclass
class LibraryConfig:
    std_cell_libs: list[str] = field(default_factory=list)
    macro_libs: list[str] = field(default_factory=list)
    io_libs: list[str] = field(default_factory=list)
    ndm_libs: list[str] = field(default_factory=list)
    liberty_libs: list[str] = field(default_factory=list)  # .lib files for Innovus
    dont_use_cells: list[str] = field(default_factory=list)
    vt_libs: dict[str, list[str]] = field(default_factory=dict)
    main_lib_name: str = ""
    eco_lib: str = ""
    vt_percentage_constraint: dict[str, float] = field(default_factory=dict)
    driver_cell: str = ""
    delay_cell: str = ""
    antenna_cell: str = ""
    boundary_cells: dict[str, str] = field(default_factory=dict)
    tap_cell: str = ""
    endcap_cell: str = ""
    decap_cells: list[str] = field(default_factory=list)
    filler_cells: list[str] = field(default_factory=list)


@dataclass
class TimingDerateConfig:
    """Timing derate settings for OCV."""
    late_factor: float = 1.0
    early_factor: float = 1.0
    late_clock_factor: float | None = None
    early_clock_factor: float | None = None


@dataclass
class CTSConfig:
    """Clock Tree Synthesis configuration."""
    target_skew_ns: float = 0.1
    target_early_delay_ns: float = 0.0
    max_transition_ns: float | None = None
    max_fanout: int | None = None
    leaf_max_transition_ns: float | None = None
    use_leaf_max_transition_on_macros: bool = False
    max_rc_delay_ns: float | None = None
    inter_clock_balance: bool = False
    ocv_clustering: bool = True
    ocv_path_sharing: bool = True
    logic_level_balance: bool = False
    routing_layers: list[str] = field(default_factory=list)
    stop_pin_on_macro: bool = True
    skip_redundant_final_opto: bool = False


@dataclass
class PlacementConfig:
    """Placement configuration."""
    target_utilization: float = 0.7
    max_cell_density_threshold: float = -1.0
    congestion_effort: str = "medium"
    target_routing_density: float = 0.6
    max_net_length_um: float = 250.0
    vt_min_filler_size: int = 2
    consider_vt_spacing: bool = True
    consider_continuous_od_spacing: bool = True
    consider_pode_spacing: bool = False
    insert_endcap: bool = True
    insert_welltap: bool = True
    insert_predecap: bool = True
    insert_postdecap: bool = True
    insert_spare: bool = False
    insert_eco: bool = True
    tap_distance_um: float = 40.0
    power_net: str = "VDD"
    ground_net: str = "VSS"
    macro_keepout_margin: list[float] = field(default_factory=lambda: [5.0, 5.0, 5.0, 5.0])
    auto_macro_placement: bool = True


@dataclass
class RoutingConfig:
    """Routing configuration."""
    timing_driven: bool = True
    timing_driven_effort: str = "high"
    crosstalk_driven: bool = True
    track_timing_driven: bool = True
    track_crosstalk_driven: bool = True
    antenna_fixing: bool = True
    insert_diodes_during_routing: bool = True
    optimize_wire_via_effort: str = "high"
    optimize_tie_off_effort: str = "high"
    repair_shorts_over_macros_effort: str = "high"
    generate_off_grid_pin_tracks: bool = True
    si_delta_delay: bool = True
    si_route_xtalk_prevention: bool = True
    si_static_noise: bool = True
    si_timing_window: bool = True
    si_analysis_effort: str = "medium"
    redundant_via_insertion: str = "medium"
    search_repair_loop: int = 40
    eco_route_search_repair_loops: int = 20
    xtalk_reduction_loops: int = 5


@dataclass
class MCMMScenario:
    """Multi-Corner Multi-Mode scenario definition."""
    name: str = ""
    corner: str = "tt"                    # Process corner name
    analysis_type: str = "bc_wc"          # bc_wc, on_chip_variation
    setup: bool = True
    hold: bool = True
    leakage_power: bool = False
    dynamic_power: bool = False
    sdc_file: str = ""
    clock_file: str = ""
    tlu_plus_file: str = ""               # Max or min TLU+ depending on corner
    operating_condition: str = ""


@dataclass
class SynthesisConfig:
    """Synthesis-specific configuration with industrial-grade options."""

    # ---- Basic compile options ----
    compile_ultra: bool = True
    no_autoungroup: bool = True
    timing_high_effort: bool = True
    incremental_compile: bool = False
    max_incremental_loops: int = 0
    tns_effort: str = "high"
    high_resistance: bool = False
    num_cores: int = 64

    # ---- Physical awareness (DC-T) ----
    topographical_mode: bool = False
    tlu_plus_file: str = ""               # TLU+ parasitic file
    tech2itf_map: str = ""                # Technology to ITF mapping
    floorplan_file: str = ""              # Floorplan input file
    def_file: str = ""                    # DEF floorplan input
    physical_constraints_file: str = ""   # Additional physical constraints TCL
    dc_obs_file: str = ""                 # Global observation (obs) file
    floorplan_exploration: bool = False   # ICC DP floorplan exploration

    # ---- Multi-Corner Multi-Mode ----
    mcmm_enabled: bool = False
    mcmm_scenarios: list[MCMMScenario] = field(default_factory=list)
    mcmm_default_scenario: str = ""

    # ---- Power optimization ----
    power_optimization: bool = True
    power_effort: str = "high"
    leakage_optimization: bool = True
    dynamic_optimization: bool = True
    power_prediction: bool = False        # Requires DC-T
    clock_gating: bool = True
    self_gating: bool = False
    clock_gating_style: str = "integrated"   # integrated, discrete
    clock_gating_positive_edge: bool = True
    clock_gating_control_point: str = "before"  # before, after
    physically_aware_cg: bool = True
    flatten_cg: bool = True

    # ---- Timing settings ----
    critical_range_ns: float = 0.0
    max_transition_dc: float = 0.5
    max_fanout_dc: int = 20
    max_capacitance_dc: float = 0.5
    awe_effort: int = 10
    arnoldi_effort: int = 10
    enable_register_merging: bool = False

    # ---- Congestion optimization ----
    congestion_optimization: bool = False

    # ---- DFT / Scan ----
    scan_insertion: bool = False
    scan_style: str = "multiplexed"       # multiplexed, clocked
    scan_coverage: bool = False           # Retain DFT coverage cells

    # ---- SVF / ECO support ----
    svf_enabled: bool = True

    # ---- VT control ----
    vt_dont_use_patterns: dict[str, list[str]] = field(default_factory=dict)
    vt_release_patterns: dict[str, list[str]] = field(default_factory=dict)

    # ---- Hierarchy management ----
    keep_hierarchies: list[str] = field(default_factory=list)
    flatten_all: bool = False
    flatten_start_level: int = 2
    size_only_patterns: list[str] = field(default_factory=list)  # Patterns for set_size_only

    # ---- Non-Default Routing Rules ----
    ndr_constraints_file: str = ""
    compile_constraints_file: str = ""
    place_constraints_file: str = ""

    # ---- Auto-weight adjustment ----
    auto_weight_adjustment: bool = False

    # ---- Port buffers ----
    insert_port_buffers: list[str] = field(default_factory=list)


@dataclass
class PTConfig:
    """PrimeTime sign-off STA configuration."""
    # Basic options
    num_cores: int = 8
    significant_digits: int = 3
    
    # Netlist and parasitics
    netlist_file: str = ""           # Gate-level netlist
    sdc_file: str = ""               # SDC constraints
    spef_file: str = ""              # SPEF parasitics
    spef_format: str = "auto"        # auto, SPEF, DSPF
    
    # Libraries
    search_path: list[str] = field(default_factory=list)
    target_library: list[str] = field(default_factory=list)
    link_library: list[str] = field(default_factory=list)
    symbol_library: list[str] = field(default_factory=list)
    
    # Multi-VT and dont_use
    vt_groups: dict[str, str] = field(default_factory=dict)  # lib_pattern -> vt_group_name
    dont_use_patterns: list[str] = field(default_factory=list)
    custom_dont_use: list[str] = field(default_factory=list)
    custom_remove_dontuse: list[str] = field(default_factory=list)
    
    # Timing settings
    timing_derate_late: float = 1.0
    timing_derate_early: float = 1.0
    enable_cppr: bool = True
    cppr_threshold_ps: float = 1.0
    enable_si_analysis: bool = True
    save_pin_arrival_and_slack: bool = True
    delay_calc_mode: str = "full_design"
    
    # Power analysis
    enable_power_analysis: bool = True
    vcd_file: str = ""
    vcd_strip_path: str = ""
    vcd_time_range: list[float] = field(default_factory=list)
    saif_file: str = ""
    saif_strip_path: str = ""
    power_analysis_mode: str = "averaged"  # averaged, time_based
    power_mode: str = "averaged"
    
    # Path Group Analysis
    report_transition: bool = True
    report_net: bool = True
    report_capacitance: bool = True
    max_paths: int = 20
    nworst: int = 1
    slack_lesser_than: float = 0.0
    
    # ECO fixing
    enable_eco: bool = False
    eco_physical_mode: str = "placement"  # placement, none
    lef_library: str = ""
    final_def: str = ""
    fix_setup: bool = False
    fix_hold: bool = False
    fix_drc: bool = False
    fix_power: bool = False
    fix_leakage: bool = False
    setup_opt_margin: float = 0.0
    hold_opt_margin: float = 0.0
    setup_opt_slack: float = 0.0
    hold_opt_slack: float = 0.0
    fix_setup_groups: list[str] = field(default_factory=list)
    fix_hold_groups: list[str] = field(default_factory=list)
    fix_drc_buffer_list: list[str] = field(default_factory=list)
    fix_hold_buffer_list: list[str] = field(default_factory=list)
    eco_power_priority: list[str] = field(default_factory=list)
    power_opt_margin: float = 0.0
    eco_scripts_output: str = ""
    
    # Model extraction
    enable_model_extraction: bool = False
    input_transition: float = 0.3
    
    # Session and reports
    save_session: bool = True
    session_name: str = ""
    report_path: str = "./PT/report"
    output_path: str = "./PT/out"
    
    # Analysis coverage
    enable_analysis_coverage: bool = True


@dataclass
class DesignConfig:
    """Top-level design configuration."""
    design_name: str = "top"
    top_module: str = "top"
    clock_period_ns: float = 10.0
    clock_name: str = "clk"
    die_width_um: float = 2900.0
    die_height_um: float = 1900.0
    core_offset_um: list[float] = field(default_factory=lambda: [180, 180, 180, 180])
    scenario: str = "func.tt0p9v.wc.cmax_25c.setup"
    pdk: PDKConfig = field(default_factory=PDKConfig)
    libraries: LibraryConfig = field(default_factory=LibraryConfig)
    rtl_files: list[str] = field(default_factory=list)  # Explicit file list (backward compat)
    rtl_dir: str = ""                   # RTL directory path
    rtl_filelist: str = ""              # filelist.f path (industry standard)
    sdc_file: str = ""
    clocks: list[ClockDefinition] = field(default_factory=list)
    timing_derate: TimingDerateConfig = field(default_factory=TimingDerateConfig)
    cts: CTSConfig = field(default_factory=CTSConfig)
    placement: PlacementConfig = field(default_factory=PlacementConfig)
    routing: RoutingConfig = field(default_factory=RoutingConfig)
    synthesis: SynthesisConfig = field(default_factory=SynthesisConfig)
    pt: PTConfig = field(default_factory=PTConfig)
    eda: EDAEnvironment = field(default_factory=EDAEnvironment)
    target_utilization: float = 0.7

    def __post_init__(self):
        if not self.clocks and self.clock_name:
            self.clocks = [ClockDefinition(
                name=self.clock_name,
                period_ns=self.clock_period_ns,
            )]
        if isinstance(self.placement, PlacementConfig):
            self.placement.target_utilization = self.target_utilization


@dataclass
class DesignState:
    """
    Full design state flowing through the backend pipeline.

    This is the single source of truth. Each tool adapter reads config from here
    and writes results back. Analyzers consume this for cross-stage diagnostics.
    """
    config: DesignConfig = field(default_factory=DesignConfig)
    current_stage: FlowStage = FlowStage.INIT
    stage_results: dict[str, StageResult] = field(default_factory=dict)
    artifacts: dict[str, str] = field(default_factory=dict)
    work_root: str = ""
    history: list[dict[str, Any]] = field(default_factory=list)

    def get_stage_result(self, stage: FlowStage) -> StageResult:
        key = stage.name
        if key not in self.stage_results:
            self.stage_results[key] = StageResult(stage=stage)
        return self.stage_results[key]

    def record_artifact(self, key: str, path: str):
        self.artifacts[key] = str(path)

    def get_artifact(self, key: str) -> str | None:
        return self.artifacts.get(key)

    def snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(asdict(self))

    def save(self, path: str | Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.snapshot(), f, indent=2, default=lambda o: o.name if isinstance(o, (FlowStage, StageStatus)) else str(o))

    @classmethod
    def load(cls, path: str | Path) -> DesignState:
        with open(path) as f:
            data = json.load(f)
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict) -> DesignState:
        """Deserialize from dict, properly handling nested dataclasses."""
        state = cls()

        if "config" in data:
            cfg_data = data["config"]
            # Reconstruct nested dataclasses
            pdk_data = cfg_data.get("pdk", {})
            if isinstance(pdk_data, dict):
                pdk = PDKConfig(**{k: v for k, v in pdk_data.items() if k in PDKConfig.__dataclass_fields__})
            else:
                pdk = pdk_data

            libs_data = cfg_data.get("libraries", {})
            if isinstance(libs_data, dict):
                libraries = LibraryConfig(**{k: v for k, v in libs_data.items() if k in LibraryConfig.__dataclass_fields__})
            else:
                libraries = libs_data

            clocks_data = cfg_data.get("clocks", [])
            clocks = []
            if isinstance(clocks_data, list):
                for cd in clocks_data:
                    if isinstance(cd, dict):
                        clocks.append(ClockDefinition(**{k: v for k, v in cd.items() if k in ClockDefinition.__dataclass_fields__}))
                    else:
                        clocks.append(cd)

            derate_data = cfg_data.get("timing_derate", {})
            if isinstance(derate_data, dict):
                timing_derate = TimingDerateConfig(**{k: v for k, v in derate_data.items() if k in TimingDerateConfig.__dataclass_fields__})
            else:
                timing_derate = derate_data

            cts_data = cfg_data.get("cts", {})
            if isinstance(cts_data, dict):
                cts = CTSConfig(**{k: v for k, v in cts_data.items() if k in CTSConfig.__dataclass_fields__})
            else:
                cts = cts_data

            place_data = cfg_data.get("placement", {})
            if isinstance(place_data, dict):
                placement = PlacementConfig(**{k: v for k, v in place_data.items() if k in PlacementConfig.__dataclass_fields__})
            else:
                placement = place_data

            route_data = cfg_data.get("routing", {})
            if isinstance(route_data, dict):
                routing = RoutingConfig(**{k: v for k, v in route_data.items() if k in RoutingConfig.__dataclass_fields__})
            else:
                routing = route_data

            syn_data = cfg_data.get("synthesis", {})
            if isinstance(syn_data, dict):
                synthesis = SynthesisConfig(**{k: v for k, v in syn_data.items() if k in SynthesisConfig.__dataclass_fields__})
            else:
                synthesis = syn_data

            pt_data = cfg_data.get("pt", {})
            if isinstance(pt_data, dict):
                pt = PTConfig(**{k: v for k, v in pt_data.items() if k in PTConfig.__dataclass_fields__})
            else:
                pt = pt_data

            eda_data = cfg_data.get("eda", {})
            if isinstance(eda_data, dict):
                eda = EDAEnvironment(**{k: v for k, v in eda_data.items() if k in EDAEnvironment.__dataclass_fields__})
            else:
                eda = eda_data

            state.config = DesignConfig(
                design_name=cfg_data.get("design_name", "top"),
                top_module=cfg_data.get("top_module", "top"),
                clock_period_ns=float(cfg_data.get("clock_period_ns", 10.0)),
                clock_name=cfg_data.get("clock_name", "clk"),
                die_width_um=float(cfg_data.get("die_width_um", 2900.0)),
                die_height_um=float(cfg_data.get("die_height_um", 1900.0)),
                core_offset_um=cfg_data.get("core_offset_um", [180, 180, 180, 180]),
                scenario=cfg_data.get("scenario", "func.tt0p9v.wc.cmax_25c.setup"),
                pdk=pdk,
                libraries=libraries,
                rtl_files=cfg_data.get("rtl_files", []),
                rtl_dir=cfg_data.get("rtl_dir", ""),
                rtl_filelist=cfg_data.get("rtl_filelist", ""),
                sdc_file=cfg_data.get("sdc_file", ""),
                clocks=clocks,
                timing_derate=timing_derate,
                cts=cts,
                placement=placement,
                routing=routing,
                synthesis=synthesis,
                pt=pt,
                eda=eda,
                target_utilization=float(cfg_data.get("target_utilization", 0.7)),
            )

        stage_val = data.get("current_stage", "INIT")
        if isinstance(stage_val, str):
            state.current_stage = FlowStage[stage_val] if stage_val in FlowStage.__members__ else FlowStage.INIT
        elif isinstance(stage_val, int):
            try:
                state.current_stage = FlowStage(stage_val)
            except ValueError:
                state.current_stage = FlowStage.INIT
        else:
            state.current_stage = FlowStage.INIT

        state.artifacts = data.get("artifacts", {})
        state.work_root = data.get("work_root", "")
        state.history = data.get("history", [])

        return state
