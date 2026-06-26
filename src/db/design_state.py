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
    FLOORPLAN = auto()
    PLACEMENT = auto()
    CTS = auto()
    ROUTING = auto()
    ROUTE_OPT = auto()
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
class SynthesisConfig:
    """Synthesis-specific configuration."""
    compile_ultra: bool = True
    no_autoungroup: bool = True
    timing_high_effort: bool = True
    incremental_compile: bool = False
    max_incremental_loops: int = 0
    tns_effort: str = "high"
    high_resistance: bool = False
    power_optimization: bool = True
    power_effort: str = "high"
    physically_aware_cg: bool = True
    flatten_cg: bool = True
    critical_range_ns: float = 0.0
    max_transition_dc: float = 0.5
    max_fanout_dc: int = 20
    awe_effort: int = 10
    arnoldi_effort: int = 10
    enable_register_merging: bool = False
    num_cores: int = 64


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
    rtl_files: list[str] = field(default_factory=list)
    sdc_file: str = ""
    clocks: list[ClockDefinition] = field(default_factory=list)
    timing_derate: TimingDerateConfig = field(default_factory=TimingDerateConfig)
    cts: CTSConfig = field(default_factory=CTSConfig)
    placement: PlacementConfig = field(default_factory=PlacementConfig)
    routing: RoutingConfig = field(default_factory=RoutingConfig)
    synthesis: SynthesisConfig = field(default_factory=SynthesisConfig)
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
                sdc_file=cfg_data.get("sdc_file", ""),
                clocks=clocks,
                timing_derate=timing_derate,
                cts=cts,
                placement=placement,
                routing=routing,
                synthesis=synthesis,
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
