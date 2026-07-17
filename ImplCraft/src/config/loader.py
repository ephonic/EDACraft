"""
Configuration Loader — reads/writes YAML project config with industrial features.

YAML config format (full example):
```yaml
design:
  name: FullSystem
  top_module: FullSystem
  clock_period_ns: 10.0
  clock_name: clk
  die_width_um: 2900
  die_height_um: 1900
  core_offset_um: [180, 180, 180, 180]
  target_utilization: 0.7
  scenario: func.tt0p9v.wc.cmax_25c.setup

pdk:
  name: tsmc28hpcp
  tech_file: /path/to/tech.tf
  metal_stack: [M1, M2, M3, M4, M5, M6, M7, M8, M9, AP]
  min_routing_layer: M2
  max_routing_layer: M9
  min_layer_mode: allow_pin_connection
  max_layer_mode: hard
  gds_map_file: /path/to/gds.map
  antenna_rule_file: /path/to/antenna.rule
  icv_drc_runset: /path/to/drc.runset
  icv_fill_runset: /path/to/fill.runset
  tlu_plus_max: /path/to/max.tluplus
  tlu_plus_min: /path/to/min.tluplus
  tech2itf_map: /path/to/tech2itf.map

libraries:
  std_cell_libs:
    - /path/to/stdcell.db
  ndm_libs:
    - /path/to/stdcell.ndm
  dont_use_cells: []
  vt_libs:
    RVT: [/path/to/rvt.db]
    LVT: [/path/to/lvt.db]
    ULVT: [/path/to/ulvt.db]
  main_lib_name: stdcell
  eco_lib: LVT_ECO
  vt_percentage_constraint: {LVT: 5.0}
  driver_cell: BUFFD2BWP30P140
  delay_cell: DEL020D1BWP30P140
  antenna_cell: ANTENNA_BWP30P140
  tap_cell: TAPCELL_BWP30P140
  endcap_cell: ENDCAP_BWP30P140
  decap_cells: [DCAP4_BWP30P140, DCAP8_BWP30P140, DCAP16_BWP30P140]
  filler_cells: [FILL1_BWP30P140, FILL2_BWP30P140, FILL4_BWP30P140]
  boundary_cells:
    left: BOUNDARY_LEFTBWP30P140
    right: BOUNDARY_RIGHTBWP30P140

clocks:
  - name: clk
    period_ns: 10.0
    setup_uncertainty_ns: 0.5
    hold_uncertainty_ns: 0.15
    transition_ns: 0.1
    clock_type: CTS
    top_metal: M7
    pin_or_port: clk

timing_derate:
  late_factor: 1.02
  early_factor: 0.98

cts:
  target_skew_ns: 0.1
  target_early_delay_ns: 0.0
  inter_clock_balance: false
  ocv_clustering: true
  ocv_path_sharing: true

placement:
  target_utilization: 0.7
  congestion_effort: medium
  max_net_length_um: 250.0
  insert_endcap: true
  insert_welltap: true
  insert_predecap: true
  insert_postdecap: true
  insert_spare: false
  insert_eco: true
  tap_distance_um: 40.0
  power_net: VDD
  ground_net: VSS

routing:
  timing_driven: true
  timing_driven_effort: high
  crosstalk_driven: true
  antenna_fixing: true
  si_delta_delay: true
  si_static_noise: true
  redundant_via_insertion: medium
  search_repair_loop: 40

synthesis:
  compile_ultra: true
  tns_effort: high
  power_optimization: true
  max_transition_dc: 0.5
  max_fanout_dc: 20
  num_cores: 64

rtl:
  files:
    - /path/to/rtl/top.v
  sdc_file: /path/to/constraints.sdc

flow:
  work_root: ./work
  dry_run: false
```
"""
from __future__ import annotations

import copy

import yaml
from pathlib import Path
from typing import Any

from ..db.design_state import (
    DesignConfig, PDKConfig, LibraryConfig,
    ClockDefinition, TimingDerateConfig, CTSConfig,
    PlacementConfig, RoutingConfig, SynthesisConfig,
    EDAEnvironment,
)


def _parse_clocks(clocks_data: list[dict]) -> list[ClockDefinition]:
    """Parse clock definitions from YAML."""
    clocks = []
    for cd in clocks_data:
        clocks.append(ClockDefinition(
            name=cd.get("name", ""),
            period_ns=float(cd.get("period_ns", 10.0)),
            setup_uncertainty_ns=float(cd.get("setup_uncertainty_ns", 0.1)),
            hold_uncertainty_ns=float(cd.get("hold_uncertainty_ns", 0.05)),
            transition_ns=float(cd.get("transition_ns", 0.1)),
            clock_type=cd.get("clock_type", "CTS"),
            top_metal=cd.get("top_metal", "M7"),
            mesh_region=cd.get("mesh_region", []),
            mesh_trunk_multiple=int(cd.get("mesh_trunk_multiple", 8)),
            mesh_trunk_spacing=cd.get("mesh_trunk_spacing", [40.0, 40.0]),
            pin_or_port=cd.get("pin_or_port", ""),
        ))
    return clocks


def _parse_pdk(pdk_data: dict) -> PDKConfig:
    """Parse PDK config from YAML."""
    return PDKConfig(
        name=pdk_data.get("name", "tsmc28hpcp"),
        tech_file=pdk_data.get("tech_file", ""),
        metal_stack=pdk_data.get("metal_stack", ["M1","M2","M3","M4","M5","M6","M7","M8","M9","AP"]),
        min_routing_layer=pdk_data.get("min_routing_layer", "M2"),
        max_routing_layer=pdk_data.get("max_routing_layer", "M9"),
        min_layer_mode=pdk_data.get("min_layer_mode", "allow_pin_connection"),
        max_layer_mode=pdk_data.get("max_layer_mode", "hard"),
        gds_map_file=pdk_data.get("gds_map_file", ""),
        lef_files=pdk_data.get("lef_files", []),
        antenna_rule_file=pdk_data.get("antenna_rule_file", ""),
        icv_drc_runset=pdk_data.get("icv_drc_runset", ""),
        icv_fill_runset=pdk_data.get("icv_fill_runset", ""),
        calibre_drc_runset=pdk_data.get("calibre_drc_runset", ""),
        calibre_lvs_runset=pdk_data.get("calibre_lvs_runset", ""),
        std_cell_gds=pdk_data.get("std_cell_gds", ""),
        std_cell_spice=pdk_data.get("std_cell_spice", ""),
        power_nets=pdk_data.get("power_nets", ["VDD"]),
        ground_nets=pdk_data.get("ground_nets", ["VSS"]),
        tlu_plus_max=pdk_data.get("tlu_plus_max", ""),
        tlu_plus_min=pdk_data.get("tlu_plus_min", ""),
        tech2itf_map=pdk_data.get("tech2itf_map", ""),
        setup_voltage_v=float(pdk_data.get("setup_voltage_v", 0.9)),
        hold_voltage_v=float(pdk_data.get("hold_voltage_v", 0.88)),
        temperature_c=float(pdk_data.get("temperature_c", 25.0)),
        innovus_site_name=pdk_data.get("innovus_site_name", "core"),
        pegasus_drc_runset=pdk_data.get("pegasus_drc_runset", ""),
        pegasus_lvs_runset=pdk_data.get("pegasus_lvs_runset", ""),
        nxtgrd_max=pdk_data.get("nxtgrd_max", ""),
        nxtgrd_min=pdk_data.get("nxtgrd_min", ""),
        starrc_layer_map=pdk_data.get("starrc_layer_map", ""),
        cell_name_suffix_strip=pdk_data.get("cell_name_suffix_strip", ""),
        liberty_suffix_strip=pdk_data.get("liberty_suffix_strip", ""),
    )


def _parse_libraries(lib_data: dict) -> LibraryConfig:
    """Parse library config from YAML."""
    bc = lib_data.get("boundary_cells", {})
    if isinstance(bc, dict):
        pass
    else:
        bc = {}
    return LibraryConfig(
        std_cell_libs=lib_data.get("std_cell_libs", []),
        macro_libs=lib_data.get("macro_libs", []),
        io_libs=lib_data.get("io_libs", []),
        ndm_libs=lib_data.get("ndm_libs", []),
        liberty_libs=lib_data.get("liberty_libs", []),
        dont_use_cells=lib_data.get("dont_use_cells", []),
        vt_libs=lib_data.get("vt_libs", {}),
        main_lib_name=lib_data.get("main_lib_name", ""),
        eco_lib=lib_data.get("eco_lib", ""),
        vt_percentage_constraint=lib_data.get("vt_percentage_constraint", {}),
        driver_cell=lib_data.get("driver_cell", ""),
        delay_cell=lib_data.get("delay_cell", ""),
        antenna_cell=lib_data.get("antenna_cell", ""),
        boundary_cells=bc,
        tap_cell=lib_data.get("tap_cell", ""),
        endcap_cell=lib_data.get("endcap_cell", ""),
        decap_cells=lib_data.get("decap_cells", []),
        filler_cells=lib_data.get("filler_cells", []),
    )


def _is_legacy_schema(data: dict) -> bool:
    """Detect legacy flat schema used by early ImplCraft configs."""
    return "design_name" in data or isinstance(data.get("libraries", {}).get("std_cell"), list)


def _convert_legacy_schema(data: dict) -> dict:
    """Convert legacy flat schema to the current nested schema."""
    converted: dict[str, Any] = copy.deepcopy(data)

    # ---- design ----
    design: dict[str, Any] = {"name": converted.pop("design_name", "top")}
    if "top_module" in converted:
        design["top_module"] = converted.pop("top_module")
    if "scenario" in converted:
        design["scenario"] = converted.pop("scenario")
    if "target_utilization" in converted:
        design["target_utilization"] = converted.pop("target_utilization")

    old_die = converted.pop("die", {})
    if old_die:
        design["die"] = {
            "width_um": old_die.get("width_um", 2900.0),
            "height_um": old_die.get("height_um", 1900.0),
            "core_offset_um": old_die.get("core_offset_um", [180, 180, 180, 180]),
            "target_utilization": old_die.get("target_utilization", 0.7),
        }
        # Flatten die metrics so DesignConfig picks them up directly too.
        design["die_width_um"] = design["die"]["width_um"]
        design["die_height_um"] = design["die"]["height_um"]
        design["core_offset_um"] = design["die"]["core_offset_um"]
        if "target_utilization" not in design and "target_utilization" in old_die:
            design["target_utilization"] = old_die["target_utilization"]

    # ---- clocks -> top-level clock shorthand ----
    clocks = converted.get("clocks", [])
    if clocks and isinstance(clocks, list):
        first_clk = clocks[0]
        if isinstance(first_clk, dict):
            design["clock_period_ns"] = first_clk.get("period_ns", 10.0)
            design["clock_name"] = first_clk.get("name", "clk")

    converted["design"] = design

    # ---- rtl ----
    rtl: dict[str, Any] = converted.get("rtl", {})
    if "sdc_file" in converted:
        rtl["sdc_file"] = converted.pop("sdc_file")
    converted["rtl"] = rtl

    # ---- libraries ----
    libs: dict[str, Any] = converted.get("libraries", {})
    if "std_cell" in libs:
        libs["std_cell_libs"] = libs.pop("std_cell")
    if "io" in libs:
        libs["io_libs"] = libs.pop("io")
    if "macro" in libs:
        libs["macro_libs"] = libs.pop("macro")
    converted["libraries"] = libs

    # ---- eda ----
    eda: dict[str, Any] = converted.get("eda", {})
    if "synopsys" in eda and "synopsys_script" not in eda:
        eda["synopsys_script"] = eda.pop("synopsys")
    if "primetime" in eda and "primetime_script" not in eda:
        eda["primetime_script"] = eda.pop("primetime")
    if "mentor" in eda and "mentor_script" not in eda:
        eda["mentor_script"] = eda.pop("mentor")
    if "cadence" in eda and "cadence_script" not in eda:
        eda["cadence_script"] = eda.pop("cadence")
    converted["eda"] = eda

    # ---- synthesis nested options ----
    syn = converted.get("synthesis", {}) or {}
    if "power" in syn and isinstance(syn["power"], dict):
        pw = syn.pop("power")
        syn["power_optimization"] = pw.get("enabled", True)
        syn["power_effort"] = pw.get("effort", "high")
        syn["leakage_optimization"] = pw.get("leakage", True)
        syn["dynamic_optimization"] = pw.get("dynamic", True)
        syn["power_prediction"] = pw.get("prediction", False)
    if "clock_gating" in syn and isinstance(syn["clock_gating"], dict):
        cg = syn.pop("clock_gating")
        syn["clock_gating"] = cg.get("enabled", True)
        syn["self_gating"] = cg.get("self_gating", False)
        syn["clock_gating_style"] = cg.get("style", "integrated")
        syn["clock_gating_positive_edge"] = cg.get("positive_edge", True)
        syn["clock_gating_control_point"] = cg.get("control_point", "before")
        syn["physically_aware_cg"] = cg.get("physically_aware", True)
        syn["flatten_cg"] = cg.get("flatten", True)
    if "timing" in syn and isinstance(syn["timing"], dict):
        tm = syn.pop("timing")
        syn["critical_range_ns"] = tm.get("critical_range_ns", 0.0)
        syn["max_transition_dc"] = tm.get("max_transition", 0.5)
        syn["max_fanout_dc"] = tm.get("max_fanout", 20)
        syn["max_capacitance_dc"] = tm.get("max_capacitance", 0.5)
        syn["enable_register_merging"] = tm.get("register_merging", False)
    if "mcmm" in syn and isinstance(syn["mcmm"], dict):
        mm = syn.pop("mcmm")
        syn["mcmm_enabled"] = mm.get("enabled", False)
        # scenario objects are left as-is; loader will ignore unknown keys
    if "physical" in syn and isinstance(syn["physical"], dict):
        ph = syn.pop("physical")
        syn["topographical_mode"] = ph.get("enabled", False)
        for k in ["tlu_plus_file", "tech2itf_map", "floorplan_file", "def_file",
                  "physical_constraints_file"]:
            if k in ph:
                syn[k] = ph[k]
    if "dft" in syn and isinstance(syn["dft"], dict):
        dft = syn.pop("dft")
        syn["scan_insertion"] = dft.get("scan_insertion", False)
        syn["scan_style"] = dft.get("scan_style", "multiplexed")
        syn["scan_coverage"] = dft.get("scan_coverage", False)
    if "vt_control" in syn and isinstance(syn["vt_control"], dict):
        vt = syn.pop("vt_control")
        syn["vt_dont_use_patterns"] = vt.get("dont_use", {})
        syn["vt_release_patterns"] = vt.get("release", {})
    if "hierarchy" in syn and isinstance(syn["hierarchy"], dict):
        hier = syn.pop("hierarchy")
        syn["keep_hierarchies"] = hier.get("keep", [])
        syn["flatten_all"] = hier.get("flatten_all", False)
        syn["flatten_start_level"] = hier.get("flatten_start_level", 2)
        syn["size_only_patterns"] = hier.get("size_only_patterns", [])
    converted["synthesis"] = syn

    # Preserve other top-level sections that do not need conversion.
    for key in ["timing_derate", "cts", "placement", "routing", "pt", "flow",
                "innovus", "tempus", "pegasus", "icc2", "calibre"]:
        if key in data and key not in converted:
            converted[key] = data[key]

    # Normalize legacy timing_derate keys (late/early -> late_factor/early_factor).
    if "timing_derate" in converted:
        td = converted["timing_derate"]
        if isinstance(td, dict):
            if "late" in td and "late_factor" not in td:
                td["late_factor"] = td.pop("late")
            if "early" in td and "early_factor" not in td:
                td["early_factor"] = td.pop("early")

    return converted


def load_config(config_path: str | Path) -> tuple[DesignConfig, dict[str, Any]]:
    """
    Load project configuration from a YAML file.

    Supports both the current nested schema and the legacy flat schema.

    Returns:
        (DesignConfig, flow_options) tuple.
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        data = yaml.safe_load(f)

    if data is None:
        data = {}

    # Backward compatibility with old flat schema
    if _is_legacy_schema(data):
        data = _convert_legacy_schema(data)

    design_data = data.get("design", {})
    pdk_data = data.get("pdk", {})
    lib_data = data.get("libraries", {})
    rtl_data = data.get("rtl", {})
    clocks_data = data.get("clocks", [])
    derate_data = data.get("timing_derate", {})
    cts_data = data.get("cts", {}) or {}
    place_data = data.get("placement", {}) or {}
    route_data = data.get("routing", {}) or {}
    syn_data = data.get("synthesis", {}) or {}

    # Parse sub-configs
    pdk = _parse_pdk(pdk_data)
    libraries = _parse_libraries(lib_data)
    clocks = _parse_clocks(clocks_data) if clocks_data else []

    derate = TimingDerateConfig(
        late_factor=float(derate_data.get("late_factor", 1.0)),
        early_factor=float(derate_data.get("early_factor", 1.0)),
        late_clock_factor=_opt_float(derate_data.get("late_clock_factor")),
        early_clock_factor=_opt_float(derate_data.get("early_clock_factor")),
    )

    cts = CTSConfig(
        target_skew_ns=float(cts_data.get("target_skew_ns", 0.1)),
        target_early_delay_ns=float(cts_data.get("target_early_delay_ns", 0.0)),
        max_transition_ns=_opt_float(cts_data.get("max_transition_ns")),
        max_fanout=cts_data.get("max_fanout"),
        leaf_max_transition_ns=_opt_float(cts_data.get("leaf_max_transition_ns")),
        use_leaf_max_transition_on_macros=cts_data.get("use_leaf_max_transition_on_macros", False),
        max_rc_delay_ns=_opt_float(cts_data.get("max_rc_delay_ns")),
        inter_clock_balance=cts_data.get("inter_clock_balance", False),
        ocv_clustering=cts_data.get("ocv_clustering", True),
        ocv_path_sharing=cts_data.get("ocv_path_sharing", True),
        logic_level_balance=cts_data.get("logic_level_balance", False),
        routing_layers=cts_data.get("routing_layers", []),
        stop_pin_on_macro=cts_data.get("stop_pin_on_macro", True),
    )

    placement = PlacementConfig(
        target_utilization=float(place_data.get("target_utilization", 0.7)),
        max_cell_density_threshold=float(place_data.get("max_cell_density_threshold", -1.0)),
        congestion_effort=place_data.get("congestion_effort", "medium"),
        target_routing_density=float(place_data.get("target_routing_density", 0.6)),
        max_net_length_um=float(place_data.get("max_net_length_um", 250.0)),
        vt_min_filler_size=int(place_data.get("vt_min_filler_size", 2)),
        consider_vt_spacing=place_data.get("consider_vt_spacing", True),
        consider_continuous_od_spacing=place_data.get("consider_continuous_od_spacing", True),
        consider_pode_spacing=place_data.get("consider_pode_spacing", False),
        insert_endcap=place_data.get("insert_endcap", True),
        insert_welltap=place_data.get("insert_welltap", True),
        insert_predecap=place_data.get("insert_predecap", True),
        insert_postdecap=place_data.get("insert_postdecap", True),
        insert_spare=place_data.get("insert_spare", False),
        insert_eco=place_data.get("insert_eco", True),
        tap_distance_um=float(place_data.get("tap_distance_um", 40.0)),
        power_net=place_data.get("power_net", "VDD"),
        ground_net=place_data.get("ground_net", "VSS"),
        macro_keepout_margin=place_data.get("macro_keepout_margin", [5.0, 5.0, 5.0, 5.0]),
        auto_macro_placement=place_data.get("auto_macro_placement", True),
    )

    routing = RoutingConfig(
        timing_driven=route_data.get("timing_driven", True),
        timing_driven_effort=route_data.get("timing_driven_effort", "high"),
        crosstalk_driven=route_data.get("crosstalk_driven", True),
        track_timing_driven=route_data.get("track_timing_driven", True),
        track_crosstalk_driven=route_data.get("track_crosstalk_driven", True),
        antenna_fixing=route_data.get("antenna_fixing", True),
        insert_diodes_during_routing=route_data.get("insert_diodes_during_routing", True),
        optimize_wire_via_effort=route_data.get("optimize_wire_via_effort", "high"),
        optimize_tie_off_effort=route_data.get("optimize_tie_off_effort", "high"),
        repair_shorts_over_macros_effort=route_data.get("repair_shorts_over_macros_effort", "high"),
        generate_off_grid_pin_tracks=route_data.get("generate_off_grid_pin_tracks", True),
        si_delta_delay=route_data.get("si_delta_delay", True),
        si_route_xtalk_prevention=route_data.get("si_route_xtalk_prevention", True),
        si_static_noise=route_data.get("si_static_noise", True),
        si_timing_window=route_data.get("si_timing_window", True),
        si_analysis_effort=route_data.get("si_analysis_effort", "medium"),
        redundant_via_insertion=route_data.get("redundant_via_insertion", "medium"),
        search_repair_loop=int(route_data.get("search_repair_loop", 40)),
        eco_route_search_repair_loops=int(route_data.get("eco_route_search_repair_loops", 20)),
        xtalk_reduction_loops=int(route_data.get("xtalk_reduction_loops", 5)),
    )

    synthesis = SynthesisConfig(
        compile_ultra=syn_data.get("compile_ultra", True),
        no_autoungroup=syn_data.get("no_autoungroup", True),
        timing_high_effort=syn_data.get("timing_high_effort", True),
        incremental_compile=syn_data.get("incremental_compile", False),
        max_incremental_loops=int(syn_data.get("max_incremental_loops", 0)),
        tns_effort=syn_data.get("tns_effort", "high"),
        high_resistance=syn_data.get("high_resistance", False),
        power_optimization=syn_data.get("power_optimization", True),
        power_effort=syn_data.get("power_effort", "high"),
        physically_aware_cg=syn_data.get("physically_aware_cg", True),
        flatten_cg=syn_data.get("flatten_cg", True),
        critical_range_ns=float(syn_data.get("critical_range_ns", 0.0)),
        max_transition_dc=float(syn_data.get("max_transition_dc", 0.5)),
        max_fanout_dc=int(syn_data.get("max_fanout_dc", 20)),
        awe_effort=int(syn_data.get("awe_effort", 10)),
        arnoldi_effort=int(syn_data.get("arnoldi_effort", 10)),
        enable_register_merging=syn_data.get("enable_register_merging", False),
        num_cores=int(syn_data.get("num_cores", 64)),
    )

    # Parse EDA environment
    eda_data = data.get("eda", {})
    if isinstance(eda_data, dict):
        eda = EDAEnvironment(
            synopsys_script=eda_data.get("synopsys_script", ""),
            primetime_script=eda_data.get("primetime_script", ""),
            mentor_script=eda_data.get("mentor_script", ""),
            cadence_script=eda_data.get("cadence_script", ""),
        )
    else:
        eda = EDAEnvironment()

    config = DesignConfig(
        design_name=design_data.get("name", "top"),
        top_module=design_data.get("top_module", design_data.get("name", "top")),
        clock_period_ns=float(design_data.get("clock_period_ns", 10.0)),
        clock_name=design_data.get("clock_name", "clk"),
        die_width_um=float(design_data.get("die_width_um", 2900.0)),
        die_height_um=float(design_data.get("die_height_um", 1900.0)),
        core_offset_um=design_data.get("core_offset_um", [180, 180, 180, 180]),
        scenario=design_data.get("scenario", "func.tt0p9v.wc.cmax_25c.setup"),
        pdk=pdk,
        libraries=libraries,
        rtl_files=rtl_data.get("files", []),
        rtl_dir=rtl_data.get("dir", ""),
        rtl_filelist=rtl_data.get("filelist", ""),
        sdc_file=rtl_data.get("sdc_file", ""),
        clocks=clocks,
        timing_derate=derate,
        cts=cts,
        placement=placement,
        routing=routing,
        synthesis=synthesis,
        eda=eda,
        target_utilization=float(design_data.get("target_utilization", 0.7)),
    )

    # Preserve tool-specific sections that adapters may query at runtime.
    for tool_key in ["innovus", "tempus", "pegasus", "icc2", "calibre"]:
        if tool_key in data:
            setattr(config, tool_key, data[tool_key])

    # Extract flow options
    flow_data = data.get("flow", {})
    flow_options = {
        "work_root": flow_data.get("work_root", "./work"),
        "dry_run": flow_data.get("dry_run", False),
        "stages": flow_data.get("stages", None),
        "tool_chain": flow_data.get("tool_chain", "synopsys"),
    }

    return config, flow_options


def _opt_float(val) -> float | None:
    """Convert to float or return None."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def save_config(config: DesignConfig, path: str | Path, flow_options: dict[str, Any] | None = None):
    """Save configuration to YAML."""
    path = Path(path)

    data: dict[str, Any] = {
        "design": {
            "name": config.design_name,
            "top_module": config.top_module,
            "clock_period_ns": config.clock_period_ns,
            "clock_name": config.clock_name,
            "die_width_um": config.die_width_um,
            "die_height_um": config.die_height_um,
            "core_offset_um": config.core_offset_um,
            "target_utilization": config.target_utilization,
            "scenario": config.scenario,
        },
        "pdk": {
            "name": config.pdk.name,
            "tech_file": config.pdk.tech_file,
            "metal_stack": config.pdk.metal_stack,
            "min_routing_layer": config.pdk.min_routing_layer,
            "max_routing_layer": config.pdk.max_routing_layer,
            "min_layer_mode": config.pdk.min_layer_mode,
            "max_layer_mode": config.pdk.max_layer_mode,
            "calibre_drc_runset": config.pdk.calibre_drc_runset,
            "calibre_lvs_runset": config.pdk.calibre_lvs_runset,
            "tlu_plus_max": config.pdk.tlu_plus_max,
            "tlu_plus_min": config.pdk.tlu_plus_min,
            "tech2itf_map": config.pdk.tech2itf_map,
            "setup_voltage_v": config.pdk.setup_voltage_v,
            "hold_voltage_v": config.pdk.hold_voltage_v,
            "temperature_c": config.pdk.temperature_c,
        },
        "libraries": {
            "std_cell_libs": config.libraries.std_cell_libs,
            "ndm_libs": config.libraries.ndm_libs,
            "macro_libs": config.libraries.macro_libs,
            "io_libs": config.libraries.io_libs,
            "dont_use_cells": config.libraries.dont_use_cells,
            "main_lib_name": config.libraries.main_lib_name,
            "eco_lib": config.libraries.eco_lib,
            "driver_cell": config.libraries.driver_cell,
            "delay_cell": config.libraries.delay_cell,
            "antenna_cell": config.libraries.antenna_cell,
            "tap_cell": config.libraries.tap_cell,
            "endcap_cell": config.libraries.endcap_cell,
            "decap_cells": config.libraries.decap_cells,
            "filler_cells": config.libraries.filler_cells,
            "boundary_cells": config.libraries.boundary_cells,
        },
        "rtl": {
            "files": config.rtl_files,
            "sdc_file": config.sdc_file,
        },
    }

    # Clocks
    if config.clocks:
        data["clocks"] = []
        for c in config.clocks:
            data["clocks"].append({
                "name": c.name,
                "period_ns": c.period_ns,
                "setup_uncertainty_ns": c.setup_uncertainty_ns,
                "hold_uncertainty_ns": c.hold_uncertainty_ns,
                "transition_ns": c.transition_ns,
                "clock_type": c.clock_type,
                "top_metal": c.top_metal,
                "pin_or_port": c.pin_or_port,
            })

    # Timing derate
    d = config.timing_derate
    if d.late_factor != 1.0 or d.early_factor != 1.0:
        data["timing_derate"] = {
            "late_factor": d.late_factor,
            "early_factor": d.early_factor,
        }

    # CTS
    c = config.cts
    data["cts"] = {
        "target_skew_ns": c.target_skew_ns,
        "target_early_delay_ns": c.target_early_delay_ns,
        "inter_clock_balance": c.inter_clock_balance,
        "ocv_clustering": c.ocv_clustering,
        "ocv_path_sharing": c.ocv_path_sharing,
    }

    # Placement
    p = config.placement
    data["placement"] = {
        "target_utilization": p.target_utilization,
        "congestion_effort": p.congestion_effort,
        "max_net_length_um": p.max_net_length_um,
        "insert_endcap": p.insert_endcap,
        "insert_welltap": p.insert_welltap,
        "insert_predecap": p.insert_predecap,
        "insert_postdecap": p.insert_postdecap,
        "insert_spare": p.insert_spare,
        "insert_eco": p.insert_eco,
        "tap_distance_um": p.tap_distance_um,
        "power_net": p.power_net,
        "ground_net": p.ground_net,
    }

    # Routing
    r = config.routing
    data["routing"] = {
        "timing_driven": r.timing_driven,
        "timing_driven_effort": r.timing_driven_effort,
        "crosstalk_driven": r.crosstalk_driven,
        "antenna_fixing": r.antenna_fixing,
        "si_delta_delay": r.si_delta_delay,
        "si_static_noise": r.si_static_noise,
        "redundant_via_insertion": r.redundant_via_insertion,
        "search_repair_loop": r.search_repair_loop,
    }

    # Synthesis
    s = config.synthesis
    data["synthesis"] = {
        "compile_ultra": s.compile_ultra,
        "tns_effort": s.tns_effort,
        "power_optimization": s.power_optimization,
        "max_transition_dc": s.max_transition_dc,
        "max_fanout_dc": s.max_fanout_dc,
        "num_cores": s.num_cores,
    }

    if flow_options:
        data["flow"] = flow_options

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


# =============================================================================
# Stage-specific config loaders (industrial architecture)
# =============================================================================

def load_pt_config(yaml_path: str | Path):
    """Load PrimeTime stage config from YAML file."""
    from .pt_config import PTStageConfig
    return PTStageConfig.from_yaml(yaml_path)


def load_dc_config(yaml_path: str | Path):
    """Load DC synthesis stage config from YAML file."""
    from .dc_config import DCStageConfig
    return DCStageConfig.from_yaml(yaml_path)
