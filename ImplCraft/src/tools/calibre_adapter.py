"""
Calibre Adapter — physical verification (DRC / LVS).

Generates Calibre rule decks and parses results back into DRCMetrics / LVSMetrics.
"""
from __future__ import annotations

import logging
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from ..db.design_state import (
    DesignState, FlowStage, StageResult, StageStatus,
    DRCMetrics, LVSMetrics,
)
from .base import ToolAdapter
from .utils import gds, netlist, paths, port_labels

logger = logging.getLogger("ic_backend")


class CalibreAdapter(ToolAdapter):
    """
    Calibre adapter for DRC and LVS physical verification.

    Sub-stages:
      - drc: Design Rule Check
      - lvs: Layout vs Schematic
    """
    tool_name = "Calibre"
    stage = FlowStage.PV_DRC  # default
    env_script = "/share/apps/EDAs/mg.bash"

    def __init__(self, state: DesignState, sub_stage: str = "drc"):
        super().__init__(state)
        self.sub_stage = sub_stage
        if sub_stage == "lvs":
            self.stage = FlowStage.PV_LVS
        else:
            self.stage = FlowStage.PV_DRC

    def _get_shell_cmd(self) -> str:
        if self.sub_stage == "drc":
            return "calibre -drc -hier"
        elif self.sub_stage == "lvs":
            return "calibre -lvs -hier"
        return "calibre -batch"

    def setup_work_dir(self, stage_name: str | None = None) -> Path:
        name = stage_name or f"calibre_{self.sub_stage}"
        root = super().setup_work_dir(name)
        # Remove stale Calibre result files so each run starts clean.
        for stale in [
            "DRC_RES.db", "drc_results.db", "drc_summary.rpt",
            "LVS_RES.db", "lvs_results.db", "lvs_report.rpt",
        ]:
            (root / stale).unlink(missing_ok=True)
        for stale in ["out", "rpt", "svdb"]:
            for f in (root / stale).glob("*"):
                try:
                    if f.is_file():
                        f.unlink()
                    elif f.is_dir():
                        import shutil
                        shutil.rmtree(f)
                except OSError:
                    pass
        return root

    def generate_script(self) -> str:
        if self.sub_stage == "drc":
            return self._gen_drc_deck()
        elif self.sub_stage == "lvs":
            return self._gen_lvs_deck()
        raise ValueError(f"Unknown Calibre sub-stage: {self.sub_stage}")

    def parse_results(self) -> None:
        result = self.state.get_stage_result(self.stage)
        if self.work_dir is None:
            return

        if self.sub_stage == "drc":
            self._parse_drc_results(result)
        elif self.sub_stage == "lvs":
            self._parse_lvs_results(result)

    # ----------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------

    def _resolve_artifact_path(self, path: str) -> Path:
        """Resolve an artifact path, interpreting relative paths against work_root."""
        return paths.resolve_artifact_path(path, self.state.work_root)

    def _resolve_gds(self) -> str:
        """Resolve routed GDS file, preferring uncompressed but accepting .gz."""
        return str(paths.resolve_routed_gds(
            self.state.config.design_name,
            work_root=self.state.work_root,
            artifacts=self.state.artifacts,
        ).resolve())

    def _resolve_netlist(self) -> str:
        """Resolve routed Verilog netlist for LVS."""
        return str(paths.resolve_routed_netlist(
            self.state.config.design_name,
            work_root=self.state.work_root,
            artifacts=self.state.artifacts,
        ).resolve())

    def _resolve_def(self) -> Path | None:
        """Return the routed DEF file path, if available."""
        return paths.resolve_routed_def(
            self.state.config.design_name,
            work_root=self.state.work_root,
            artifacts=self.state.artifacts,
        )

    def _generate_port_labels_from_def(self, port_names: set[str]) -> Path | None:
        """Build a Calibre LAYOUT TEXT label file from the DEF routing/pins.

        Delegates to the reusable ``port_labels`` utility.
        """
        def_file = self._resolve_def()
        if not def_file:
            return None
        labels = port_labels.generate_port_labels_from_def(
            def_file,
            port_names,
            std_gds=self._std_cell_gds(),
        )
        if not labels:
            return None
        out_file = self.work_dir / "port_labels.txt" if self.work_dir else Path("port_labels.txt")
        return port_labels.write_port_labels(labels, out_file)

    def _std_cell_gds(self) -> str:
        """Return configured standard-cell GDS library path, if any."""
        gds = getattr(self.state.config.pdk, "std_cell_gds", "")
        return str(Path(gds).resolve()) if gds else ""

    def _std_cell_spice(self) -> str:
        """Return configured standard-cell SPICE library path, if any."""
        spice = getattr(self.state.config.pdk, "std_cell_spice", "")
        return str(Path(spice).resolve()) if spice else ""

    def _run_calibredrv(self, args: list[str], cwd: Path | None = None) -> None:
        """Run calibredrv with the Mentor environment loaded."""
        gds.run_calibredrv(args, env_script=self.resolved_env_script, cwd=cwd or self.work_dir)

    def _merge_std_cell_gds(self, design_gds: str, output_path: Path) -> str:
        """Merge the routed design GDS with the standard-cell GDS library."""
        std_cell_gds = self._std_cell_gds()
        if not std_cell_gds or not Path(std_cell_gds).exists():
            return design_gds
        cell_map = gds.build_cell_name_map(
            gds.list_gds_undefined_cells(design_gds, env_script=self.resolved_env_script),
            gds.list_gds_cells(std_cell_gds, env_script=self.resolved_env_script),
        )
        merged = gds.merge_gds(
            design_gds, std_cell_gds, output_path,
            cell_map=cell_map or None,
            env_script=self.resolved_env_script,
            work_dir=self.work_dir,
        )
        return str(merged)

    def _convert_verilog_to_spice(self, verilog_file: str, output_path: Path) -> str:
        """Convert the Verilog netlist to a SPICE netlist with v2lvs."""
        std_spice = self._std_cell_spice()
        if not std_spice or not Path(std_spice).exists():
            return verilog_file
        out = netlist.verilog_to_spice(
            verilog_file,
            std_spice,
            output_path,
            power_nets=getattr(self.state.config.pdk, "power_nets", ["VDD"]),
            ground_nets=getattr(self.state.config.pdk, "ground_nets", ["VSS"]),
            env_script=self.resolved_env_script,
            work_dir=self.work_dir,
        )
        return str(out)

    def _prepare_external_deck(self, original_deck: str, for_lvs: bool = False) -> str:
        """Copy external rule deck, substitute placeholders, and remove duplicated specs."""
        import shutil

        original_path = Path(original_deck)
        local = self.work_dir / original_path.name
        src_text = original_path.read_text()

        # For LVS, copy relative INCLUDE dependencies (e.g. ./DFM) so the copied
        # deck still resolves its sub-includes.
        if for_lvs:
            for match in re.finditer(r'^INCLUDE\s+"?(\.\/\S+)"?', src_text, re.MULTILINE | re.IGNORECASE):
                rel_ref = match.group(1)
                src_ref = original_path.parent / rel_ref
                dst_ref = self.work_dir / rel_ref
                if src_ref.exists() and not dst_ref.exists():
                    dst_ref.parent.mkdir(parents=True, exist_ok=True)
                    if src_ref.is_dir():
                        shutil.copytree(src_ref, dst_ref)
                    else:
                        shutil.copy2(src_ref, dst_ref)

        # Statements that the wrapper deck sets explicitly.
        wrapper_specs = [
            "LAYOUT SYSTEM", "LAYOUT PATH", "LAYOUT PRIMARY",
            "SOURCE SYSTEM", "SOURCE PATH", "SOURCE PRIMARY",
        ]
        if for_lvs:
            wrapper_specs.extend([
                "LVS REPORT", "LVS POWER NAME", "LVS GROUND NAME",
                "MASK SVDB DIRECTORY",
            ])

        lines_out = []
        for line in src_text.splitlines():
            stripped = line.strip()
            # Remove literal placeholder lines; the wrapper deck sets these.
            if stripped.startswith('LAYOUT PATH "GDSFILENAME"') or stripped.startswith('LAYOUT PRIMARY "TOPCELLNAME"'):
                continue
            if stripped.startswith('SOURCE PATH "NETLISTFILENAME"') or stripped.startswith('SOURCE PRIMARY "TOPCELLNAME"'):
                continue
            # Drop layout/source/report specs that would conflict with the wrapper.
            if any(stripped.startswith(spec) for spec in wrapper_specs):
                continue
            line = line.replace('"GDSFILENAME"', f'"{self._resolve_gds()}"')
            line = line.replace('"TOPCELLNAME"', f'"{self.state.config.top_module}"')
            lines_out.append(line)
        local.write_text("\n".join(lines_out))
        return str(local.resolve())

    # ----------------------------------------------------------------
    # Rule Deck Generators
    # ----------------------------------------------------------------

    def _gen_drc_deck(self) -> str:
        cfg = self.state.config
        gds_file = self._resolve_gds()
        std_gds = self._std_cell_gds()
        if std_gds and Path(std_gds).exists():
            merged_path = self.work_dir / f"{cfg.design_name}_merged.gds" if self.work_dir else Path(tempfile.gettempdir()) / f"{cfg.design_name}_merged.gds"
            gds_file = self._merge_std_cell_gds(gds_file, merged_path)

        rule_deck = cfg.pdk.calibre_drc_runset or cfg.pdk.tech_file
        uses_external_runset = bool(cfg.pdk.calibre_drc_runset)

        lines = [
            f"// Calibre DRC Rule Deck",
            f"// Design: {cfg.design_name}",
            f"// Auto-generated by IC Backend Framework",
            "",
        ]
        if uses_external_runset:
            local_deck = self._prepare_external_deck(rule_deck, for_lvs=False)
            lines.extend([
                f"LAYOUT SYSTEM GDSII",
                f"LAYOUT PATH \"{gds_file}\"",
                f"LAYOUT PRIMARY {cfg.top_module}",
                "",
                f"// Include PDK DRC rules",
                f'INCLUDE "{local_deck}"',
                "",
            ])
        else:
            lines.extend([
                f"PRECISION 1000",
                f"LAYOUT PATH \"{gds_file}\"",
                f"LAYOUT PRIMARY {cfg.top_module}",
                f"LAYOUT SYSTEM GDSII",
                f"DRC RESULTS DATABASE ./out/drc_results.db",
                f"DRC MAXIMUM RESULTS ALL",
                f"DRC MAXIMUM VERTEX 4096",
                f"DRC CELL NAME YES",
                f"DRC SUMMARY REPORT ./rpt/drc_summary.rpt",
                "",
                f"// Include PDK DRC rules",
                f'INCLUDE "{rule_deck}"',
                "",
            ])
        return "\n".join(lines)

    def _top_level_ports_from_spice(self, spice_file: str) -> list[str]:
        """Return the ordered pin list from the top-level .subckt line."""
        try:
            text = Path(spice_file).read_text(errors="ignore")
        except OSError:
            return []
        # Match .subckt TOP pins ... ; continuation lines start with '+'.
        pattern = re.compile(
            r'^\.SUBCKT\s+' + re.escape(self.state.config.top_module) + r'\b'
            r'((?:\s+[^\n]+(?:\n\+[^\n]+)*)?)',
            re.IGNORECASE | re.MULTILINE,
        )
        m = pattern.search(text)
        if not m:
            return []
        pin_text = m.group(1).replace('\n+', ' ')
        return pin_text.split()

    def _port_labels_file(self, required_ports: set[str] | None = None) -> Path | None:
        """Return the path to the ICC2-generated port-label file, if available."""
        work_root = Path(self.state.work_root) if self.state.work_root else Path.cwd()
        candidates = [
            self.state.get_artifact("icc2_finish_port_labels"),
            work_root / "finish" / "out" / "port_labels.txt",
            work_root / "out" / "port_labels.txt",
        ]
        for c in candidates:
            if not c:
                continue
            p = self._resolve_artifact_path(str(c))
            if p.exists():
                if required_ports is None:
                    return p
                found = {line.split()[0] for line in p.read_text(errors="ignore").splitlines() if line.strip()}
                if required_ports.issubset(found):
                    return p
        return None

    def _gen_lvs_deck(self) -> str:
        cfg = self.state.config
        gds_file = self._resolve_gds()
        std_gds = self._std_cell_gds()
        if std_gds and Path(std_gds).exists():
            merged_path = self.work_dir / f"{cfg.design_name}_merged.gds" if self.work_dir else Path(tempfile.gettempdir()) / f"{cfg.design_name}_merged.gds"
            gds_file = self._merge_std_cell_gds(gds_file, merged_path)

        netlist_file = self._resolve_netlist()
        std_spice = self._std_cell_spice()
        if std_spice and Path(std_spice).exists():
            spice_path = self.work_dir / "netlist_lvs.spice" if self.work_dir else Path(tempfile.gettempdir()) / "netlist_lvs.spice"
            netlist_file = self._convert_verilog_to_spice(netlist_file, spice_path)

        rule_deck = cfg.pdk.calibre_lvs_runset or cfg.pdk.tech_file
        uses_external_runset = bool(cfg.pdk.calibre_lvs_runset)

        power = getattr(cfg.pdk, "power_nets", ["VDD"])
        ground = getattr(cfg.pdk, "ground_nets", ["VSS"])
        power_names = " ".join(power)
        ground_names = " ".join(ground)

        lines = [
            f"// Calibre LVS Rule Deck",
            f"// Design: {cfg.design_name}",
            f"// Auto-generated by IC Backend Framework",
            "",
        ]
        if uses_external_runset:
            deck_text = Path(rule_deck).read_text(errors="ignore")
            # Common TSMC DRC-only decks have a plaintext header like "CALIBRE DRC COMMAND FILE".
            # A DRC-only runset cannot be reused for LVS (even if it contains some DRC ERC output).
            if "DRC COMMAND FILE" in deck_text:
                raise ValueError(
                    f"The configured Calibre LVS runset '{rule_deck}' appears to be a DRC-only deck. "
                    "LVS requires a separate PDK LVS rule deck (with DEVICE/CONNECT/LVS statements)."
                )
            local_deck = self._prepare_external_deck(rule_deck, for_lvs=True)
            lines.extend([
                f"LAYOUT SYSTEM GDSII",
                f"LAYOUT PATH \"{gds_file}\"",
                f"LAYOUT PRIMARY {cfg.top_module}",
                f"SOURCE PATH \"{netlist_file}\"",
                f"SOURCE PRIMARY {cfg.top_module}",
                f"SOURCE SYSTEM SPICE",
                "",
            ])

            # Annotate top-level ports generated by the APR stage.  The ICC2 finish
            # script writes port name / GDS text layer / x / y to port_labels.txt.
            # If that file is missing or incomplete, derive labels from the DEF.
            port_names = set(self._top_level_ports_from_spice(netlist_file))
            port_label_file = self._port_labels_file(required_ports=port_names)
            if not port_label_file and port_names:
                port_label_file = self._generate_port_labels_from_def(port_names)
            if port_label_file and port_label_file.exists():
                lines.extend([
                    "// Annotate top-level ports for LVS",
                ])
                for pline in port_label_file.read_text(errors="ignore").splitlines():
                    parts = pline.split()
                    if len(parts) >= 4:
                        pname, ptext_layer, px, py = parts[0], parts[1], parts[2], parts[3]
                        if pname in port_names:
                            # Calibre LAYOUT TEXT syntax: "text" x y layer
                            lines.append(f'LAYOUT TEXT "{pname}" {px} {py} {ptext_layer}')
                lines.append("")

            lines.extend([
                f"LVS REPORT \"./rpt/lvs_report.rpt\"",
                f"MASK SVDB DIRECTORY \"./out/svdb\" QUERY",
                f"LVS POWER NAME {power_names}",
                f"LVS GROUND NAME {ground_names}",
                "",
                f"// Include PDK LVS rules",
                f'INCLUDE "{local_deck}"',
                "",
            ])
        else:
            lines.extend([
                f"PRECISION 1000",
                f"",
                f"LAYOUT PATH \"{gds_file}\"",
                f"LAYOUT PRIMARY {cfg.top_module}",
                f"LAYOUT SYSTEM GDSII",
                f"",
                f"SOURCE PATH \"{netlist_file}\"",
                f"SOURCE PRIMARY {cfg.top_module}",
                f"SOURCE SYSTEM SPICE",
                f"",
                f"LVS REPORT ./rpt/lvs_report.rpt",
                f"MASK SVDB DIRECTORY ./out/svdb QUERY",
                f"LVS POWER NAME {power_names}",
                f"LVS GROUND NAME {ground_names}",
                f"LVS COMPARE PROPERTY",
                f"LVS DEVICE PROPERTY",
                f"LVS ABUTMENT BOX YES",
                f"LVS EXECUTE ERC",
                f"LVS REPORT MAXIMUM 1000",
                f"LVS ABORT ON SUPPLY ERROR YES",
                f"LVS FILTER UNUSED OPTION YES",
                f"LVS FILTER UNUSED DEVICE NO",
                "",
                f"// Include PDK LVS rules",
                f'INCLUDE "{rule_deck}"',
                "",
            ])
        return "\n".join(lines)

    # ----------------------------------------------------------------
    # Result Parsers
    # ----------------------------------------------------------------

    def _parse_drc_results(self, result: StageResult):
        """Parse Calibre DRC results."""
        # Calibre's external PDK runsets usually write DRC.rep / DRC_RES.db;
        # the internal fallback writes drc_summary.rpt / drc_results.db.
        report_candidates = [
            "rpt/DRC.rep",
            "rpt/drc_summary.rpt",
            "DRC.rep",
            "drc_summary.rpt",
        ]
        db_candidates = [
            "rpt/DRC_RES.db",
            "rpt/drc_results.db",
            "DRC_RES.db",
            "drc_results.db",
        ]

        # Try summary report(s)
        for report_name in report_candidates:
            report_file = self.work_dir / report_name
            if not report_file.exists():
                continue
            text = report_file.read_text(errors="ignore")

            # Total DRC Results Generated: <unique> (<total>)
            m = re.search(r'TOTAL DRC Results Generated:\s*(\d+)', text, re.IGNORECASE)
            if m and result.drc.total_errors is None:
                result.drc.total_errors = int(m.group(1))
                result.drc.is_clean = result.drc.total_errors == 0

            # Legacy / internal summary format
            m = re.search(r'Total DRC Errors\.?\s*:\s*(\d+)', text, re.IGNORECASE)
            if m and result.drc.total_errors is None:
                result.drc.total_errors = int(m.group(1))
                result.drc.is_clean = result.drc.total_errors == 0

            # Per-rule result counts
            for match in re.finditer(
                r'RULECHECK\s+(\S+)\s+\.\.\.\.\.\.\.+\s*TOTAL Result Count\s*=\s*(\d+)',
                text,
            ):
                rule_name = match.group(1)
                count = int(match.group(2))
                if count:
                    result.drc.errors_by_type[rule_name] = count

            for match in re.finditer(r'(\w+\.\d+)\s*:\s*(\d+)', text):
                rule_name = match.group(1)
                count = int(match.group(2))
                if count:
                    result.drc.errors_by_type[rule_name] = count

        # Also check results database(s)
        for db_name in db_candidates:
            results_db = self.work_dir / db_name
            if results_db.exists() and result.drc.total_errors is None:
                text = results_db.read_text(errors="ignore")
                error_count = len(re.findall(r'^\s*DRC ERROR', text, re.MULTILINE))
                if error_count > 0:
                    result.drc.total_errors = error_count
                    result.drc.is_clean = False
                else:
                    result.drc.is_clean = True

        # If we still have no numeric result, scan the tool log for fatal errors.
        if result.drc.total_errors is None:
            log_file = self.work_dir / "log" / "run.log"
            if log_file.exists():
                text = log_file.read_text(errors="ignore")
                # Count Calibre ERROR lines (ignore benign warnings).
                error_lines = [ln for ln in text.splitlines() if re.search(r'^ERROR:', ln)]
                if error_lines:
                    result.drc.total_errors = len(error_lines)
                    result.drc.is_clean = False
                    result.status = StageStatus.FAILED
                    for ln in error_lines[:10]:
                        result.messages.append(ln.strip())

        # Record artifacts
        for name in report_candidates + db_candidates:
            fpath = self.work_dir / name
            if fpath.exists():
                self.state.record_artifact(f"drc_{name.replace('.', '_')}", str(fpath))
                result.output_files[name] = str(fpath)

    def _parse_lvs_results(self, result: StageResult):
        """Parse Calibre LVS results."""
        report_candidates = [
            "rpt/lvs_report.rpt",
            "rpt/LVS.rep",
            "lvs_report.rpt",
            "LVS.rep",
        ]
        report_file = None
        for name in report_candidates:
            candidate = self.work_dir / name
            if candidate.exists():
                report_file = candidate
                break

        if report_file:
            text = report_file.read_text(errors="ignore")

            # Check for correct comparison
            if re.search(r'\bCORRECT\b', text, re.IGNORECASE):
                result.lvs.is_clean = True
                result.lvs.num_errors = 0
                result.messages.append("LVS comparison: CORRECT")
            elif re.search(r'\bINCORRECT\b', text, re.IGNORECASE):
                result.lvs.is_clean = False
                result.messages.append("LVS comparison: INCORRECT")
            elif re.search(r'\bNOT\s+COMPARED\b', text, re.IGNORECASE):
                result.lvs.is_clean = False
                result.messages.append("LVS could not compare layout and source")

            # Port / net count summary in the detailed top-level section, e.g.:
            #   Ports:              0        25    *
            #   Nets:             131       104    *
            m = re.search(
                r'^\s*Ports:\s*(\d+)\s+(\d+)\s*\*?\s*$',
                text,
                re.MULTILINE | re.IGNORECASE,
            )
            if m:
                layout_ports, source_ports = int(m.group(1)), int(m.group(2))
                if layout_ports != source_ports:
                    result.messages.append(
                        f"LVS port count mismatch: layout={layout_ports}, source={source_ports}"
                    )
                    result.lvs.num_mismatches = result.lvs.num_mismatches or 0
                    result.lvs.num_mismatches += abs(layout_ports - source_ports)

            m = re.search(
                r'^\s*Nets:\s*(\d+)\s+(\d+)\s*\*?\s*$',
                text,
                re.MULTILINE | re.IGNORECASE,
            )
            if m:
                layout_nets, source_nets = int(m.group(1)), int(m.group(2))
                if layout_nets != source_nets:
                    result.messages.append(
                        f"LVS net count mismatch: layout={layout_nets}, source={source_nets}"
                    )
                    result.lvs.num_mismatches = result.lvs.num_mismatches or 0
                    result.lvs.num_mismatches += abs(layout_nets - source_nets)

            # ERC errors (from the ERC section, if present)
            m = re.search(r'Total ERC Errors\.?\s*:\s*(\d+)', text, re.IGNORECASE)
            if m:
                result.lvs.num_errors = int(m.group(1))

        # If no report and the log has fatal errors, mark FAILED.
        if report_file is None:
            log_file = self.work_dir / "log" / "run.log"
            if log_file.exists():
                text = log_file.read_text(errors="ignore")
                error_lines = [ln for ln in text.splitlines() if re.search(r'^ERROR:', ln)]
                if error_lines:
                    result.status = StageStatus.FAILED
                    result.lvs.is_clean = False
                    for ln in error_lines[:10]:
                        result.messages.append(ln.strip())

        # Record artifacts
        for name in report_candidates + ["lvs_results.db", "LVS_RES.db"]:
            fpath = self.work_dir / name
            if fpath.exists():
                self.state.record_artifact(f"lvs_{name.replace('.', '_')}", str(fpath))
                result.output_files[name] = str(fpath)
        svdb_dir = self.work_dir / "out" / "svdb"
        if svdb_dir.exists():
            self.state.record_artifact("lvs_svdb_dir", str(svdb_dir))
            result.output_files["svdb"] = str(svdb_dir)
