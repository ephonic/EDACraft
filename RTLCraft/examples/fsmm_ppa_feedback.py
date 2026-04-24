#!/usr/bin/env python3
"""
FSMM full PPA feedback loop demo.

Flow:
    RTL (FSMM) -> BLIF -> ABC synthesis -> mapped Verilog
    -> Netlist parse -> LEF -> Placement -> Global Routing -> Detailed Routing
    -> RC extraction -> RTL feedback -> AST modifications
"""

import os
import sys
import tempfile

sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import BLIFEmitter, ABCSynthesizer, WireLoadModel, PPAAnalyzer
from rtlgen.lef import generate_demo_lef, parse_lef
from rtlgen.liberty import generate_sizing_demo_liberty, parse_liberty
from rtlgen.netlist import parse_mapped_verilog, parse_mapped_blif, annotate_net_directions
from rtlgen.placement import AnalyticalPlacer
from rtlgen.routing import GlobalRouter, DetailedRouter
from rtlgen.rcextract import DetailedRCExtractor, RTLFeedbackEngine
from rtlgen.codegen import VerilogEmitter
from examples.fsmm import FSMM


def build_lef_lib(tmpdir: str):
    lef_path = os.path.join(tmpdir, "demo.lef")
    lib_path = os.path.join(tmpdir, "demo.lib")
    generate_demo_lef(lef_path)
    generate_sizing_demo_liberty(lib_path)
    return parse_lef(lef_path), parse_liberty(lib_path)


def main():
    dut = FSMM(Q=16, DW=8)

    # ------------------------------------------------------------------
    # 0. Pre-loop PPA analysis (static)
    # ------------------------------------------------------------------
    ppa = PPAAnalyzer(dut)
    static = ppa.analyze_static()
    print("=" * 60)
    print("Pre-synthesis Static PPA")
    print("=" * 60)
    print(f"Logic depth : {max(static['logic_depth'].values()) if static['logic_depth'] else 0}")
    print(f"Gate estimate: {static['gate_count']:.1f} NAND2-equiv")
    print(f"Reg bits    : {static['reg_bits']}")
    print(f"Fanout report top-3: {sorted(static['fanout_report'].items(), key=lambda x: x[1], reverse=True)[:3]}")
    suggestions = ppa.suggest_optimizations(static)
    for s in suggestions:
        print(f"  * {s}")

    with tempfile.TemporaryDirectory() as tmpdir:
        # --------------------------------------------------------------
        # 1. Synthesis
        # --------------------------------------------------------------
        blif_path = os.path.join(tmpdir, "fsmm.blif")
        lib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "gf65.lib")
        mapped_blif = os.path.join(tmpdir, "fsmm_mapped.blif")

        blif = BLIFEmitter().emit(dut)
        with open(blif_path, "w") as f:
            f.write(blif)

        abc_path = os.path.expanduser("~/.local/bin/abc")
        synth = ABCSynthesizer(abc_path=abc_path)
        if not synth.is_available():
            print(f"WARNING: ABC not found at {abc_path}, skipping synthesis.")
            return

        result = synth.run(
            input_blif=blif_path,
            liberty=lib_path if os.path.exists(lib_path) else None,
            output_blif=mapped_blif,
            cwd=tmpdir,
        )
        print("\nSynthesis result:")
        print(f"  Area : {result.area}")
        print(f"  Delay: {result.delay}")
        print(f"  Gates: {result.gates}")
        print(f"  Depth: {result.depth}")

        # --------------------------------------------------------------
        # 2. Netlist parse (from BLIF to avoid ABC write_verilog segfault)
        # --------------------------------------------------------------
        print("Parsing mapped BLIF...")
        with open(mapped_blif, "r") as f:
            blif_text = f.read()
        nl = parse_mapped_blif(blif_text)

        lef, lib = build_lef_lib(tmpdir)
        annotate_net_directions(nl, lib)

        # --------------------------------------------------------------
        # 3. Placement
        # --------------------------------------------------------------
        print("Running placement...")
        placer = AnalyticalPlacer(nl, lef)
        placement = placer.place(target_utilization=0.4)
        print(f"\nPlacement: die {placement.width:.2f} x {placement.height:.2f}, HPWL={placement.hpwl:.2f}")

        # --------------------------------------------------------------
        # 4. Routing
        # --------------------------------------------------------------
        print("Running routing...")
        cell_widths = {}
        cell_heights = {}
        for cname, cell in nl.cells.items():
            macro = lef.macros.get(cell.cell_type)
            if macro:
                cell_widths[cname] = macro.size[0]
                cell_heights[cname] = macro.size[1]
            else:
                cell_widths[cname] = 1.0
                cell_heights[cname] = 1.0

        grouter = GlobalRouter(nl, placement, cell_widths, cell_heights, grid_cols=32, grid_rows=32)
        global_routes = grouter.route()
        print(f"Global routing: {len(global_routes.global_routes)} nets routed")

        drouter = DetailedRouter(nl, placement, global_routes, cell_widths, cell_heights)
        detailed_routes = drouter.route()
        print(f"Detailed routing: {len(detailed_routes.detailed_routes)} nets routed")

        # --------------------------------------------------------------
        # 5. RC extraction
        # --------------------------------------------------------------
        print("Running RC extraction...")
        rc_extractor = DetailedRCExtractor(nl, detailed_routes)
        rc_result = rc_extractor.extract()
        print(f"\nRC extraction:")
        print(f"  Total WL: {rc_result.total_wirelength:.2f} um")
        print(f"  Total R : {rc_result.total_res:.2f} ohm")
        print(f"  Total C : {rc_result.total_cap:.2f} fF")

        # Top-5 critical nets
        top_nets = sorted(rc_result.nets.values(), key=lambda n: n.elmore_delay, reverse=True)[:5]
        for n in top_nets:
            print(f"  Net {n.net_name}: WL={n.wirelength:.2f} um, Elmore={n.elmore_delay:.2f} ps, Fanout={n.fanout}")

        # --------------------------------------------------------------
        # 6. RTL feedback
        # --------------------------------------------------------------
        print("Running RTL feedback...")
        feedback = RTLFeedbackEngine(nl, rc_result)
        report = feedback.analyze()
        print(f"\nRTL Feedback: {report.summary}")
        for item in report.items:
            print(f"[{item.severity.upper()}] {item.net_name}: {item.suggestion}")

        # --------------------------------------------------------------
        # 7. Apply feedback to AST
        # --------------------------------------------------------------
        print("\nApplying RTL feedback to Module AST...")
        modified = False
        for item in report.items:
            if item.severity == "critical" and "fanout splitting" in item.suggestion.lower():
                # Example: duplicate high-fanout net (simplified heuristic)
                print(f"  -> Would duplicate net {item.net_name}")
                modified = True
            elif "pipeline insertion" in item.suggestion.lower():
                print(f"  -> Would insert pipeline stage for net {item.net_name}")
                modified = True

        if modified:
            # Re-emit for visual confirmation
            emitter = VerilogEmitter()
            new_verilog = emitter.emit(dut)
            out_v = os.path.join(tmpdir, "fsmm_optimized.v")
            with open(out_v, "w") as f:
                f.write(new_verilog)
            print(f"\nOptimized Verilog written to {out_v}")
        else:
            print("\nNo critical feedback items to apply automatically.")


if __name__ == "__main__":
    main()
