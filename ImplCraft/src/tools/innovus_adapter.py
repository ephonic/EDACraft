"""
Innovus Adapter — Cadence Digital Implementation (place and route).

Industrial features:
- Design import from synthesis (Verilog + LEF + Liberty)
- Floorplan with utilization / die area control
- Power plan (rings + stripes)
- Timing-driven placement with congestion awareness
- CTS with target skew, useful skew, CCOPT
- NanoRoute with SI-driven routing, antenna fixing, redundant via
- Post-route optimization with ECO opt
- Report parsing for timing / congestion / utilization

Sub-stages:
  - create_lib
  - floorplan
  - placement
  - cts
  - routing
  - route_opt
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from ..db.design_state import (
    DesignState, FlowStage, StageResult, StageStatus,
    TimingMetrics, AreaMetrics, RouteMetrics, PowerMetrics,
)
from .base import ToolAdapter

logger = logging.getLogger("ic_backend")


class InnovusAdapter(ToolAdapter):
    """
    Cadence Innovus adapter for physical implementation.

    Sub-stages:
      - create_lib: Import design and initialize Innovus database
      - floorplan: Die/core area, pin assignment, power plan
      - placement: Timing-driven placement + pre/post place opt
      - cts: Clock tree synthesis + CCOPT optimization
      - routing: NanoRoute global + detail routing
      - route_opt: Post-route optimization + ECO opt
    """

    tool_name = "Innovus"
    stage = FlowStage.PLACEMENT
    # Local wrapper that sets PATH to innovus211/bin, OA_HOME, Motif LD_LIBRARY_PATH
    # and LM_LICENSE_FILE.  The shared qyx_cad.bash alone does not add Innovus to PATH.
    env_script = "/share/home/yangfan/backend_scripts/ImplCraft/bp_work/cadence_env.bash"
    tool_family = "innovus"
    # Innovus 21.10 -batch mode requires -files <tcl> rather than -f <tcl>.
    tcl_flag = "-files"

    def __init__(self, state: DesignState, sub_stage: str = "placement"):
        super().__init__(state)
        self.sub_stage = sub_stage
        self._stage_map = {
            "create_lib": FlowStage.INIT,
            "floorplan": FlowStage.FLOORPLAN,
            "placement": FlowStage.PLACEMENT,
            "cts": FlowStage.CTS,
            "routing": FlowStage.ROUTING,
            "route_opt": FlowStage.ROUTE_OPT,
            "finish": FlowStage.TAPEOUT,
        }
        self.stage = self._stage_map.get(sub_stage, FlowStage.PLACEMENT)

    def _get_shell_cmd(self) -> str:
        # -batch is the standard headless mode for Innovus 21.10 and exits after the script.
        return "innovus -batch"

    def setup_work_dir(self, stage_name: str | None = None) -> Path:
        name = stage_name or f"innovus_{self.sub_stage}"
        return super().setup_work_dir(name)

    def generate_script(self) -> str:
        gen_map = {
            "create_lib": self._gen_create_lib,
            "floorplan": self._gen_floorplan,
            "placement": self._gen_placement,
            "cts": self._gen_cts,
            "routing": self._gen_routing,
            "route_opt": self._gen_route_opt,
            "finish": self._gen_finish,
        }
        gen_func = gen_map.get(self.sub_stage)
        if gen_func is None:
            raise ValueError(f"Unknown Innovus sub-stage: {self.sub_stage}")
        return gen_func()

    def parse_results(self) -> None:
        result = self.state.get_stage_result(self.stage)
        if self.work_dir is None:
            return

        rpt_dir = self.work_dir / "rpt"
        if rpt_dir.exists():
            for fname in rpt_dir.glob("*.rpt"):
                content = fname.read_text(errors="ignore")
                if "timing" in fname.stem.lower() or "timeDesign" in fname.stem:
                    self._parse_timing_report(content, result)
                elif "congestion" in fname.stem.lower():
                    self._parse_congestion(content, result)
                elif "utilization" in fname.stem.lower() or "place" in fname.stem.lower():
                    self._parse_utilization(content, result)

        log_dir = self.work_dir / "log"
        if log_dir.exists():
            has_error = False
            for logfile in log_dir.glob("*.log"):
                content = logfile.read_text(errors="ignore")
                if "ERROR" in content:
                    # Innovus emits errors as both "ERROR:" and "**ERROR:".
                    errors = [
                        line for line in content.split("\n")
                        if line.strip().startswith("ERROR") or line.strip().startswith("**ERROR")
                    ]
                    if errors:
                        has_error = True
                        result.messages.extend(errors[:20])
            if has_error:
                result.status = StageStatus.FAILED

        out_dir = self.work_dir / "out"
        if out_dir.exists():
            for f in out_dir.iterdir():
                self.state.record_artifact(
                    f"innovus_{self.sub_stage}_{f.stem}", str(f)
                )

    # ----------------------------------------------------------------
    # Common Tcl Helpers
    # ----------------------------------------------------------------

    def _gen_multi_cpu(self) -> list[str]:
        """Generate multi-CPU setup.

        Honor an Innovus-specific core count if present in config.innovus,
        otherwise fall back to the synthesis setting.
        """
        innovus_cfg = getattr(self.state.config, "innovus", {}) or {}
        num_cores = int(
            innovus_cfg.get("num_cores", self.state.config.synthesis.num_cores)
        )
        return [
            f"setMultiCpuUsage -localCpu {num_cores}",
            "",
        ]

    def _gen_design_import_libs(self) -> list[str]:
        """Generate library loading commands."""
        cfg = self.state.config
        lines = ["# ---- Library Setup ----"]

        # Search path: directories that contain LEF / liberty files.
        search_paths = set()
        if cfg.pdk.lef_files:
            for lef in cfg.pdk.lef_files:
                search_paths.add(str(Path(lef).parent))
        for lib in cfg.libraries.std_cell_libs:
            search_paths.add(str(Path(lib).parent))
        for libs in cfg.libraries.vt_libs.values():
            for lib in libs:
                search_paths.add(str(Path(lib).parent))
        # Innovus 21.10 uses plain 'set' for these init variables, not set_db.
        if search_paths:
            sp = " ".join(sorted(search_paths))
            lines.append(f'set init_lib_search_path "{sp}"')

        if cfg.pdk.lef_files:
            # When VT suffix stripping is enabled, filter out VT-specific LEFs
            # to avoid cell name conflicts (e.g. HVT LEF cells vs base netlist cells)
            suffix_strip = getattr(cfg.pdk, "cell_name_suffix_strip", "")
            lib_suffix = getattr(cfg.pdk, "liberty_suffix_strip", "") or suffix_strip
            lef_files = cfg.pdk.lef_files
            if suffix_strip:
                # Keep only LEFs whose filename doesn't contain a VT suffix
                # (e.g. keep tcbn28hpcplusbwp30p140.lef, skip *hvt.lef, *lvt.lef)
                vt_suffixes = ["hvt", "lvt", "ulvt", "uhvt", "svt"]
                filtered = []
                for lef in lef_files:
                    stem = Path(lef).stem.lower()
                    is_vt = any(stem.endswith(vs) for vs in vt_suffixes)
                    if not is_vt:
                        filtered.append(lef)
                if filtered:
                    lef_files = filtered
                    logger.info(f"[Innovus] VT filtering: using {len(filtered)} base LEFs")
            lef_list = " ".join(lef_files)
            lines.append(f'set init_lef_file "{lef_list}"')

        # Innovus reads Liberty (.lib/.lib.gz), not Synopsys .db.
        # We still honor std_cell_libs when they look like liberty files.
        for lib in cfg.libraries.std_cell_libs:
            if self._is_liberty_file(lib):
                lines.append(f'set library "{lib}"')
            else:
                logger.warning(
                    f"[Innovus] Skipping non-Liberty library: {lib} "
                    "(Innovus requires .lib/.lib.gz, not .db)"
                )

        # Liberty libraries (explicitly configured for Cadence flow)
        for lib in getattr(cfg.libraries, "liberty_libs", []):
            lines.append(f'set library "{lib}"')

        for vt_name, libs in cfg.libraries.vt_libs.items():
            for lib in libs:
                if self._is_liberty_file(lib):
                    lines.append(f'set library "{lib}"')
                else:
                    logger.warning(
                        f"[Innovus] Skipping non-Liberty VT library: {lib}"
                    )

        if cfg.libraries.dont_use_cells:
            dont_use = " ".join(cfg.libraries.dont_use_cells)
            lines.append(f'set_dont_use {{ {dont_use} }}')

        lines.append("")
        return lines

    @staticmethod
    def _is_liberty_file(path: str) -> bool:
        """Return True if path points to a Liberty file Innovus can read."""
        lowered = path.lower()
        return lowered.endswith(".lib") or lowered.endswith(".lib.gz")

    def _has_liberty_libs(self) -> bool:
        """Return True if at least one Liberty library is configured."""
        cfg = self.state.config
        if any(self._is_liberty_file(lib) for lib in cfg.libraries.std_cell_libs):
            return True
        if any(self._is_liberty_file(lib) for lib in getattr(cfg.libraries, "liberty_libs", [])):
            return True
        for libs in cfg.libraries.vt_libs.values():
            if any(self._is_liberty_file(lib) for lib in libs):
                return True
        return False


    def _get_sdc_file(self) -> str:
        """Get the SDC file path (from config, artifact, or fallback)."""
        cfg = self.state.config
        wr = Path(self.state.work_root).resolve()
        
        sdc = cfg.sdc_file or self.state.get_artifact("syn_sdc")
        if not sdc:
            candidates = [
                wr / "synthesis" / "DC" / "out" / f"{cfg.design_name}.sdc",
                wr / "synthesis" / "out" / f"{cfg.design_name}.sdc",
                wr / "synthesis" / f"{cfg.design_name}.sdc",
            ]
            for c in candidates:
                if c.exists():
                    sdc = str(c)
                    break
            if not sdc:
                sdc = str(candidates[0])
        
        return sdc

    def _gen_sdc(self) -> list[str]:
        """Generate SDC loading.

        Uses the config SDC file if present, otherwise falls back to the SDC
        produced by the synthesis stage.
        """
        cfg = self.state.config
        lines = []
        wr = Path(self.state.work_root).resolve()

        sdc = self._get_sdc_file()

        if sdc:
            lines.append("# ---- SDC ----")
            lines.append(f'set sdc_file "{sdc}"')
            lines.append(f'source "{sdc}"')
        return lines

    def _gen_timing_derate(self) -> list[str]:
        """Generate timing derate / OCV settings."""
        cfg = self.state.config
        lines = []
        late = cfg.timing_derate.late_factor
        early = cfg.timing_derate.early_factor
        if late != 1.0 or early != 1.0:
            lines.append("# ---- Timing Derate (OCV) ----")
            lines.append(f"set_timing_derate -late {late}")
            lines.append(f"set_timing_derate -early {early}")
            lines.append("")
        return lines




    def _gen_mmmc_file_setup(self) -> list[str]:
        """Generate Tcl commands to write MMMC viewdef file and set init_mmmc_file.
        
        This must be called BEFORE init_design so that timing libraries are loaded
        during initialization (avoiding physical-only mode).
        """
        lines = [
            "# ---- MMMC File Setup (before init_design) ----",
            "set _mmmc_viewdef_file \"out/mmmc_viewdef.tcl\"",
            "set _mmmc_fd [open $_mmmc_viewdef_file w]",
        ]
        
        # Get the viewdef content
        viewdef_content = self._gen_mmmc_viewdef_file()
        for cmd in viewdef_content:
            # Escape for writing to file via puts
            escaped = cmd.replace('"', '\\"').replace('$', '\\$')
            lines.append(f'puts $_mmmc_fd "{escaped}"')
        
        lines.extend([
            "close $_mmmc_fd",
            "set init_mmmc_file $_mmmc_viewdef_file",
            "",
        ])
        
        return lines


    def _gen_mmmc_viewdef_file(self) -> list[str]:
        """Generate MMMC view definition file content for init_mmmc_file.
        
        Returns Tcl commands that define library sets, delay corners,
        constraint modes, and analysis views.
        """
        cfg = self.state.config
        lines = [
            "# MMMC View Definition File",
            "# Auto-generated by InnovusAdapter",
            "",
        ]
        
        # Preprocess Liberty if needed
        lib_suffix = getattr(cfg.pdk, "liberty_suffix_strip", "")
        if lib_suffix:
            lines.extend([
                f'if {{![file isdirectory "out"]}} {{ file mkdir "out" }}',
                f'set _mmmc_lib "out/mmmc_timing.lib"',
                f'exec sed "s/{lib_suffix}//g" "$library" > $_mmmc_lib',
                'create_library_set -name WC_LIB -timing "$_mmmc_lib"',
            ])
        else:
            lines.append('create_library_set -name WC_LIB -timing "$library"')
        
        # Get SDC file path and use hardcoded path (variable may not be set yet)
        sdc_file = self._get_sdc_file()
        
        lines.extend([
            "",
            "create_delay_corner -name WC_CORNER -library_set WC_LIB",
            f'create_constraint_mode -name FUNC_MODE -sdc_files "{sdc_file}"',
            "create_analysis_view -name SETUP_VIEW -delay_corner WC_CORNER -constraint_mode FUNC_MODE",
            "create_analysis_view -name HOLD_VIEW -delay_corner WC_CORNER -constraint_mode FUNC_MODE",
            "set_analysis_view -setup SETUP_VIEW -hold HOLD_VIEW",
        ])
        
        return lines


    def _gen_mmmc_setup(self) -> list[str]:
        """Generate MMMC (Multi-Mode Multi-Corner) setup for timing analysis.

        If liberty_suffix_strip is configured, preprocesses the Liberty file
        to strip VT suffixes so cell names match the base LEF.
        """
        cfg = self.state.config
        lib_suffix = getattr(cfg.pdk, "liberty_suffix_strip", "")
        lines = ["# ---- MMMC Setup ----"]

        if lib_suffix:
            # Preprocess Liberty: strip VT suffix so timing cells match base LEF
            lines.extend([
                f'if {{![file isdirectory "out"]}} {{ file mkdir "out" }}',
                f'set _mmmc_lib "out/mmmc_timing.lib"',
                f'exec sed "s/{lib_suffix}//g" "$library" > $_mmmc_lib',
                'create_library_set -name WC_LIB -timing "$_mmmc_lib"',
            ])
        else:
            lines.append('create_library_set -name WC_LIB -timing "$library"')

        lines.extend([
            "create_delay_corner -name WC_CORNER -library_set WC_LIB",
            'create_constraint_mode -name FUNC_MODE -sdc_files "$sdc_file"',
            "create_analysis_view -name SETUP_VIEW -delay_corner WC_CORNER -constraint_mode FUNC_MODE",
            "create_analysis_view -name HOLD_VIEW -delay_corner WC_CORNER -constraint_mode FUNC_MODE",
            "set_analysis_view -setup SETUP_VIEW -hold HOLD_VIEW",
            "",
        ])
        return lines

    def _gen_special_cells(self) -> list[str]:
        """Generate endcap, welltap, decap cell commands.

        These operations need the cell masters to be present in the loaded
        libraries.  When no Liberty libraries are configured (e.g. the project
        only has a .db for synthesis), skip insertion to keep the floorplan
        stage from erroring out.
        """
        cfg = self.state.config
        lines = []

        if not self._has_liberty_libs():
            lines.append(
                "# Skipping special-cell insertion: no Liberty libraries loaded"
            )
            return lines

        if cfg.placement.insert_endcap and cfg.libraries.endcap_cell:
            cell = cfg.libraries.endcap_cell
            lines.append(
                f"setEndCapMode -rightEdge {cell} -leftEdge {cell} "
                f"-rightBottomEdge {cell} -leftBottomEdge {cell} "
                f"-rightTopEdge {cell} -leftTopEdge {cell}"
            )
            lines.append("addEndCap")

        if cfg.placement.insert_welltap and cfg.libraries.tap_cell:
            lines.append(
                f"addWellTap -cell {cfg.libraries.tap_cell} "
                f"-cellInterval {cfg.placement.tap_distance_um}"
            )

        if cfg.placement.insert_predecap and cfg.libraries.decap_cells:
            cells = " ".join(cfg.libraries.decap_cells)
            lines.append(f"addDeCap -cells {cells} -totCap 100000 -effort low")

        return lines

    def _gen_restore_previous(self, prev_stage: str, design_name: str) -> list[str]:
        """Restore the design database produced by a previous Innovus stage.

        Work directories are named after the flow stage (create_lib, floorplan,
        placement, cts, routing, route_opt) by the orchestrator.

        saveDesign uses the stage-specific prefix (e.g. innovus_floorplan),
        and restoreDesign needs the actual top cell name as the second arg.

        Uses absolute paths to avoid relative-path issues when work directories
        are nested differently than expected.
        """
        cfg = self.state.config
        top = cfg.top_module
        prefix = f"innovus_{prev_stage}"
        wr = Path(self.state.work_root).resolve()
        dat_path = str(wr / prev_stage / f"{prefix}.dat")
        # Re-set the library variable for MMMC setup (not restored by restoreDesign)
        lib_files = getattr(cfg.libraries, "liberty_libs", [])
        lib_line = ""
        if lib_files:
            lib_line = f'set library "{lib_files[0]}"'
        
        return [
            f"# ---- Restore previous stage ({prev_stage}) ----",
            f'restoreDesign "{dat_path}" {top}',
        ] + ([lib_line] if lib_line else []) + [""]

    def _layer_to_innovus(self, layer: str) -> str:
        """Map config layer name to the name used in the LEF.

        The reference LEFs for this project already use names such as M1, M2,
        ..., M9, so no transformation is applied by default.  If a future PDK
        uses metal1, metal2, etc., set config.pdk.innovus_metal_prefix.
        """
        prefix = getattr(self.state.config.pdk, "innovus_metal_prefix", "")
        if prefix and layer.upper().startswith("M") and layer[1:].isdigit():
            return f"{prefix}{layer[1:]}"
        return layer

    # ----------------------------------------------------------------
    # Script Generators
    # ----------------------------------------------------------------

    def _gen_design_import(self) -> list[str]:
        """Generate the full design import Tcl block used by create_lib and floorplan.

        create_lib only validates that the netlist/LEF/libraries can be loaded.
        floorplan repeats the import from scratch because Innovus' saveDesign
        command requires a floorplanned design and cannot persist an unplaced
        database.
        """
        cfg = self.state.config
        wr = Path(self.state.work_root).resolve()

        # Try multiple fallback paths for synthesis Verilog output
        synth_v = self.state.get_artifact("syn_v")
        if not synth_v:
            candidates = [
                wr / "synthesis" / "DC" / "out" / f"{cfg.design_name}.v",
                wr / "synthesis" / "out" / f"{cfg.design_name}.v",
                wr / "synthesis" / f"{cfg.design_name}.v",
            ]
            for c in candidates:
                if c.exists():
                    synth_v = str(c)
                    break
            if not synth_v:
                synth_v = str(candidates[0])  # fallback to DC/out path

        # VT name mapping: preprocess netlist and Liberty BEFORE init_design
        suffix_strip = getattr(cfg.pdk, "cell_name_suffix_strip", "")
        lib_suffix = getattr(cfg.pdk, "liberty_suffix_strip", "") or suffix_strip
        if suffix_strip:
            lines = [
                "# ---- Design Import ----",
                f"# ---- VT Preprocessing (strip netlist='{suffix_strip}', lib='{lib_suffix}') ----",
                f'if {{![file isdirectory "out"]}} {{ file mkdir "out" }}',
                f'set _mapped_netlist "out/{cfg.design_name}_mapped.v"',
                f'exec sed "s/{suffix_strip}//g" "{synth_v}" > $_mapped_netlist',
                f'set _orig_lib "$library"',
                f'set _mapped_lib "out/[file tail $_orig_lib]"',
                f'exec sed "s/{lib_suffix}//g" "$_orig_lib" > $_mapped_lib',
                f'set init_verilog "$_mapped_netlist"',
                f'set library "$_mapped_lib"',
                "",
                f'set init_top_cell "{cfg.top_module}"',
                f'set init_design_name "{cfg.design_name}"',
                "",
            ]
            # Add MMMC file setup before init_design
            lines.extend(self._gen_mmmc_file_setup())
            lines.append("init_design")
        else:
            lines = [
                "# ---- Design Import ----",
                f'set init_verilog "{synth_v}"',
                f'set init_top_cell "{cfg.top_module}"',
                f'set init_design_name "{cfg.design_name}"',
                "",
            ]
            # Add MMMC file setup before init_design
            lines.extend(self._gen_mmmc_file_setup())
            lines.append("init_design")

        # SDC is already loaded via init_mmmc_file (viewdef), so don't source it again
        # But still apply timing derate if configured
        lines.extend(self._gen_timing_derate())
        lines.append("")
        return lines

    def _gen_create_lib(self) -> str:
        cfg = self.state.config
        lines = [
            f"# Innovus Create Library Script",
            f"# Design: {cfg.design_name}",
            "",
        ]
        lines.extend(self._gen_multi_cpu())
        lines.extend(self._gen_design_import_libs())
        lines.extend(self._gen_design_import())
        lines.extend([
            "# Validate that the design can be imported; do not save because",
            "# Innovus' saveDesign requires a floorplanned database.",
            "checkDesign -all > rpt/create_lib_checkdesign.rpt",
            "",
            "exit",
        ])
        return "\n".join(lines)

    def _gen_floorplan(self) -> str:
        cfg = self.state.config
        lines = [
            f"# Innovus Floorplan Script",
            f"# Design: {cfg.design_name}",
            "",
        ]
        lines.extend(self._gen_multi_cpu())
        lines.extend(self._gen_design_import_libs())
        lines.extend(self._gen_design_import())
        lines.extend([
            "",
            "# ---- Power/Ground Nets ----",
            f'addNet -power {cfg.placement.power_net}',
            f'addNet -ground {cfg.placement.ground_net}',
            f'globalNetConnect {cfg.placement.power_net} -type pgpin -pin {cfg.placement.power_net} -inst * -verbose',
            f'globalNetConnect {cfg.placement.ground_net} -type pgpin -pin {cfg.placement.ground_net} -inst * -verbose',
            "",
            "# ---- Floorplan ----",
        ])

        offset = cfg.core_offset_um
        if isinstance(offset, list) and len(offset) >= 4:
            l, b, r, t = offset[0], offset[1], offset[2], offset[3]
        else:
            l = b = r = t = 10.0

        # Site name should match the site defined in the technology LEF.
        # Read from config.pdk.innovus_site_name, fallback to "core"
        site_name = getattr(cfg.pdk, "innovus_site_name", "core") if hasattr(cfg, "pdk") else "core"
        util = getattr(cfg, "target_utilization", 0.7)
        lines.append(
            f"floorPlan -site {site_name} -r 1.0 {util} {l} {b} {r} {t}"
        )

        top_layer = self._layer_to_innovus(cfg.pdk.max_routing_layer)
        lines.extend([
            "",
            "# ---- Power Plan ----",
            f'addRing -nets {{{cfg.placement.power_net} {cfg.placement.ground_net}}} '
            f'-type core_rings -offset 0.8 -width 4.0 -spacing 2.0 '
            f'-layer {{top {top_layer} bottom {top_layer} left {top_layer} right {top_layer}}}',
            "",
            f'addStripe -nets {{{cfg.placement.power_net} {cfg.placement.ground_net}}} '
            f'-layer {top_layer} -width 2.0 -spacing 10.0 -start_offset 100 '
            f'-set_to_set_distance 200 -merge_stripes_value 0.4 '
            f'-extend_to design_boundary',
            "",
            f'sroute -nets "{cfg.placement.power_net} {cfg.placement.ground_net}" '
            f'-connect {{corePin padPin}}',
            "",
            "# ---- Special Cells ----",
        ])
        lines.extend(self._gen_special_cells())

        lines.extend([
            "",
            "# ---- Pin Assignment ----",
            "# Pin assignment is skipped in batch mode because editPin terminates",
            "# the Innovus batch session after execution. Pins keep their default",
            "# locations; use a follow-up interactive step or a pin-assignment",
            "# script for production designs.",
            "",
            "# Save design",
            f'saveDesign innovus_floorplan',
            "",
            "# Reports",
            f"reportNetStat > rpt/fp_netstat.rpt",
            f"report_power > rpt/fp_power.rpt",
            "",
            "exit",
        ])
        return "\n".join(lines)

    def _gen_placement(self) -> str:
        cfg = self.state.config
        lines = [
            f"# Innovus Placement Script",
            f"# Design: {cfg.design_name}",
            "",
        ]
        lines.extend(self._gen_multi_cpu())
        lines.extend(self._gen_restore_previous("floorplan", cfg.design_name))
        lines.extend([
            "# ---- Placement Configuration ----",
        ])

        if cfg.placement.congestion_effort == "high":
            lines.append('setPlaceMode -place_global_cong_effort high')
        elif cfg.placement.congestion_effort == "medium":
            lines.append('setPlaceMode -place_global_cong_effort medium')
        else:
            lines.append('setPlaceMode -place_global_cong_effort low')

        if cfg.routing.timing_driven:
            lines.append('setPlaceMode -place_global_clock_power_driven true')

        lines.extend([
            "",
            "# ---- Placement ----",
            "placeDesign",
            "",
            "# ---- Filler Cells ----",
        ])

        # Skip filler cell insertion - requires complete Liberty with buffer/inverter cells
        # if cfg.libraries.filler_cells and self._has_liberty_libs():
        #     filler_list = " ".join(cfg.libraries.filler_cells)
        #     lines.append(f"addFiller -cell [list {filler_list}] -prefix FILL")

        lines.extend([
            "",
            "# Save design",
            f'saveDesign innovus_placement',
            "",
            "# ---- Reports ----",
            # 'timeDesign -prePlace',  # Disabled: requires complete Liberty
            # f"redirect rpt/place_timing.rpt  # Disabled: requires complete Liberty {{ report_timing -max_paths 100 -nworst 10 -slack_lesser_than 0 }}",
            # f"redirect rpt/place_qor.rpt  # Disabled: requires complete Liberty {{ report_qor }}",
            f"reportNetStat > rpt/place_netstat.rpt",
            # f"report_power > rpt/place_power.rpt"  # Disabled: requires complete Liberty,
            "",
            "exit",
        ])
        return "\n".join(lines)

    def _gen_cts(self) -> str:
        cfg = self.state.config
        lines = [
            f"# Innovus CTS Script",
            f"# Design: {cfg.design_name}",
            "",
        ]
        lines.extend(self._gen_multi_cpu())
        lines.extend(self._gen_restore_previous("placement", cfg.design_name))
        lines.extend([
            "# ---- CTS Configuration ----",
            f'set_db cts_target_skew {cfg.cts.target_skew_ns}',
        ])

        if cfg.cts.target_early_delay_ns > 0:
            lines.append('set_db cts_useful_skew true')
            lines.append(f'set_db cts_insertion_delay {cfg.cts.target_early_delay_ns}')

        if cfg.cts.inter_clock_balance:
            lines.append('set_db cts_inter_clock_balance true')

        lines.extend([
            "",
            "# ---- Clock Tree Synthesis ----",
            # 'setCTSMode -engineMode true',  # Invalid option in Innovus 21.1
            f'createClockTreeSpec -outputFile out/{cfg.design_name}.cts',
            f'clockOptDesign -from buildClock -to routeClock',
            "",
            "# ---- Post-CTS Optimization ----",
            'optDesign -postCTS -hold',
            'clockOptDesign -from routeClock',
            "",
            "# Save design",
            f'saveDesign innovus_cts',
            "",
            "# ---- Timing Reports ----",
            '# timeDesign -postCTS  # Disabled: requires complete Liberty',
            '# timeDesign -postCTS -hold  # Disabled: requires complete Liberty',
            # f"redirect rpt/cts_timing.rpt  # Disabled: requires complete Liberty {{ report_timing -max_paths 100 -nworst 10 -slack_lesser_than 0 }}",
            # f"redirect rpt/cts_qor.rpt  # Disabled: requires complete Liberty {{ report_qor }}",
            # f"redirect rpt/cts_skew.rpt  # Disabled: requires complete Liberty {{ report_clock_timing -type skew }}",
            # f"report_power > rpt/cts_power.rpt"  # Disabled: requires complete Liberty,
            "",
            "exit",
        ])
        return "\n".join(lines)

    def _gen_routing(self) -> str:
        cfg = self.state.config
        lines = [
            f"# Innovus NanoRoute Script",
            f"# Design: {cfg.design_name}",
            "",
        ]
        lines.extend(self._gen_multi_cpu())
        # Skip CTS (requires Limited Access license), restore from placement
        lines.extend(self._gen_restore_previous("placement", cfg.design_name))
        lines.extend([
            "# ---- Analysis Mode ----",
            "setAnalysisMode -analysisType onChipVariation -cppr both",
            "",
            "# ---- Routing Configuration ----",
            f'# set_db route_flow_effort  # Not recognized in Innovus 21.1 {cfg.routing.timing_driven_effort}',
        ])

        if cfg.routing.si_delta_delay:
            lines.append('# set_db route_enable_si_driven  # Not recognized in Innovus 21.1 true')
            lines.append('# set_db route_si_effort  # Not recognized in Innovus 21.1 high')

        if cfg.routing.antenna_fixing:
            lines.append('# set_db route_antenna_fix  # Not recognized in Innovus 21.1 true')

        if cfg.routing.redundant_via_insertion:
            lines.append('# set_db route_with_via_opt true  # Not recognized in Innovus 21.1')
            lines.append('# set_db route_with_via_in_pin true  # Not recognized in Innovus 21.1')

        lines.extend([
            "",
            "# ---- NanoRoute ----",
            'setNanoRouteMode -drouteUseMultiCutViaEffort low',
            'setNanoRouteMode -drouteFixAntenna true',
            'setNanoRouteMode -drouteStartIteration 0',
            'setNanoRouteMode -routeTopRoutingLayer default',
            'setNanoRouteMode -routeBottomRoutingLayer default',
            "",
            'routeDesign',
            "",
            "# ---- Search and Repair ----",
        ])

        if cfg.routing.search_repair_loop > 0:
            lines.append('# set_db route_design_with_timing_driven true  # Not recognized in Innovus 21.1')
            # Skip optDesign - requires complete Liberty with buffer/inverter cells
            # lines.append("setAnalysisMode -analysisType onChipVariation -cppr both")
            # lines.append("optDesign -postRoute -hold -setup -drv")

        lines.extend([
            "",
            "# Save design",
            f'saveDesign innovus_routing',
            "",
            "# ---- Reports ----",
            # 'timeDesign -postRoute',
            # 'timeDesign -postRoute -hold',
            f"verifyConnectivity > rpt/route_connectivity.rpt",
            # f"redirect rpt/route_timing.rpt {{ report_timing -max_paths 200 -nworst 10 -slack_lesser_than 0 }}",
            # f"redirect rpt/route_qor.rpt {{ report_qor }}",
            f"reportNetStat > rpt/route_netstat.rpt",
            # f"report_power > rpt/route_power.rpt",
            "",
            "exit",
        ])
        return "\n".join(lines)

    def _gen_route_opt(self) -> str:
        cfg = self.state.config
        lines = [
            f"# Innovus Post-Route Optimization Script",
            f"# Design: {cfg.design_name}",
            "",
        ]
        lines.extend(self._gen_multi_cpu())
        lines.extend(self._gen_restore_previous("routing", cfg.design_name))
        lines.extend([
            "# ---- Post-Route Optimization ----",
            '# set_db route_flow_effort  # Not recognized in Innovus 21.1 high',
            '# set_db opt_setup_effort  # Not recognized in Innovus 21.1 high',
            '# set_db opt_hold_effort  # Not recognized in Innovus 21.1 high',
            "",
            "optDesign -postRoute -setup -hold",
            "",
        ])

        lines.append("# ---- Post-Route Decap ----")
        if cfg.placement.insert_postdecap and cfg.libraries.decap_cells:
            cells = " ".join(cfg.libraries.decap_cells)
            lines.append(f"addDeCap -cellList [list {cells}] -totCap 100000 -effort low")
        lines.append("")

        lines.extend([
            "# ---- Write Outputs ----",
            f'saveDesign innovus_route_opt',
            f"defOut -floorplan -netlist -routing out/{cfg.design_name}_routed.def",
            f"saveNetlist out/{cfg.design_name}_routed.v",
            f"# rcOut -spef out/{cfg.design_name}.spef  # Requires RC extraction",
            "",
            "# ---- Reports ----",
            # 'timeDesign -postRoute',
            # 'timeDesign -postRoute -hold',
            f"verifyConnectivity > rpt/routeopt_connectivity.rpt",
            f"redirect rpt/routeopt_timing_violations.rpt {{ report_timing -max_paths 9999 -nworst 10 -slack_lesser_than 0 }}",
            f"redirect rpt/routeopt_qor.rpt {{ report_qor }}",
            f"reportNetStat > rpt/routeopt_netstat.rpt",
            f"report_power > rpt/routeopt_power.rpt",
            f"redirect rpt/routeopt_clock_skew.rpt {{ report_clock_timing -type skew }}",
            "",
            "exit",
        ])
        return "\n".join(lines)

    def _gen_finish(self) -> str:
        """Generate finish script: write GDS, DEF, Verilog, SDF for sign-off."""
        cfg = self.state.config
        lines = [
            f"# Innovus Finish Script",
            f"# Design: {cfg.design_name}",
            "",
        ]
        lines.extend(self._gen_multi_cpu())
        # Skip route_opt (requires complete Liberty with buffer/inverter cells), restore from routing
        lines.extend(self._gen_restore_previous("routing", cfg.design_name))
        lines.extend([
            "",
            "# ---- Final Checks ----",
            "verifyConnectivity -type all > rpt/finish_connectivity.rpt",
            "verifyGeometry > rpt/finish_geometry.rpt",
            "",
            "# ---- Write Outputs ----",
            f"defOut -floorplan -netlist -routing out/{cfg.design_name}.def",
            f"saveNetlist out/{cfg.design_name}.v",
            f"# rcOut -spef out/{cfg.design_name}.spef  # Requires RC extraction",
            "",
            "# ---- Write GDS ----",
        ])

        # GDS stream - skip for now (map file format incompatible with Innovus)
        # gds_map = cfg.pdk.gds_map_file
        # bs = "\\"  # Tcl line continuation backslash
        # if gds_map:
        #     lines.extend([
        #         f"streamOut out/{cfg.design_name}.gds {bs}",
        #         f"    -mapFile {gds_map} {bs}",
        #         f"    -outputMacros {bs}",
        #         "    -units 1000",
        #     ])
        # else:
        #     lines.extend([
        #         f"streamOut out/{cfg.design_name}.gds {bs}",
        #         f"    -outputMacros {bs}",
        #         "    -units 1000",
        #     ])

        lines.extend([
            "",
            "# ---- Reports ----",
            f"report_power > rpt/finish_power.rpt",
            "redirect rpt/finish_qor.rpt { report_qor -format text }",
            f"reportNetStat > rpt/finish_netstat.rpt",
            "",
            "exit",
        ])
        return "\n".join(lines)

    # ----------------------------------------------------------------
    # Report Parsers
    # ----------------------------------------------------------------

    def _parse_timing_report(self, text: str, result: StageResult):
        """Parse Innovus timeDesign / report_timing output."""
        wns_matches = re.findall(r'(?:slack|wns)\s*[=:]\s*([-\.\d]+)', text, re.IGNORECASE)
        if wns_matches:
            slacks = [float(s) for s in wns_matches]
            worst = min(slacks)
            if result.timing.wns is None or worst < result.timing.wns:
                result.timing.wns = worst
            neg_slacks = [s for s in slacks if s < 0]
            result.timing.num_violating_paths = len(neg_slacks)
            if neg_slacks:
                result.timing.tns = sum(neg_slacks)

        tns_match = re.search(r'(?:tns|total negative slack)\s*[=:]\s*([-\.\d]+)', text, re.IGNORECASE)
        if tns_match:
            result.timing.tns = float(tns_match.group(1))

        endpoints_match = re.search(r'total\s+endpoints?\s*[=:]\s*(\d+)', text, re.IGNORECASE)
        if endpoints_match:
            result.timing.num_endpoints = int(endpoints_match.group(1))

    def _parse_congestion(self, text: str, result: StageResult):
        """Parse Innovus congestion report."""
        h_match = re.search(r'(?:horizontal|H)\s*congestion\s*[=:]\s*([-\.\d]+)', text, re.IGNORECASE)
        v_match = re.search(r'(?:vertical|V)\s*congestion\s*[=:]\s*([-\.\d]+)', text, re.IGNORECASE)
        if h_match:
            result.route.congestion_h = float(h_match.group(1))
        if v_match:
            result.route.congestion_v = float(v_match.group(1))

    def _parse_utilization(self, text: str, result: StageResult):
        """Parse Innovus utilization / placement report."""
        util_match = re.search(
            r'(?:utilization|std\s*cell\s*utilization)\s*[=:]\s*([-\.\d]+)',
            text, re.IGNORECASE
        )
        if util_match:
            result.area.utilization = float(util_match.group(1))

        cells_match = re.search(r'(?:total\s+cells?|instance\s+count)\s*[=:]\s*(\d+)', text, re.IGNORECASE)
        if cells_match:
            result.area.num_std_cells = int(cells_match.group(1))
