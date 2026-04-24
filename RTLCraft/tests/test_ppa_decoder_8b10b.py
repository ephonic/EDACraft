#!/usr/bin/env python3
"""
PPAAnalyzer demonstration for the 8b10b Decoder.

Runs static + dynamic analysis and prints a human-readable report.
"""

import sys

sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Simulator, PPAAnalyzer
from examples.decoder_8b10b import Decoder8b10b


def main():
    dut = Decoder8b10b()
    ppa = PPAAnalyzer(dut)

    # Static analysis (no simulation needed)
    static = ppa.analyze_static()
    print("=" * 60)
    print(f"Static PPA Analysis for {dut.name}")
    print("=" * 60)
    print(f"Max logic depth      : {max(static['logic_depth'].values()) if static['logic_depth'] else 0}")
    print(f"Gate estimate        : {static['gate_count']:.1f} NAND2-equiv")
    print(f"Register bits        : {static['reg_bits']}")
    print(f"Case branches        : {static['mux_complexity']['total_cases']}")
    print(f"Max case width       : {static['mux_complexity']['max_case_width']}")
    print(f"Dead signals         : {static['dead_signals']}")

    # Show top-5 deepest paths
    depths = static['logic_depth']
    if depths:
        print("\nTop-5 deepest combinational paths:")
        for sig, d in sorted(depths.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {sig:20s} depth={d}")

    # Show top-5 highest fanout
    fanout = static['fanout_report']
    if fanout:
        print("\nTop-5 highest fanout signals:")
        for sig, f in sorted(fanout.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {sig:20s} fanout={f}")

    # Suggestions
    suggestions = ppa.suggest_optimizations(static)
    if suggestions:
        print("\n[Optimization Suggestions]")
        for s in suggestions:
            print(f"  • {s}")

    # Dynamic analysis: run a quick simulation to collect toggle rates
    sim = Simulator(dut, trace_signals=list(dut._inputs.keys()) + list(dut._outputs.keys()) +
                                    list(dut._wires.keys()) + list(dut._regs.keys()))

    # Drive some patterns to generate activity
    sim.set("reset_in", 1)
    sim.set("clk_in", 0)
    sim.step()
    sim.set("clk_in", 1)
    sim.step()
    sim.set("reset_in", 0)

    # Feed a mix of control and data symbols
    patterns = [
        (0b001111_0100, 1),   # K.28.0
        (0b110000_1011, 1),   # K.28.0
        (0b100111_0100, 0),   # data
        (0b011000_1011, 0),   # data
        (0b111000_1110, 0),   # data
    ]
    for pat, ctrl in patterns:
        sim.set("decoder_in", pat)
        sim.set("control_in", ctrl)
        sim.set("decoder_valid_in", 1)
        sim.set("clk_in", 0)
        sim.step()
        sim.set("clk_in", 1)
        sim.step()

    dyn = ppa.analyze_dynamic(sim)
    toggles = dyn["toggle_rates"]
    if toggles:
        avg = sum(toggles.values()) / len(toggles)
        max_sig = max(toggles, key=toggles.get)
        print(f"\nDynamic Analysis (over {len(sim.trace)-1} cycles)")
        print(f"  Avg toggle rate : {avg:.2%}/cycle")
        print(f"  Hottest signal  : {max_sig} ({toggles[max_sig]:.2%}/cycle)")

    # Full report
    print("\n" + ppa.report(sim))


if __name__ == "__main__":
    main()
