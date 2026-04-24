#!/usr/bin/env python3
"""
标准组件库扩展示例：BarrelShifter / LFSR / CRC / Divider。
"""

import sys
sys.path.insert(0, "..")

from rtlgen import (
    BarrelShifter, LFSR, CRC, Divider,
    VerilogEmitter, Simulator,
)


if __name__ == "__main__":
    print("=" * 60)
    print("1. BarrelShifter (left rotate)")
    print("=" * 60)
    shifter = BarrelShifter(width=8, direction="left_rotate")
    print(VerilogEmitter().emit(shifter))

    print("=" * 60)
    print("2. LFSR (16-bit, taps=[16,14,13,11])")
    print("=" * 60)
    lfsr = LFSR(width=16, taps=[16, 14, 13, 11], seed=0xACE1)
    print(VerilogEmitter().emit(lfsr))

    # 仿真 LFSR
    sim = Simulator(lfsr, trace_signals=["out", "enable"])
    sim.reset()
    sim.set("enable", 1)
    for _ in range(5):
        sim.step()
    print("LFSR trace (first 5 cycles after reset):")
    sim.dump_trace(fmt="table")
    print()

    print("=" * 60)
    print("3. CRC-8 (poly=0x07)")
    print("=" * 60)
    crc = CRC(data_width=8, poly_width=8, polynomial=0x07)
    print(VerilogEmitter().emit(crc))

    print("=" * 60)
    print("4. Divider (8/8)")
    print("=" * 60)
    div = Divider(dividend_width=8, divisor_width=8)
    print(VerilogEmitter().emit(div))

    # 仿真 Divider
    sim_div = Simulator(div, trace_signals=["quotient", "remainder", "done", "busy"])
    sim_div.reset()
    sim_div.set("dividend", 100)
    sim_div.set("divisor", 7)
    sim_div.set("start", 1)
    sim_div.step()
    sim_div.set("start", 0)
    while sim_div.get("done") == 0 and len(sim_div.trace) < 20:
        sim_div.step()
    print(f"Divider result: 100 / 7 = {sim_div.get('quotient')} rem {sim_div.get('remainder')}")
    sim_div.dump_trace(fmt="table")
