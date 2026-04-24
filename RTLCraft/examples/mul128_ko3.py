#!/usr/bin/env python3
"""
128x128 位整数乘法器（KO3 算法 + 3 级流水线）

- 128-bit 零填充到 144-bit (3 x 48-bit)
- 每 48-bit 再用 KO3 分解为 3 x 16-bit
- 底层用 16x16 组合乘法器
- 共 36 个 Mul16x16（KO3 两级）vs 朴素 64 个，节省 ~44%
"""

import sys
sys.path.insert(0, "..")

from rtlgen import Module, Input, Output, Reg, Wire, Vector, VerilogEmitter
from rtlgen.logic import Cat, Const, If, Else, PadLeft, Split, comment


# =====================================================================
# 底层: 16x16 无符号乘法器
# =====================================================================
class Mul16x16(Module):
    def __init__(self, name: str = "Mul16x16"):
        super().__init__(name)
        self.a = Input(16, "a")
        self.b = Input(16, "b")
        self.prod = Output(32, "prod")

        @self.comb
        def _logic():
            comment("16x16 unsigned multiplier (combinational)")
            self.prod <<= self.a * self.b


# =====================================================================
# 中层: 48x48 无符号乘法器（KO3 -> 6x Mul16x16）
# =====================================================================
class Mul48x48(Module):
    def __init__(self, name: str = "Mul48x48"):
        super().__init__(name)
        self.a = Input(48, "a")
        self.b = Input(48, "b")
        self.prod = Output(96, "prod")

        @self.comb
        def _logic():
            comment("48x48 multiplier using KO3 -> 6x Mul16x16")
            a_parts = Split(self.a, 16)   # [a0, a1, a2]
            b_parts = Split(self.b, 16)   # [b0, b1, b2]
            a0, a1, a2 = a_parts
            b0, b1, b2 = b_parts

            comment("Cross-segment sums")
            s01 = Wire(17, "s01"); s01 <<= a0 + a1
            s02 = Wire(17, "s02"); s02 <<= a0 + a2
            s12 = Wire(17, "s12"); s12 <<= a1 + a2
            t01 = Wire(17, "t01"); t01 <<= b0 + b1
            t02 = Wire(17, "t02"); t02 <<= b0 + b2
            t12 = Wire(17, "t12"); t12 <<= b1 + b2

            comment("6 parallel 16x16 multiplications")
            mul_prods = {}
            for x, y, suffix in [
                (a0, b0, "p0"), (a1, b1, "p1"), (a2, b2, "p2"),
                (s01, t01, "p01"), (s02, t02, "p02"), (s12, t12, "p12"),
            ]:
                mul = Mul16x16("Mul16x16")
                p = Wire(32, f"mul_{suffix}")
                self.instantiate(mul, f"u_mul_{suffix}", port_map={
                    "a": x, "b": y, "prod": p
                })
                mul_prods[suffix] = p

            p0  = mul_prods["p0"]
            p1  = mul_prods["p1"]
            p2  = mul_prods["p2"]
            p01 = mul_prods["p01"]
            p02 = mul_prods["p02"]
            p12 = mul_prods["p12"]

            comment("KO3 partial product combination")
            self.prod <<= (
                Cat(p2, Const(0, 64))
                + Cat((p12 - p2 - p1), Const(0, 48))
                + Cat((p02 - p2 - p0 + p1), Const(0, 32))
                + Cat((p01 - p1 - p0), Const(0, 16))
                + p0
            )


# =====================================================================
# 顶层: 128x128 无符号乘法器（3 级流水线）
# =====================================================================
class Mul128x128(Module):
    def __init__(self):
        super().__init__("Mul128x128")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.a = Input(128, "a")
        self.b = Input(128, "b")
        self.valid_in = Input(1, "valid_in")
        self.ready_out = Output(1, "ready_out")
        self.prod = Output(256, "prod")
        self.valid_out = Output(1, "valid_out")
        self.ready_in = Input(1, "ready_in")

        # -----------------------------------------------------------------
        # 级间 ready 线（提前声明，seq 块会引用）
        # -----------------------------------------------------------------
        self.s1_ready = Wire(1, "s1_ready")
        self.s2_ready = Wire(1, "s2_ready")

        # -----------------------------------------------------------------
        # Stage 0: 分段与加法
        # -----------------------------------------------------------------
        comment("Stage 0: split 128-bit to 3x48-bit segments and compute cross sums")
        self.A_w = Vector(48, 3, "s0_A", vtype=Wire)
        self.B_w = Vector(48, 3, "s0_B", vtype=Wire)
        self.SA_w = Vector(49, 3, "s0_SA", vtype=Wire)
        self.SB_w = Vector(49, 3, "s0_SB", vtype=Wire)

        @self.comb
        def _s0_comb():
            a_ext = PadLeft(self.a, 144)
            b_ext = PadLeft(self.b, 144)
            parts_a = Split(a_ext, 48)
            parts_b = Split(b_ext, 48)
            for i in range(3):
                self.A_w[i] <<= parts_a[i]
                self.B_w[i] <<= parts_b[i]
            for i in range(3):
                self.SA_w[i] <<= self.A_w[i] + self.A_w[(i + 1) % 3]
                self.SB_w[i] <<= self.B_w[i] + self.B_w[(i + 1) % 3]

        # S0 -> S1 寄存器
        self.s1_valid = Reg(1, "s1_valid")
        self.A_r = Vector(48, 3, "s1_A", vtype=Reg)
        self.B_r = Vector(48, 3, "s1_B", vtype=Reg)
        self.SA_r = Vector(49, 3, "s1_SA", vtype=Reg)
        self.SB_r = Vector(49, 3, "s1_SB", vtype=Reg)

        @self.seq(self.clk, self.rst)
        def _s0_seq():
            with If(self.rst == 1):
                self.s1_valid <<= 0
            with Else():
                with If(self.valid_in & self.ready_out):
                    self.s1_valid <<= 1
                    for i in range(3):
                        self.A_r[i] <<= self.A_w[i]
                        self.B_r[i] <<= self.B_w[i]
                        self.SA_r[i] <<= self.SA_w[i]
                        self.SB_r[i] <<= self.SB_w[i]
                with Else():
                    with If(self.s1_ready):
                        self.s1_valid <<= 0

        # -----------------------------------------------------------------
        # Stage 1: 6 个 Mul48x48 并行
        # -----------------------------------------------------------------
        comment("Stage 1: 6 parallel Mul48x48")
        mul48_ports = [
            (self.A_r[0], self.B_r[0], "P0"),
            (self.A_r[1], self.B_r[1], "P1"),
            (self.A_r[2], self.B_r[2], "P2"),
            (self.SA_r[0], self.SB_r[0], "S01"),
            (self.SA_r[1], self.SB_r[1], "S02"),
            (self.SA_r[2], self.SB_r[2], "S12"),
        ]
        self.mul48_prods = {}
        for a_sig, b_sig, suffix in mul48_ports:
            mul = Mul48x48("Mul48x48")
            p = Wire(96, f"mul48_{suffix}")
            self.instantiate(mul, f"u_mul48_{suffix}", port_map={
                "a": a_sig, "b": b_sig, "prod": p
            })
            self.mul48_prods[suffix] = p

        # S1 -> S2 寄存器
        self.s2_valid = Reg(1, "s2_valid")
        self.s2_P = {k: Reg(96, f"s2_{k}") for k in self.mul48_prods}

        @self.seq(self.clk, self.rst)
        def _s1_seq():
            with If(self.rst == 1):
                self.s2_valid <<= 0
            with Else():
                with If(self.s1_valid & self.s1_ready):
                    self.s2_valid <<= 1
                    for k, v in self.mul48_prods.items():
                        self.s2_P[k] <<= v
                with Else():
                    with If(self.s2_ready):
                        self.s2_valid <<= 0

        # -----------------------------------------------------------------
        # Stage 2: KO3 组合输出
        # -----------------------------------------------------------------
        comment("Stage 2: combine 6 partial products with KO3 to 256-bit result")
        P0 = self.s2_P["P0"]
        P1 = self.s2_P["P1"]
        P2 = self.s2_P["P2"]
        S01 = self.s2_P["S01"]
        S02 = self.s2_P["S02"]
        S12 = self.s2_P["S12"]

        @self.comb
        def _s2_comb():
            part4 = Cat(P2, Const(0, 192))
            part3 = Cat((S12 - P2 - P1), Const(0, 144))
            part2 = Cat((S02 - P2 - P0 + P1), Const(0, 96))
            part1 = Cat((S01 - P1 - P0), Const(0, 48))
            part0 = P0
            self.prod <<= (part4 + part3 + part2 + part1 + part0)[255:0]
            self.valid_out <<= self.s2_valid

        # 握手
        @self.comb
        def _handshake():
            comment("Pipeline handshake: ready backpropagation")
            self.s2_ready <<= self.ready_in
            self.s1_ready <<= (~self.s2_valid) | self.s2_ready
            self.ready_out <<= (~self.s1_valid) | self.s1_ready


if __name__ == "__main__":
    top = Mul128x128()
    emitter = VerilogEmitter()
    print(emitter.emit_design(top))
