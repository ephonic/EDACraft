#!/usr/bin/env python3
"""
Placement + Fast RC Extraction Demo.

演示从 mapped Verilog → LEF → Analytical Placement → Fast RC 的完整链路。
"""
import sys
sys.path.insert(0, "..")

from rtlgen.lef import generate_demo_lef, parse_lef
from rtlgen.liberty import generate_sizing_demo_liberty, parse_liberty
from rtlgen.netlist import parse_mapped_verilog, annotate_net_directions
from rtlgen.placement import AnalyticalPlacer
from rtlgen.rc import FastRCExtractor


def main():
    # ------------------------------------------------------------------
    # 1. Create a small structural netlist (simulating ABC output)
    # ------------------------------------------------------------------
    verilog = """
module chain (a, b, c, d, y);
  input a, b, c, d;
  output y;
  wire n1, n2, n3;
  NAND2X1 g0(.A(a), .B(b), .Y(n1));
  INVX1   g1(.A(n1), .Y(n2));
  NOR2X1  g2(.A(c), .B(n2), .Y(n3));
  INVX1   g3(.A(n3), .Y(y));
endmodule
"""
    generate_sizing_demo_liberty("/tmp/sizing_demo.lib")
    lib = parse_liberty("/tmp/sizing_demo.lib")

    nl = parse_mapped_verilog(verilog)
    annotate_net_directions(nl, lib)

    # ------------------------------------------------------------------
    # 2. Generate / parse demo LEF
    # ------------------------------------------------------------------
    generate_demo_lef("/tmp/demo.lef")
    lef = parse_lef("/tmp/demo.lef")
    print("LEF macros:", list(lef.macros.keys()))
    print("LEF layers:", list(lef.layers.keys()))

    # ------------------------------------------------------------------
    # 3. Analytical Placement
    # ------------------------------------------------------------------
    placer = AnalyticalPlacer(nl, lef)
    result = placer.place()

    print("\n--- Placement Result ---")
    print(f"Die size: {result.width:.2f} x {result.height:.2f}")
    print(f"HPWL: {result.hpwl:.2f}")
    for cell, (x, y) in result.positions.items():
        print(f"  {cell:<6} @ ({x:.2f}, {y:.2f})")

    # ------------------------------------------------------------------
    # 4. Fast RC Extraction
    # ------------------------------------------------------------------
    extractor = FastRCExtractor(nl, lef, result)
    rc = extractor.extract()

    print("\n--- RC Extraction Result ---")
    print(f"Total R: {rc.total_res:.3f} ohm, Total C: {rc.total_cap:.3f} fF")
    for name, nrc in rc.nets.items():
        print(
            f"  {name:<10} R={nrc.resistance:.3f} ohm, C={nrc.capacitance:.3f} fF, "
            f"Elmore={nrc.elmore_delay*1e3:.4f} ps"
        )


if __name__ == "__main__":
    main()
