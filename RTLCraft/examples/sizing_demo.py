#!/usr/bin/env python3
"""
Gate Sizing Demo — 完整链路：RTL → BLIF → ABC → Python-native sizing.

本示例演示：
1. 用 RTLCraft 设计一个 4 级逻辑链
2. 生成 BLIF 并调用 ABC 做逻辑综合与工艺映射
3. 用 Python-native GateSizer 对映射后的网表进行二次 sizing 优化
4. 输出优化前后的面积/延迟/Slack 对比报告

运行:
    PYTHONPATH=.. python sizing_demo.py
"""
import sys
sys.path.insert(0, "..")

from rtlgen import Module, Input, Output, Wire
from rtlgen.blifgen import BLIFEmitter
from rtlgen.liberty import generate_sizing_demo_liberty, parse_liberty
from rtlgen.netlist import parse_mapped_verilog, annotate_net_directions
from rtlgen.sizing import GateSizer
from rtlgen.synth import ABCSynthesizer


class LogicChain(Module):
    """Deep combinational chain for sizing demonstration."""

    def __init__(self):
        super().__init__("logic_chain")
        self.a = Input(1, "a")
        self.b = Input(1, "b")
        self.c = Input(1, "c")
        self.d = Input(1, "d")
        self.y = Output(1, "y")

        self.n1 = Wire(1, "n1")
        self.n2 = Wire(1, "n2")
        self.n3 = Wire(1, "n3")

        @self.comb
        def _logic():
            self.n1 <<= self.a & self.b
            self.n2 <<= ~self.n1 | self.c
            self.n3 <<= self.n2 & self.d
            self.y <<= ~self.n3


def main():
    # ------------------------------------------------------------------
    # 1. Generate a demo Liberty with drive-strength variants
    # ------------------------------------------------------------------
    generate_sizing_demo_liberty("/tmp/sizing_demo.lib")
    lib = parse_liberty("/tmp/sizing_demo.lib")
    print("Available cells:", list(lib.cells.keys()))

    # ------------------------------------------------------------------
    # 2. RTL → BLIF
    # ------------------------------------------------------------------
    top = LogicChain()
    blif_text = BLIFEmitter().emit(top)
    with open("/tmp/logic_chain.blif", "w") as f:
        f.write(blif_text)

    # ------------------------------------------------------------------
    # 3. ABC synthesis
    # ------------------------------------------------------------------
    abc = ABCSynthesizer(abc_path="/Users/yangfan/.local/bin/abc")
    abc_res = abc.run(
        "/tmp/logic_chain.blif",
        liberty="/tmp/sizing_demo.lib",
        output_verilog="/tmp/logic_chain_abc.v",
    )
    print("\n--- ABC Synthesis Result ---")
    print(f"Area: {abc_res.area:.3f}, Delay: {abc_res.delay:.4f} ns, Gates: {abc_res.gates}, Depth: {abc_res.depth}")

    # ------------------------------------------------------------------
    # 4. Python-native Gate Sizing
    # ------------------------------------------------------------------
    nl = parse_mapped_verilog(abc_res.mapped_verilog)
    annotate_net_directions(nl, lib)

    sizer = GateSizer(nl, lib)
    sizing_res = sizer.optimize(target_delay=0.30)

    print("\n--- Python-native Sizing Result ---")
    print(sizing_res.report)

    # ------------------------------------------------------------------
    # 5. Write sized Verilog
    # ------------------------------------------------------------------
    with open("/tmp/logic_chain_sized.v", "w") as f:
        f.write(sizing_res.sized_verilog)
    print("\nSized Verilog written to /tmp/logic_chain_sized.v")


if __name__ == "__main__":
    main()
