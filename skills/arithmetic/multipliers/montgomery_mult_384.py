#!/usr/bin/env python3
"""
384-bit Fully Pipelined Montgomery Modular Multiplier
with complete Karatsuba-Ofman decomposition tree:
  384 -> 128 (KO-3)
  128 -> 64  (KO-2)
  64  -> 32  (KO-2)
  32  -> 16  (KO-2)
Leaf: 16x16 combinational multipliers.
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Wire, Reg, Vector, VerilogEmitter
from rtlgen.logic import Cat, Const, If, Else, Mux, PadLeft, Rep, Split
from rtlgen.pipeline import ShiftReg


def _sign_ext(signal, target_width):
    """Sign-extend signal to target_width bits."""
    if signal.width >= target_width:
        return signal
    msb = signal[signal.width - 1]
    return Cat(Rep(msb, target_width - signal.width), signal)


# =====================================================================
# Leaf combinational multipliers
# =====================================================================
class Mul16x16(Module):
    def __init__(self, name: str = "Mul16x16"):
        super().__init__(name)
        self.a = Input(16, "a")
        self.b = Input(16, "b")
        self.prod = Output(32, "prod")
        @self.comb
        def _logic():
            self.prod <<= self.a * self.b

class Mul17x17(Module):
    def __init__(self, name: str = "Mul17x17"):
        super().__init__(name)
        self.a = Input(17, "a")
        self.b = Input(17, "b")
        self.prod = Output(34, "prod")
        @self.comb
        def _logic():
            self.prod <<= self.a * self.b

class Mul18x18(Module):
    def __init__(self, name: str = "Mul18x18"):
        super().__init__(name)
        self.a = Input(18, "a")
        self.b = Input(18, "b")
        self.prod = Output(36, "prod")
        @self.comb
        def _logic():
            self.prod <<= self.a * self.b

class Mul34x34(Module):
    """Combinational 34x34 multiplier (used as cross term in Mul65x65)."""
    def __init__(self, name: str = "Mul34x34"):
        super().__init__(name)
        self.a = Input(34, "a")
        self.b = Input(34, "b")
        self.prod = Output(68, "prod")
        @self.comb
        def _logic():
            self.prod <<= self.a * self.b

# =====================================================================
# 32x32 KO-2 Pipeline (latency = 2 cycles)
# =====================================================================
class Mul32x32Pipe(Module):
    def __init__(self, name: str = "Mul32x32Pipe"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.a = Input(32, "a")
        self.b = Input(32, "b")
        self.valid_in = Input(1, "valid_in")
        self.ready_out = Output(1, "ready_out")
        self.prod = Output(64, "prod")
        self.valid_out = Output(1, "valid_out")
        self.ready_in = Input(1, "ready_in")

        self.s1_ready = Wire(1, "s1_ready")

        # S0: input reg + cross sums
        self.s0_s = Wire(17, "s0_s")
        self.s0_t = Wire(17, "s0_t")
        @self.comb
        def _s0_comb():
            self.s0_s <<= PadLeft(self.a[15:0], 17) + PadLeft(self.a[31:16], 17)
            self.s0_t <<= PadLeft(self.b[15:0], 17) + PadLeft(self.b[31:16], 17)

        self.s1_valid = Reg(1, "s1_valid")
        self.s1_a0 = Reg(16, "s1_a0")
        self.s1_a1 = Reg(16, "s1_a1")
        self.s1_b0 = Reg(16, "s1_b0")
        self.s1_b1 = Reg(16, "s1_b1")
        self.s1_s = Reg(17, "s1_s")
        self.s1_t = Reg(17, "s1_t")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _s0_seq():
            with If(self.rst_n == 0):
                self.s1_valid <<= 0
            with Else():
                with If(self.ready_out):
                    self.s1_valid <<= self.valid_in
                    with If(self.valid_in):
                        self.s1_a0 <<= self.a[15:0]
                        self.s1_a1 <<= self.a[31:16]
                        self.s1_b0 <<= self.b[15:0]
                        self.s1_b1 <<= self.b[31:16]
                        self.s1_s <<= self.s0_s
                        self.s1_t <<= self.s0_t

        # S1: leaf multipliers (combinational)
        self.p0 = Wire(32, "p0")
        self.p1 = Wire(32, "p1")
        self.p01 = Wire(34, "p01")
        self.instantiate(Mul16x16("u_p0"), "u_p0",
            port_map={"a": self.s1_a0, "b": self.s1_b0, "prod": self.p0})
        self.instantiate(Mul16x16("u_p1"), "u_p1",
            port_map={"a": self.s1_a1, "b": self.s1_b1, "prod": self.p1})
        self.instantiate(Mul17x17("u_p01"), "u_p01",
            port_map={"a": self.s1_s, "b": self.s1_t, "prod": self.p01})

        self.out_valid = Reg(1, "out_valid")
        self.out_prod = Reg(64, "out_prod")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _s1_seq():
            with If(self.rst_n == 0):
                self.out_valid <<= 0
            with Else():
                with If(self.s1_ready):
                    self.out_valid <<= self.s1_valid
                    with If(self.s1_valid):
                        part2 = Cat(self.p1, Const(0, 32))
                        part1 = Cat((self.p01 - self.p1 - self.p0), Const(0, 16))
                        part0 = self.p0
                        self.out_prod <<= (part2 + part1 + part0)[63:0]

        @self.comb
        def _out_comb():
            self.prod <<= self.out_prod
            self.valid_out <<= self.out_valid

        @self.comb
        def _handshake():
            self.s1_ready <<= (~self.out_valid) | self.ready_in
            self.ready_out <<= (~self.s1_valid) | self.s1_ready

# =====================================================================
# 33x33 KO-2 Pipeline (latency = 2 cycles)
# a = a1(17b)*2^16 + a0(16b)
# =====================================================================
class Mul33x33Pipe(Module):
    def __init__(self, name: str = "Mul33x33Pipe"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.a = Input(33, "a")
        self.b = Input(33, "b")
        self.valid_in = Input(1, "valid_in")
        self.ready_out = Output(1, "ready_out")
        self.prod = Output(66, "prod")
        self.valid_out = Output(1, "valid_out")
        self.ready_in = Input(1, "ready_in")

        self.s1_ready = Wire(1, "s1_ready")

        self.s0_s = Wire(18, "s0_s")
        self.s0_t = Wire(18, "s0_t")
        @self.comb
        def _s0_comb():
            self.s0_s <<= PadLeft(self.a[15:0], 18) + PadLeft(self.a[32:16], 18)
            self.s0_t <<= PadLeft(self.b[15:0], 18) + PadLeft(self.b[32:16], 18)

        self.s1_valid = Reg(1, "s1_valid")
        self.s1_a0 = Reg(16, "s1_a0")
        self.s1_a1 = Reg(17, "s1_a1")
        self.s1_b0 = Reg(16, "s1_b0")
        self.s1_b1 = Reg(17, "s1_b1")
        self.s1_s = Reg(18, "s1_s")
        self.s1_t = Reg(18, "s1_t")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _s0_seq():
            with If(self.rst_n == 0):
                self.s1_valid <<= 0
            with Else():
                with If(self.ready_out):
                    self.s1_valid <<= self.valid_in
                    with If(self.valid_in):
                        self.s1_a0 <<= self.a[15:0]
                        self.s1_a1 <<= self.a[32:16]
                        self.s1_b0 <<= self.b[15:0]
                        self.s1_b1 <<= self.b[32:16]
                        self.s1_s <<= self.s0_s
                        self.s1_t <<= self.s0_t

        self.p0 = Wire(32, "p0")
        self.p1 = Wire(34, "p1")
        self.p01 = Wire(36, "p01")
        self.instantiate(Mul16x16("u_p0"), "u_p0",
            port_map={"a": self.s1_a0, "b": self.s1_b0, "prod": self.p0})
        self.instantiate(Mul17x17("u_p1"), "u_p1",
            port_map={"a": self.s1_a1, "b": self.s1_b1, "prod": self.p1})
        self.instantiate(Mul18x18("u_p01"), "u_p01",
            port_map={"a": self.s1_s, "b": self.s1_t, "prod": self.p01})

        self.out_valid = Reg(1, "out_valid")
        self.out_prod = Reg(66, "out_prod")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _s1_seq():
            with If(self.rst_n == 0):
                self.out_valid <<= 0
            with Else():
                with If(self.s1_ready):
                    self.out_valid <<= self.s1_valid
                    with If(self.s1_valid):
                        part2 = Cat(self.p1, Const(0, 32))
                        part1 = Cat((self.p01 - self.p1 - self.p0), Const(0, 16))
                        part0 = self.p0
                        self.out_prod <<= (part2 + part1 + part0)[65:0]

        @self.comb
        def _out_comb():
            self.prod <<= self.out_prod
            self.valid_out <<= self.out_valid

        @self.comb
        def _handshake():
            self.s1_ready <<= (~self.out_valid) | self.ready_in
            self.ready_out <<= (~self.s1_valid) | self.s1_ready

# =====================================================================
# 64x64 KO-2 Pipeline (latency = 4 cycles)
# =====================================================================
class Mul64x64Pipe(Module):
    def __init__(self, name: str = "Mul64x64Pipe"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.a = Input(64, "a")
        self.b = Input(64, "b")
        self.valid_in = Input(1, "valid_in")
        self.ready_out = Output(1, "ready_out")
        self.prod = Output(128, "prod")
        self.valid_out = Output(1, "valid_out")
        self.ready_in = Input(1, "ready_in")

        self.s1_ready = Wire(1, "s1_ready")

        # S0: input reg + cross sums
        self.s0_s = Wire(33, "s0_s")
        self.s0_t = Wire(33, "s0_t")
        @self.comb
        def _s0_comb():
            self.s0_s <<= PadLeft(self.a[31:0], 33) + PadLeft(self.a[63:32], 33)
            self.s0_t <<= PadLeft(self.b[31:0], 33) + PadLeft(self.b[63:32], 33)

        self.s1_valid = Reg(1, "s1_valid")
        self.s1_a0 = Reg(32, "s1_a0")
        self.s1_a1 = Reg(32, "s1_a1")
        self.s1_b0 = Reg(32, "s1_b0")
        self.s1_b1 = Reg(32, "s1_b1")
        self.s1_s = Reg(33, "s1_s")
        self.s1_t = Reg(33, "s1_t")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _s0_seq():
            with If(self.rst_n == 0):
                self.s1_valid <<= 0
            with Else():
                with If(self.ready_out):
                    self.s1_valid <<= self.valid_in
                    with If(self.valid_in):
                        self.s1_a0 <<= self.a[31:0]
                        self.s1_a1 <<= self.a[63:32]
                        self.s1_b0 <<= self.b[31:0]
                        self.s1_b1 <<= self.b[63:32]
                        self.s1_s <<= self.s0_s
                        self.s1_t <<= self.s0_t

        # S1: sub-multipliers (2x pipelined + 1x combinational)
        self.p0 = Wire(64, "p0")
        self.p1 = Wire(64, "p1")
        self.p01 = Wire(68, "p01")

        self.u_p0 = Mul32x32Pipe("u_p0")
        self.u_p1 = Mul32x32Pipe("u_p1")
        self.instantiate(self.u_p0, "u_p0",
            port_map={
                "clk": self.clk, "rst_n": self.rst_n,
                "a": self.s1_a0, "b": self.s1_b0,
                "valid_in": self.s1_valid, "ready_out": Wire(1, "r0"),
                "prod": self.p0, "valid_out": Wire(1, "v0"), "ready_in": Const(1, 1)
            })
        self.instantiate(self.u_p1, "u_p1",
            port_map={
                "clk": self.clk, "rst_n": self.rst_n,
                "a": self.s1_a1, "b": self.s1_b1,
                "valid_in": self.s1_valid, "ready_out": Wire(1, "r1"),
                "prod": self.p1, "valid_out": Wire(1, "v1"), "ready_in": Const(1, 1)
            })

        # Delay s1_s/s1_t to align combinational cross-term with pipelined sub-products
        self.s1_s_d1 = Reg(33, "s1_s_d1")
        self.s1_s_d2 = Reg(33, "s1_s_d2")
        self.s1_t_d1 = Reg(33, "s1_t_d1")
        self.s1_t_d2 = Reg(33, "s1_t_d2")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _st_delay_seq():
            with If(self.rst_n == 0):
                self.s1_s_d1 <<= 0
                self.s1_s_d2 <<= 0
                self.s1_t_d1 <<= 0
                self.s1_t_d2 <<= 0
            with Else():
                self.s1_s_d1 <<= self.s1_s
                self.s1_s_d2 <<= self.s1_s_d1
                self.s1_t_d1 <<= self.s1_t
                self.s1_t_d2 <<= self.s1_t_d1

        self.instantiate(Mul34x34("u_p01"), "u_p01",
            port_map={"a": self.s1_s_d2, "b": self.s1_t_d2, "prod": self.p01})

        # Delay line to match child latency = 2
        self.s1_valid_d1 = Reg(1, "s1_valid_d1")
        self.s1_valid_d2 = Reg(1, "s1_valid_d2")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _delay_seq():
            with If(self.rst_n == 0):
                self.s1_valid_d1 <<= 0
                self.s1_valid_d2 <<= 0
            with Else():
                self.s1_valid_d1 <<= self.s1_valid
                self.s1_valid_d2 <<= self.s1_valid_d1

        self.out_valid = Reg(1, "out_valid")
        self.out_prod = Reg(128, "out_prod")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _s1_seq():
            with If(self.rst_n == 0):
                self.out_valid <<= 0
            with Else():
                with If(self.s1_ready):
                    self.out_valid <<= self.s1_valid_d2
                    with If(self.s1_valid_d2):
                        part2 = Cat(self.p1, Const(0, 64))
                        part1 = Cat((self.p01 - self.p1 - self.p0), Const(0, 32))
                        part0 = self.p0
                        self.out_prod <<= (part2 + part1 + part0)[127:0]

        @self.comb
        def _out_comb():
            self.prod <<= self.out_prod
            self.valid_out <<= self.out_valid

        @self.comb
        def _handshake():
            self.s1_ready <<= (~self.out_valid) | self.ready_in
            self.ready_out <<= (~self.s1_valid) | self.s1_ready

# =====================================================================
# 65x65 KO-2 Pipeline (latency = 4 cycles)
# =====================================================================
class Mul65x65Pipe(Module):
    def __init__(self, name: str = "Mul65x65Pipe"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.a = Input(65, "a")
        self.b = Input(65, "b")
        self.valid_in = Input(1, "valid_in")
        self.ready_out = Output(1, "ready_out")
        self.prod = Output(130, "prod")
        self.valid_out = Output(1, "valid_out")
        self.ready_in = Input(1, "ready_in")

        self.s1_ready = Wire(1, "s1_ready")

        self.s0_s = Wire(34, "s0_s")
        self.s0_t = Wire(34, "s0_t")
        @self.comb
        def _s0_comb():
            self.s0_s <<= PadLeft(self.a[31:0], 34) + PadLeft(self.a[64:32], 34)
            self.s0_t <<= PadLeft(self.b[31:0], 34) + PadLeft(self.b[64:32], 34)

        self.s1_valid = Reg(1, "s1_valid")
        self.s1_a0 = Reg(32, "s1_a0")
        self.s1_a1 = Reg(33, "s1_a1")
        self.s1_b0 = Reg(32, "s1_b0")
        self.s1_b1 = Reg(33, "s1_b1")
        self.s1_s = Reg(34, "s1_s")
        self.s1_t = Reg(34, "s1_t")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _s0_seq():
            with If(self.rst_n == 0):
                self.s1_valid <<= 0
            with Else():
                with If(self.ready_out):
                    self.s1_valid <<= self.valid_in
                    with If(self.valid_in):
                        self.s1_a0 <<= self.a[31:0]
                        self.s1_a1 <<= self.a[64:32]
                        self.s1_b0 <<= self.b[31:0]
                        self.s1_b1 <<= self.b[64:32]
                        self.s1_s <<= self.s0_s
                        self.s1_t <<= self.s0_t

        self.p0 = Wire(64, "p0")
        self.p1 = Wire(66, "p1")
        self.p01 = Wire(68, "p01")

        self.u_p0 = Mul32x32Pipe("u_p0")
        self.u_p1 = Mul33x33Pipe("u_p1")
        self.instantiate(self.u_p0, "u_p0",
            port_map={
                "clk": self.clk, "rst_n": self.rst_n,
                "a": self.s1_a0, "b": self.s1_b0,
                "valid_in": self.s1_valid, "ready_out": Wire(1, "r0"),
                "prod": self.p0, "valid_out": Wire(1, "v0"), "ready_in": Const(1, 1)
            })
        self.instantiate(self.u_p1, "u_p1",
            port_map={
                "clk": self.clk, "rst_n": self.rst_n,
                "a": self.s1_a1, "b": self.s1_b1,
                "valid_in": self.s1_valid, "ready_out": Wire(1, "r1"),
                "prod": self.p1, "valid_out": Wire(1, "v1"), "ready_in": Const(1, 1)
            })

        # Delay s1_s/s1_t to align combinational cross-term with pipelined sub-products
        self.s1_s_d1 = Reg(34, "s1_s_d1")
        self.s1_s_d2 = Reg(34, "s1_s_d2")
        self.s1_t_d1 = Reg(34, "s1_t_d1")
        self.s1_t_d2 = Reg(34, "s1_t_d2")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _st_delay_seq_65():
            with If(self.rst_n == 0):
                self.s1_s_d1 <<= 0
                self.s1_s_d2 <<= 0
                self.s1_t_d1 <<= 0
                self.s1_t_d2 <<= 0
            with Else():
                self.s1_s_d1 <<= self.s1_s
                self.s1_s_d2 <<= self.s1_s_d1
                self.s1_t_d1 <<= self.s1_t
                self.s1_t_d2 <<= self.s1_t_d1

        self.instantiate(Mul34x34("u_p01"), "u_p01",
            port_map={"a": self.s1_s_d2, "b": self.s1_t_d2, "prod": self.p01})

        self.s1_valid_d1 = Reg(1, "s1_valid_d1")
        self.s1_valid_d2 = Reg(1, "s1_valid_d2")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _delay_seq():
            with If(self.rst_n == 0):
                self.s1_valid_d1 <<= 0
                self.s1_valid_d2 <<= 0
            with Else():
                self.s1_valid_d1 <<= self.s1_valid
                self.s1_valid_d2 <<= self.s1_valid_d1

        self.out_valid = Reg(1, "out_valid")
        self.out_prod = Reg(130, "out_prod")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _s1_seq():
            with If(self.rst_n == 0):
                self.out_valid <<= 0
            with Else():
                with If(self.s1_ready):
                    self.out_valid <<= self.s1_valid_d2
                    with If(self.s1_valid_d2):
                        part2 = Cat(self.p1, Const(0, 64))
                        part1 = Cat((self.p01 - self.p1 - self.p0), Const(0, 32))
                        part0 = self.p0
                        self.out_prod <<= (part2 + part1 + part0)[129:0]

        @self.comb
        def _out_comb():
            self.prod <<= self.out_prod
            self.valid_out <<= self.out_valid

        @self.comb
        def _handshake():
            self.s1_ready <<= (~self.out_valid) | self.ready_in
            self.ready_out <<= (~self.s1_valid) | self.s1_ready

# =====================================================================
# 66x66 combinational multiplier (cross term for 129x129)
# =====================================================================
class Mul66x66(Module):
    def __init__(self, name: str = "Mul66x66"):
        super().__init__(name)
        self.a = Input(66, "a")
        self.b = Input(66, "b")
        self.prod = Output(132, "prod")
        @self.comb
        def _logic():
            self.prod <<= self.a * self.b

# =====================================================================
# 128x128 KO-2 Pipeline (latency = 6 cycles)
# =====================================================================
class Mul128x128Pipe(Module):
    def __init__(self, name: str = "Mul128x128Pipe"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.a = Input(128, "a")
        self.b = Input(128, "b")
        self.valid_in = Input(1, "valid_in")
        self.ready_out = Output(1, "ready_out")
        self.prod = Output(256, "prod")
        self.valid_out = Output(1, "valid_out")
        self.ready_in = Input(1, "ready_in")

        self.s1_ready = Wire(1, "s1_ready")

        # S0: input reg + cross sums
        self.s0_s = Wire(65, "s0_s")
        self.s0_t = Wire(65, "s0_t")
        @self.comb
        def _s0_comb():
            self.s0_s <<= PadLeft(self.a[63:0], 65) + PadLeft(self.a[127:64], 65)
            self.s0_t <<= PadLeft(self.b[63:0], 65) + PadLeft(self.b[127:64], 65)

        self.s1_valid = Reg(1, "s1_valid")
        self.s1_a0 = Reg(64, "s1_a0")
        self.s1_a1 = Reg(64, "s1_a1")
        self.s1_b0 = Reg(64, "s1_b0")
        self.s1_b1 = Reg(64, "s1_b1")
        self.s1_s = Reg(65, "s1_s")
        self.s1_t = Reg(65, "s1_t")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _s0_seq():
            with If(self.rst_n == 0):
                self.s1_valid <<= 0
            with Else():
                with If(self.ready_out):
                    self.s1_valid <<= self.valid_in
                    with If(self.valid_in):
                        self.s1_a0 <<= self.a[63:0]
                        self.s1_a1 <<= self.a[127:64]
                        self.s1_b0 <<= self.b[63:0]
                        self.s1_b1 <<= self.b[127:64]
                        self.s1_s <<= self.s0_s
                        self.s1_t <<= self.s0_t

        # S1: sub-multipliers (2x pipelined + 1x combinational)
        self.p0 = Wire(128, "p0")
        self.p1 = Wire(128, "p1")
        self.p01 = Wire(132, "p01")

        self.u_p0 = Mul64x64Pipe("u_p0")
        self.u_p1 = Mul64x64Pipe("u_p1")
        self.u_p01 = Mul65x65Pipe("u_p01")
        self.instantiate(self.u_p0, "u_p0",
            port_map={
                "clk": self.clk, "rst_n": self.rst_n,
                "a": self.s1_a0, "b": self.s1_b0,
                "valid_in": self.s1_valid, "ready_out": Wire(1, "r0"),
                "prod": self.p0, "valid_out": Wire(1, "v0"), "ready_in": Const(1, 1)
            })
        self.instantiate(self.u_p1, "u_p1",
            port_map={
                "clk": self.clk, "rst_n": self.rst_n,
                "a": self.s1_a1, "b": self.s1_b1,
                "valid_in": self.s1_valid, "ready_out": Wire(1, "r1"),
                "prod": self.p1, "valid_out": Wire(1, "v1"), "ready_in": Const(1, 1)
            })
        self.instantiate(self.u_p01, "u_p01",
            port_map={
                "clk": self.clk, "rst_n": self.rst_n,
                "a": self.s1_s, "b": self.s1_t,
                "valid_in": self.s1_valid, "ready_out": Wire(1, "r01"),
                "prod": self.p01, "valid_out": Wire(1, "v01"), "ready_in": Const(1, 1)
            })

        # Delay line to match child latency = 4
        self.s1_valid_d1 = Reg(1, "s1_valid_d1")
        self.s1_valid_d2 = Reg(1, "s1_valid_d2")
        self.s1_valid_d3 = Reg(1, "s1_valid_d3")
        self.s1_valid_d4 = Reg(1, "s1_valid_d4")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _delay_seq():
            with If(self.rst_n == 0):
                self.s1_valid_d1 <<= 0
                self.s1_valid_d2 <<= 0
                self.s1_valid_d3 <<= 0
                self.s1_valid_d4 <<= 0
            with Else():
                self.s1_valid_d1 <<= self.s1_valid
                self.s1_valid_d2 <<= self.s1_valid_d1
                self.s1_valid_d3 <<= self.s1_valid_d2
                self.s1_valid_d4 <<= self.s1_valid_d3

        self.out_valid = Reg(1, "out_valid")
        self.out_prod = Reg(256, "out_prod")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _s1_seq():
            with If(self.rst_n == 0):
                self.out_valid <<= 0
            with Else():
                with If(self.s1_ready):
                    self.out_valid <<= self.s1_valid_d4
                    with If(self.s1_valid_d4):
                        part2 = Cat(self.p1, Const(0, 128))
                        part1 = Cat((self.p01 - self.p1 - self.p0), Const(0, 64))
                        part0 = self.p0
                        self.out_prod <<= (part2 + part1 + part0)[255:0]

        @self.comb
        def _out_comb():
            self.prod <<= self.out_prod
            self.valid_out <<= self.out_valid

        @self.comb
        def _handshake():
            self.s1_ready <<= (~self.out_valid) | self.ready_in
            self.ready_out <<= (~self.s1_valid) | self.s1_ready

# =====================================================================
# 129x129 KO-2 Pipeline (latency = 6 cycles)
# =====================================================================
class Mul129x129Pipe(Module):
    def __init__(self, name: str = "Mul129x129Pipe"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.a = Input(129, "a")
        self.b = Input(129, "b")
        self.valid_in = Input(1, "valid_in")
        self.ready_out = Output(1, "ready_out")
        self.prod = Output(258, "prod")
        self.valid_out = Output(1, "valid_out")
        self.ready_in = Input(1, "ready_in")

        self.s1_ready = Wire(1, "s1_ready")

        self.s0_s = Wire(66, "s0_s")
        self.s0_t = Wire(66, "s0_t")
        @self.comb
        def _s0_comb():
            self.s0_s <<= PadLeft(self.a[63:0], 66) + PadLeft(self.a[128:64], 66)
            self.s0_t <<= PadLeft(self.b[63:0], 66) + PadLeft(self.b[128:64], 66)

        self.s1_valid = Reg(1, "s1_valid")
        self.s1_a0 = Reg(64, "s1_a0")
        self.s1_a1 = Reg(65, "s1_a1")
        self.s1_b0 = Reg(64, "s1_b0")
        self.s1_b1 = Reg(65, "s1_b1")
        self.s1_s = Reg(66, "s1_s")
        self.s1_t = Reg(66, "s1_t")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _s0_seq():
            with If(self.rst_n == 0):
                self.s1_valid <<= 0
            with Else():
                with If(self.ready_out):
                    self.s1_valid <<= self.valid_in
                    with If(self.valid_in):
                        self.s1_a0 <<= self.a[63:0]
                        self.s1_a1 <<= self.a[128:64]
                        self.s1_b0 <<= self.b[63:0]
                        self.s1_b1 <<= self.b[128:64]
                        self.s1_s <<= self.s0_s
                        self.s1_t <<= self.s0_t

        self.p0 = Wire(128, "p0")
        self.p1 = Wire(130, "p1")
        self.p01 = Wire(132, "p01")

        self.u_p0 = Mul64x64Pipe("u_p0")
        self.u_p1 = Mul65x65Pipe("u_p1")
        self.instantiate(self.u_p0, "u_p0",
            port_map={
                "clk": self.clk, "rst_n": self.rst_n,
                "a": self.s1_a0, "b": self.s1_b0,
                "valid_in": self.s1_valid, "ready_out": Wire(1, "r0"),
                "prod": self.p0, "valid_out": Wire(1, "v0"), "ready_in": Const(1, 1)
            })
        self.instantiate(self.u_p1, "u_p1",
            port_map={
                "clk": self.clk, "rst_n": self.rst_n,
                "a": self.s1_a1, "b": self.s1_b1,
                "valid_in": self.s1_valid, "ready_out": Wire(1, "r1"),
                "prod": self.p1, "valid_out": Wire(1, "v1"), "ready_in": Const(1, 1)
            })

        # Delay s1_s/s1_t to align combinational cross-term with pipelined sub-products (4 cycles)
        self.s1_s_d1 = Reg(66, "s1_s_d1")
        self.s1_s_d2 = Reg(66, "s1_s_d2")
        self.s1_s_d3 = Reg(66, "s1_s_d3")
        self.s1_s_d4 = Reg(66, "s1_s_d4")
        self.s1_t_d1 = Reg(66, "s1_t_d1")
        self.s1_t_d2 = Reg(66, "s1_t_d2")
        self.s1_t_d3 = Reg(66, "s1_t_d3")
        self.s1_t_d4 = Reg(66, "s1_t_d4")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _st_delay_seq_129():
            with If(self.rst_n == 0):
                self.s1_s_d1 <<= 0
                self.s1_s_d2 <<= 0
                self.s1_s_d3 <<= 0
                self.s1_s_d4 <<= 0
                self.s1_t_d1 <<= 0
                self.s1_t_d2 <<= 0
                self.s1_t_d3 <<= 0
                self.s1_t_d4 <<= 0
            with Else():
                self.s1_s_d1 <<= self.s1_s
                self.s1_s_d2 <<= self.s1_s_d1
                self.s1_s_d3 <<= self.s1_s_d2
                self.s1_s_d4 <<= self.s1_s_d3
                self.s1_t_d1 <<= self.s1_t
                self.s1_t_d2 <<= self.s1_t_d1
                self.s1_t_d3 <<= self.s1_t_d2
                self.s1_t_d4 <<= self.s1_t_d3

        self.instantiate(Mul66x66("u_p01"), "u_p01",
            port_map={"a": self.s1_s_d4, "b": self.s1_t_d4, "prod": self.p01})

        self.s1_valid_d1 = Reg(1, "s1_valid_d1")
        self.s1_valid_d2 = Reg(1, "s1_valid_d2")
        self.s1_valid_d3 = Reg(1, "s1_valid_d3")
        self.s1_valid_d4 = Reg(1, "s1_valid_d4")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _delay_seq():
            with If(self.rst_n == 0):
                self.s1_valid_d1 <<= 0
                self.s1_valid_d2 <<= 0
                self.s1_valid_d3 <<= 0
                self.s1_valid_d4 <<= 0
            with Else():
                self.s1_valid_d1 <<= self.s1_valid
                self.s1_valid_d2 <<= self.s1_valid_d1
                self.s1_valid_d3 <<= self.s1_valid_d2
                self.s1_valid_d4 <<= self.s1_valid_d3

        self.out_valid = Reg(1, "out_valid")
        self.out_prod = Reg(258, "out_prod")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _s1_seq():
            with If(self.rst_n == 0):
                self.out_valid <<= 0
            with Else():
                with If(self.s1_ready):
                    self.out_valid <<= self.s1_valid_d4
                    with If(self.s1_valid_d4):
                        part2 = Cat(self.p1, Const(0, 128))
                        part1 = Cat((self.p01 - self.p1 - self.p0), Const(0, 64))
                        part0 = self.p0
                        self.out_prod <<= (part2 + part1 + part0)[257:0]

        @self.comb
        def _out_comb():
            self.prod <<= self.out_prod
            self.valid_out <<= self.out_valid

        @self.comb
        def _handshake():
            self.s1_ready <<= (~self.out_valid) | self.ready_in
            self.ready_out <<= (~self.s1_valid) | self.s1_ready

# =====================================================================
# 128-bit LSB truncated multiplier (latency = 5 cycles)
# Wraps Mul128x128Pipe and slices lower 128 bits.
# =====================================================================
class LSBMult128Pipe(Module):
    def __init__(self, name: str = "LSBMult128Pipe"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.a = Input(128, "a")
        self.b = Input(128, "b")
        self.valid_in = Input(1, "valid_in")
        self.ready_out = Output(1, "ready_out")
        self.prod_lo = Output(128, "prod_lo")
        self.valid_out = Output(1, "valid_out")
        self.ready_in = Input(1, "ready_in")

        self.inner = Mul128x128Pipe("inner")
        self.inner_prod = Wire(256, "inner_prod")
        self.instantiate(self.inner, "u_inner",
            port_map={
                "clk": self.clk, "rst_n": self.rst_n,
                "a": self.a, "b": self.b,
                "valid_in": self.valid_in, "ready_out": self.ready_out,
                "prod": self.inner_prod, "valid_out": self.valid_out, "ready_in": self.ready_in
            })

        @self.comb
        def _logic():
            self.prod_lo <<= self.inner_prod[127:0]

# =====================================================================
# 128-bit MSB multiplier (wraps Mul128x128Pipe, latency = 6 cycles)
# =====================================================================
class MSBMult128(Module):
    def __init__(self, name: str = "MSBMult128"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.a = Input(128, "a")
        self.b = Input(128, "b")
        self.valid_in = Input(1, "valid_in")
        self.ready_out = Output(1, "ready_out")
        self.prod_msb = Output(144, "prod_msb")
        self.valid_out = Output(1, "valid_out")
        self.ready_in = Input(1, "ready_in")

        self.inner = Mul128x128Pipe("inner")
        self.inner_prod = Wire(256, "inner_prod")
        self.instantiate(self.inner, "u_inner",
            port_map={
                "clk": self.clk, "rst_n": self.rst_n,
                "a": self.a, "b": self.b,
                "valid_in": self.valid_in, "ready_out": self.ready_out,
                "prod": self.inner_prod, "valid_out": self.valid_out, "ready_in": self.ready_in
            })

        @self.comb
        def _logic():
            self.prod_msb <<= self.inner_prod[255:112]

# =====================================================================
# Top-level: 384-bit Montgomery Modular Multiplier
# =====================================================================
class MontgomeryMult384(Module):
    def __init__(self, name: str = "MontgomeryMult384"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.i_valid = Input(1, "i_valid")
        self.i_ready = Output(1, "i_ready")
        self.X = Input(384, "X")
        self.Y = Input(384, "Y")
        self.M = Input(384, "M")
        self.M_prime = Input(128, "M_prime")
        self.o_valid = Output(1, "o_valid")
        self.o_ready = Input(1, "o_ready")
        self.Z = Output(384, "Z")

        # ------------------------------------------------------------------
        # Stage 0: Input capture
        # ------------------------------------------------------------------
        self.s0_valid = Reg(1, "s0_valid")
        self.s0_X = Vector(128, 3, "s0_X", vtype=Reg)
        self.s0_Y = Vector(128, 3, "s0_Y", vtype=Reg)
        self.s0_M = Reg(384, "s0_M")
        self.s0_Mp = Reg(128, "s0_Mp")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _s0_seq():
            with If(self.rst_n == 0):
                self.s0_valid <<= 0
            with Else():
                with If(self.i_ready):
                    self.s0_valid <<= self.i_valid
                    with If(self.i_valid):
                        x_parts = Split(self.X, 128)
                        y_parts = Split(self.Y, 128)
                        for i in range(3):
                            self.s0_X[i] <<= x_parts[i]
                            self.s0_Y[i] <<= y_parts[i]
                        self.s0_M <<= self.M
                        self.s0_Mp <<= self.M_prime

        # Cross sums for KO-3 (computed combinatorially from S0 registers)
        self.s0_x01 = Wire(129, "s0_x01")
        self.s0_x02 = Wire(129, "s0_x02")
        self.s0_x12 = Wire(129, "s0_x12")
        self.s0_y01 = Wire(129, "s0_y01")
        self.s0_y02 = Wire(129, "s0_y02")
        self.s0_y12 = Wire(129, "s0_y12")

        @self.comb
        def _s0_comb():
            self.s0_x01 <<= PadLeft(self.s0_X[0], 129) + PadLeft(self.s0_X[1], 129)
            self.s0_x02 <<= PadLeft(self.s0_X[0], 129) + PadLeft(self.s0_X[2], 129)
            self.s0_x12 <<= PadLeft(self.s0_X[1], 129) + PadLeft(self.s0_X[2], 129)
            self.s0_y01 <<= PadLeft(self.s0_Y[0], 129) + PadLeft(self.s0_Y[1], 129)
            self.s0_y02 <<= PadLeft(self.s0_Y[0], 129) + PadLeft(self.s0_Y[2], 129)
            self.s0_y12 <<= PadLeft(self.s0_Y[1], 129) + PadLeft(self.s0_Y[2], 129)

        # ------------------------------------------------------------------
        # S1-S6: 9x parallel Mul128/129 pipes
        # ------------------------------------------------------------------
        self.p0 = Wire(256, "p0")
        self.p1 = Wire(256, "p1")
        self.p2 = Wire(256, "p2")
        self.p01 = Wire(258, "p01")
        self.p02 = Wire(258, "p02")
        self.p12 = Wire(258, "p12")

        # Pre-declare dummy wires to avoid implicit wire lint errors
        self.rp0 = Wire(1, "rp0")
        self.vp0 = Wire(1, "vp0")
        self.rp1 = Wire(1, "rp1")
        self.vp1 = Wire(1, "vp1")
        self.rp2 = Wire(1, "rp2")
        self.vp2 = Wire(1, "vp2")
        self.rp01 = Wire(1, "rp01")
        self.vp01 = Wire(1, "vp01")
        self.rp02 = Wire(1, "rp02")
        self.vp02 = Wire(1, "vp02")
        self.rp12 = Wire(1, "rp12")
        self.vp12 = Wire(1, "vp12")

        self.u_p0 = Mul128x128Pipe("u_p0")
        self.u_p1 = Mul128x128Pipe("u_p1")
        self.u_p2 = Mul128x128Pipe("u_p2")
        self.u_p01 = Mul129x129Pipe("u_p01")
        self.u_p02 = Mul129x129Pipe("u_p02")
        self.u_p12 = Mul129x129Pipe("u_p12")

        self.instantiate(self.u_p0, "u_p0",
            port_map={
                "clk": self.clk, "rst_n": self.rst_n,
                "a": self.s0_X[0], "b": self.s0_Y[0],
                "valid_in": self.s0_valid, "ready_out": self.rp0,
                "prod": self.p0, "valid_out": self.vp0, "ready_in": Const(1, 1)
            })
        self.instantiate(self.u_p1, "u_p1",
            port_map={
                "clk": self.clk, "rst_n": self.rst_n,
                "a": self.s0_X[1], "b": self.s0_Y[1],
                "valid_in": self.s0_valid, "ready_out": self.rp1,
                "prod": self.p1, "valid_out": self.vp1, "ready_in": Const(1, 1)
            })
        self.instantiate(self.u_p2, "u_p2",
            port_map={
                "clk": self.clk, "rst_n": self.rst_n,
                "a": self.s0_X[2], "b": self.s0_Y[2],
                "valid_in": self.s0_valid, "ready_out": self.rp2,
                "prod": self.p2, "valid_out": self.vp2, "ready_in": Const(1, 1)
            })
        self.instantiate(self.u_p01, "u_p01",
            port_map={
                "clk": self.clk, "rst_n": self.rst_n,
                "a": self.s0_x01, "b": self.s0_y01,
                "valid_in": self.s0_valid, "ready_out": self.rp01,
                "prod": self.p01, "valid_out": self.vp01, "ready_in": Const(1, 1)
            })
        self.instantiate(self.u_p02, "u_p02",
            port_map={
                "clk": self.clk, "rst_n": self.rst_n,
                "a": self.s0_x02, "b": self.s0_y02,
                "valid_in": self.s0_valid, "ready_out": self.rp02,
                "prod": self.p02, "valid_out": self.vp02, "ready_in": Const(1, 1)
            })
        self.instantiate(self.u_p12, "u_p12",
            port_map={
                "clk": self.clk, "rst_n": self.rst_n,
                "a": self.s0_x12, "b": self.s0_y12,
                "valid_in": self.s0_valid, "ready_out": self.rp12,
                "prod": self.p12, "valid_out": self.vp12, "ready_in": Const(1, 1)
            })

        # Delay lines for M and Mp to match Mul pipe latency = 6 cycles
        self.M_d = [Reg(384, f"M_d{i}") for i in range(6)]
        self.Mp_d = [Reg(128, f"Mp_d{i}") for i in range(6)]
        self.s0v_d = [Reg(1, f"s0v_d{i}") for i in range(6)]

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _delay_lines():
            with If(self.rst_n == 0):
                for i in range(6):
                    self.M_d[i] <<= 0
                    self.Mp_d[i] <<= 0
                    self.s0v_d[i] <<= 0
            with Else():
                # Shift registers (always shift to maintain alignment)
                for i in range(5, 0, -1):
                    self.M_d[i] <<= self.M_d[i - 1]
                    self.Mp_d[i] <<= self.Mp_d[i - 1]
                    self.s0v_d[i] <<= self.s0v_d[i - 1]
                self.M_d[0] <<= self.s0_M
                self.Mp_d[0] <<= self.s0_Mp
                self.s0v_d[0] <<= self.s0_valid

        # ------------------------------------------------------------------
        # S7: Capture Mul pipe outputs
        # ------------------------------------------------------------------
        self.s7_ready = Wire(1, "s7_ready")
        self.s7_valid = Reg(1, "s7_valid")
        self.s7_P0 = Reg(256, "s7_P0")
        self.s7_P1 = Reg(256, "s7_P1")
        self.s7_P2 = Reg(256, "s7_P2")
        self.s7_P01 = Reg(258, "s7_P01")
        self.s7_P02 = Reg(258, "s7_P02")
        self.s7_P12 = Reg(258, "s7_P12")
        self.s7_M = Reg(384, "s7_M")
        self.s7_Mp = Reg(128, "s7_Mp")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _s7_seq():
            with If(self.rst_n == 0):
                self.s7_valid <<= 0
            with Else():
                with If(self.s7_ready):
                    self.s7_valid <<= self.s0v_d[5]
                    with If(self.s0v_d[5]):
                        self.s7_P0 <<= self.p0
                        self.s7_P1 <<= self.p1
                        self.s7_P2 <<= self.p2
                        self.s7_P01 <<= self.p01
                        self.s7_P02 <<= self.p02
                        self.s7_P12 <<= self.p12
                        self.s7_M <<= self.M_d[5]
                        self.s7_Mp <<= self.Mp_d[5]

        # ------------------------------------------------------------------
        # S8: KO-3 combination -> Z0..Z4
        # ------------------------------------------------------------------
        self.s8_ready = Wire(1, "s8_ready")

        self.s8_Z0 = Wire(256, "s8_Z0")
        self.s8_Z1 = Wire(259, "s8_Z1")
        self.s8_Z2 = Wire(260, "s8_Z2")
        self.s8_Z3 = Wire(259, "s8_Z3")
        self.s8_Z4 = Wire(256, "s8_Z4")
        self.s8_M_words = Vector(128, 3, "s8_M_words", vtype=Wire)

        @self.comb
        def _s8_comb():
            m_parts = Split(self.s7_M, 128)
            for i in range(3):
                self.s8_M_words[i] <<= m_parts[i]
            self.s8_Z0 <<= self.s7_P0
            self.s8_Z1 <<= self.s7_P01 - self.s7_P0 - self.s7_P1
            self.s8_Z2 <<= PadLeft(self.s7_P02, 260) - PadLeft(self.s7_P0, 260) - PadLeft(self.s7_P2, 260) + PadLeft(self.s7_P1, 260)
            self.s8_Z3 <<= PadLeft(self.s7_P12, 259) - PadLeft(self.s7_P1, 259) - PadLeft(self.s7_P2, 259)
            self.s8_Z4 <<= self.s7_P2

        self.s8_valid = Reg(1, "s8_valid")
        self.s8_Z0_r = Reg(256, "s8_Z0_r")
        self.s8_Z1_r = Reg(259, "s8_Z1_r")
        self.s8_Z2_r = Reg(260, "s8_Z2_r")
        self.s8_Z3_r = Reg(259, "s8_Z3_r")
        self.s8_Z4_r = Reg(256, "s8_Z4_r")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _s8_seq():
            with If(self.rst_n == 0):
                self.s8_valid <<= 0
            with Else():
                with If(self.s8_ready):
                    self.s8_valid <<= self.s7_valid
                    with If(self.s7_valid):
                        self.s8_Z0_r <<= self.s8_Z0
                        self.s8_Z1_r <<= self.s8_Z1
                        self.s8_Z2_r <<= self.s8_Z2
                        self.s8_Z3_r <<= self.s8_Z3
                        self.s8_Z4_r <<= self.s8_Z4

        # M pipeline: s7_M -> r0 -> r1 -> r2
        # Each stage is a 16-deep shift register (matches RedUnit128 latency)
        self.s8_M_shift = [Reg(384, f"s8_M_shift_{i}") for i in range(16)]
        self.s8_Mp_shift = [Reg(128, f"s8_Mp_shift_{i}") for i in range(16)]

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _s8_M_shift_seq():
            with If(self.rst_n == 0):
                for i in range(16):
                    self.s8_M_shift[i] <<= 0
                    self.s8_Mp_shift[i] <<= 0
            with Else():
                for i in range(15, 0, -1):
                    self.s8_M_shift[i] <<= self.s8_M_shift[i-1]
                    self.s8_Mp_shift[i] <<= self.s8_Mp_shift[i-1]
                self.s8_M_shift[0] <<= self.s7_M
                self.s8_Mp_shift[0] <<= self.s7_Mp
        # ------------------------------------------------------------------
        # Reduction iterations 0, 1, 2
        # ------------------------------------------------------------------

        self.rr0 = Wire(1, "rr0")
        self.rr1 = Wire(1, "rr1")
        self.rr2 = Wire(1, "rr2")

        # --- Iteration 0 ---
        self.r0_Z0 = Wire(265, "r0_Z0")
        self.r0_Z1 = Wire(263, "r0_Z1")
        self.r0_Z2 = Wire(257, "r0_Z2")
        self.r0_Z3 = Wire(256, "r0_Z3")
        self.r0_valid = Wire(1, "r0_valid")

        # Combinational M word split for r0 input
        self.r0_M_in = Wire(384, "r0_M_in")
        self.r0_Mp_in = Wire(128, "r0_Mp_in")
        self.r0_Mw_in = Vector(128, 3, "r0_Mw_in", vtype=Wire)
        @self.comb
        def _r0_M_split():
            self.r0_M_in <<= self.s8_M_shift[0]
            self.r0_Mp_in <<= self.s8_Mp_shift[0]
            parts = Split(self.s8_M_shift[0], 128)
            for i in range(3):
                self.r0_Mw_in[i] <<= parts[i]

        self.u_r0 = RedUnit128("u_r0")
        self.instantiate(self.u_r0, "u_r0",
            port_map={
                "clk": self.clk, "rst_n": self.rst_n,
                "valid_in": self.s8_valid, "ready_out": self.rr0,
                "Z0": self.s8_Z0_r, "Z1": _sign_ext(self.s8_Z1_r, 263), "Z2": self.s8_Z2_r,
                "Z3": _sign_ext(self.s8_Z3_r, 260), "Z4": self.s8_Z4_r,
                "M0": self.r0_Mw_in[0], "M1": self.r0_Mw_in[1], "M2": self.r0_Mw_in[2],
                "Mp": self.r0_Mp_in,
                "valid_out": self.r0_valid, "ready_in": Const(1, 1),
                "Z0_out": self.r0_Z0, "Z1_out": self.r0_Z1,
                "Z2_out": self.r0_Z2, "Z3_out": self.r0_Z3
            })

        # Register R0 outputs (input to R1)
        self.r0_Z0_r = Reg(265, "r0_Z0_r")
        self.r0_Z1_r = Reg(263, "r0_Z1_r")
        self.r0_Z2_r = Reg(260, "r0_Z2_r")
        self.r0_Z3_r = Reg(257, "r0_Z3_r")
        self.r0_valid_r = Reg(1, "r0_valid_r")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _r0_cap():
            with If(self.rst_n == 0):
                self.r0_valid_r <<= 0
            with Else():
                self.r0_valid_r <<= self.r0_valid
                with If(self.r0_valid):
                    self.r0_Z0_r <<= self.r0_Z0
                    self.r0_Z1_r <<= self.r0_Z1
                    self.r0_Z2_r <<= self.r0_Z2
                    self.r0_Z3_r <<= self.r0_Z3

        self.r0_M_shift = [Reg(384, f"r0_M_shift_{i}") for i in range(16)]
        self.r0_Mp_shift = [Reg(128, f"r0_Mp_shift_{i}") for i in range(16)]

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _r0_M_shift_seq():
            with If(self.rst_n == 0):
                for i in range(16):
                    self.r0_M_shift[i] <<= 0
                    self.r0_Mp_shift[i] <<= 0
            with Else():
                for i in range(15, 0, -1):
                    self.r0_M_shift[i] <<= self.r0_M_shift[i-1]
                    self.r0_Mp_shift[i] <<= self.r0_Mp_shift[i-1]
                self.r0_M_shift[0] <<= self.s8_M_shift[15]
                self.r0_Mp_shift[0] <<= self.s8_Mp_shift[15]

        # --- Iteration 1 ---
        self.r1_Z0 = Wire(265, "r1_Z0")
        self.r1_Z1 = Wire(263, "r1_Z1")
        self.r1_Z2 = Wire(257, "r1_Z2")
        self.r1_Z3 = Wire(256, "r1_Z3")
        self.r1_valid = Wire(1, "r1_valid")

        self.r1_M_in = Wire(384, "r1_M_in")
        self.r1_Mp_in = Wire(128, "r1_Mp_in")
        self.r1_Mw_in = Vector(128, 3, "r1_Mw_in", vtype=Wire)
        @self.comb
        def _r1_M_split():
            self.r1_M_in <<= self.r0_M_shift[0]
            self.r1_Mp_in <<= self.r0_Mp_shift[0]
            parts = Split(self.r0_M_shift[0], 128)
            for i in range(3):
                self.r1_Mw_in[i] <<= parts[i]

        self.u_r1 = RedUnit128("u_r1")
        self.instantiate(self.u_r1, "u_r1",
            port_map={
                "clk": self.clk, "rst_n": self.rst_n,
                "valid_in": self.r0_valid_r, "ready_out": self.rr1,
                "Z0": self.r0_Z0_r, "Z1": self.r0_Z1_r, "Z2": self.r0_Z2_r,
                "Z3": _sign_ext(self.r0_Z3_r, 260), "Z4": Const(0, 257),  # Z4 should be 0 after first reduction
                "M0": self.r1_Mw_in[0], "M1": self.r1_Mw_in[1], "M2": self.r1_Mw_in[2],
                "Mp": self.r1_Mp_in,
                "valid_out": self.r1_valid, "ready_in": Const(1, 1),
                "Z0_out": self.r1_Z0, "Z1_out": self.r1_Z1,
                "Z2_out": self.r1_Z2, "Z3_out": self.r1_Z3
            })

        # Register R1 outputs (input to R2)
        self.r1_Z0_r = Reg(265, "r1_Z0_r")
        self.r1_Z1_r = Reg(263, "r1_Z1_r")
        self.r1_Z2_r = Reg(260, "r1_Z2_r")
        self.r1_valid_r = Reg(1, "r1_valid_r")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _r1_cap():
            with If(self.rst_n == 0):
                self.r1_valid_r <<= 0
            with Else():
                self.r1_valid_r <<= self.r1_valid
                with If(self.r1_valid):
                    self.r1_Z0_r <<= self.r1_Z0
                    self.r1_Z1_r <<= self.r1_Z1
                    self.r1_Z2_r <<= self.r1_Z2

        self.r1_M_shift = [Reg(384, f"r1_M_shift_{i}") for i in range(16)]
        self.r1_Mp_shift = [Reg(128, f"r1_Mp_shift_{i}") for i in range(16)]

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _r1_M_shift_seq():
            with If(self.rst_n == 0):
                for i in range(16):
                    self.r1_M_shift[i] <<= 0
                    self.r1_Mp_shift[i] <<= 0
            with Else():
                for i in range(15, 0, -1):
                    self.r1_M_shift[i] <<= self.r1_M_shift[i-1]
                    self.r1_Mp_shift[i] <<= self.r1_Mp_shift[i-1]
                self.r1_M_shift[0] <<= self.r0_M_shift[15]
                self.r1_Mp_shift[0] <<= self.r0_Mp_shift[15]

        # --- Iteration 2 ---
        self.r2_Z0 = Wire(265, "r2_Z0")
        self.r2_Z1 = Wire(263, "r2_Z1")
        self.r2_Z2 = Wire(257, "r2_Z2")
        self.r2_Z3 = Wire(256, "r2_Z3")
        self.r2_valid = Wire(1, "r2_valid")

        self.r2_M_in = Wire(384, "r2_M_in")
        self.r2_Mp_in = Wire(128, "r2_Mp_in")
        self.r2_Mw_in = Vector(128, 3, "r2_Mw_in", vtype=Wire)
        @self.comb
        def _r2_M_split():
            self.r2_M_in <<= self.r1_M_shift[0]
            self.r2_Mp_in <<= self.r1_Mp_shift[0]
            parts = Split(self.r1_M_shift[0], 128)
            for i in range(3):
                self.r2_Mw_in[i] <<= parts[i]

        self.u_r2 = RedUnit128("u_r2")
        self.instantiate(self.u_r2, "u_r2",
            port_map={
                "clk": self.clk, "rst_n": self.rst_n,
                "valid_in": self.r1_valid_r, "ready_out": self.rr2,
                "Z0": self.r1_Z0_r, "Z1": self.r1_Z1_r, "Z2": self.r1_Z2_r,
                "Z3": Const(0, 260), "Z4": Const(0, 257),  # Z3,Z4 should be 0 after second reduction
                "M0": self.r2_Mw_in[0], "M1": self.r2_Mw_in[1], "M2": self.r2_Mw_in[2],
                "Mp": self.r2_Mp_in,
                "valid_out": self.r2_valid, "ready_in": Const(1, 1),
                "Z0_out": self.r2_Z0, "Z1_out": self.r2_Z1,
                "Z2_out": self.r2_Z2, "Z3_out": self.r2_Z3
            })

        # Register R2 outputs
        self.r2_Z0_r = Reg(265, "r2_Z0_r")
        self.r2_Z1_r = Reg(263, "r2_Z1_r")
        self.r2_M_r = Reg(384, "r2_M_r")
        self.r2_valid_r = Reg(1, "r2_valid_r")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _r2_cap():
            with If(self.rst_n == 0):
                self.r2_valid_r <<= 0
            with Else():
                self.r2_valid_r <<= self.r2_valid
                with If(self.r2_valid):
                    self.r2_Z0_r <<= self.r2_Z0
                    self.r2_Z1_r <<= self.r2_Z1
                    self.r2_M_r <<= self.r1_M_shift[15]

        # ------------------------------------------------------------------
        # Final stage: conditional subtraction + output register
        # ------------------------------------------------------------------
        self.final_Z_full = Wire(391, "final_Z_full")
        self.final_Z_sub = Wire(391, "final_Z_sub")
        self.final_Z_out = Wire(384, "final_Z_out")
        self.Z_reg = Reg(384, "Z_reg")
        self.o_valid_reg = Reg(1, "o_valid_reg")

        @self.comb
        def _final_comb():
            self.final_Z_full <<= (self.r2_Z1_r << 128) + self.r2_Z0_r
            self.final_Z_sub <<= self.final_Z_full - self.r2_M_r
            self.final_Z_out <<= Mux(self.final_Z_full >= self.r2_M_r, self.final_Z_sub[383:0], self.final_Z_full[383:0])
            self.Z <<= self.Z_reg
            self.o_valid <<= self.o_valid_reg

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _final_seq():
            with If(self.rst_n == 0):
                self.o_valid_reg <<= 0
            with Else():
                with If((~self.o_valid_reg) | self.o_ready):
                    self.o_valid_reg <<= self.r2_valid_r
                    with If(self.r2_valid_r):
                        self.Z_reg <<= self.final_Z_out

        # ------------------------------------------------------------------
        # Ready back-propagation (simplified: fully feed-forward, no back-pressure)
        # ------------------------------------------------------------------
        @self.comb
        def _ready_const():
            self.s7_ready <<= 1
            self.s8_ready <<= 1
            self.i_ready <<= 1

# =====================================================================
# 128-bit word reduction unit (1 iteration of outer loop)
# Latency = 13 cycles
# =====================================================================
class RedUnit128(Module):
    def __init__(self, name: str = "RedUnit128"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.valid_in = Input(1, "valid_in")
        self.ready_out = Output(1, "ready_out")
        self.Z0 = Input(265, "Z0")
        self.Z1 = Input(263, "Z1")
        self.Z2 = Input(260, "Z2")
        self.Z3 = Input(260, "Z3")
        self.Z4 = Input(257, "Z4")
        self.M0 = Input(128, "M0")
        self.M1 = Input(128, "M1")
        self.M2 = Input(128, "M2")
        self.Mp = Input(128, "Mp")
        self.valid_out = Output(1, "valid_out")
        self.ready_in = Input(1, "ready_in")
        self.Z0_out = Output(265, "Z0_out")
        self.Z1_out = Output(263, "Z1_out")
        self.Z2_out = Output(260, "Z2_out")
        self.Z3_out = Output(257, "Z3_out")

        # ------------------------------------------------------------------
        # Stage 0-6: LSBMult128Pipe
        # ------------------------------------------------------------------
        self.lsb_q = Wire(128, "lsb_q")
        self.u_lsb = LSBMult128Pipe("u_lsb")
        self.instantiate(self.u_lsb, "u_lsb",
            port_map={
                "clk": self.clk, "rst_n": self.rst_n,
                "a": self.Z0[127:0], "b": self.Mp,
                "valid_in": self.valid_in, "ready_out": Wire(1, "rlsb"),
                "prod_lo": self.lsb_q, "valid_out": Wire(1, "vlsb"), "ready_in": Const(1, 1)
            })

        # Delay lines: M words by 7 cycles, Z1..Z4 by 14 cycles
        self.M0_d = [Reg(128, f"M0_d{i}") for i in range(8)]
        self.M1_d = [Reg(128, f"M1_d{i}") for i in range(8)]
        self.M2_d = [Reg(128, f"M2_d{i}") for i in range(8)]
        self.Z1_d = [Reg(263, f"Z1_d{i}") for i in range(14)]
        self.Z2_d = [Reg(260, f"Z2_d{i}") for i in range(14)]
        self.Z3_d = [Reg(260, f"Z3_d{i}") for i in range(14)]
        self.Z4_d = [Reg(257, f"Z4_d{i}") for i in range(14)]
        self.vin_d = [Reg(1, f"vin_d{i}") for i in range(6)]

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _delay_lines():
            with If(self.rst_n == 0):
                for i in range(8):
                    self.M0_d[i] <<= 0
                    self.M1_d[i] <<= 0
                    self.M2_d[i] <<= 0
                for i in range(6):
                    self.vin_d[i] <<= 0
                for i in range(14):
                    self.Z1_d[i] <<= 0
                    self.Z2_d[i] <<= 0
                    self.Z3_d[i] <<= 0
                    self.Z4_d[i] <<= 0
            with Else():
                for i in range(7, 0, -1):
                    self.M0_d[i] <<= self.M0_d[i - 1]
                    self.M1_d[i] <<= self.M1_d[i - 1]
                    self.M2_d[i] <<= self.M2_d[i - 1]
                for i in range(5, 0, -1):
                    self.vin_d[i] <<= self.vin_d[i - 1]
                for i in range(13, 0, -1):
                    self.Z1_d[i] <<= self.Z1_d[i - 1]
                    self.Z2_d[i] <<= self.Z2_d[i - 1]
                    self.Z3_d[i] <<= self.Z3_d[i - 1]
                    self.Z4_d[i] <<= self.Z4_d[i - 1]
                self.M0_d[0] <<= self.M0
                self.M1_d[0] <<= self.M1
                self.M2_d[0] <<= self.M2
                self.vin_d[0] <<= self.valid_in
                self.Z1_d[0] <<= self.Z1
                self.Z2_d[0] <<= self.Z2
                self.Z3_d[0] <<= self.Z3
                self.Z4_d[0] <<= self.Z4

        # ------------------------------------------------------------------
        # Stage 6: capture q, start FullMults
        # ------------------------------------------------------------------
        self.q_valid = Reg(1, "q_valid")
        self.q_r = Reg(128, "q_r")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _q_cap():
            with If(self.rst_n == 0):
                self.q_valid <<= 0
            with Else():
                self.q_valid <<= self.vin_d[5]
                with If(self.vin_d[5]):
                    self.q_r <<= self.lsb_q

        # 1-cycle delay for q_r and q_valid to keep q_r stable when u_qm* starts
        self.vin_d5_r = Reg(1, "vin_d5_r")
        self.q_valid_d = Reg(1, "q_valid_d")
        self.q_r_d = Reg(128, "q_r_d")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _delay_vin_d5():
            with If(self.rst_n == 0):
                self.vin_d5_r <<= 0
            with Else():
                self.vin_d5_r <<= self.vin_d[5]

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _delay_q():
            with If(self.rst_n == 0):
                self.q_valid_d <<= 0
                self.q_r_d <<= 0
            with Else():
                self.q_valid_d <<= self.vin_d5_r
                with If(self.vin_d5_r):
                    self.q_r_d <<= self.q_r

        # FullMults for q * M0..M2
        self.qm0 = Wire(256, "qm0")
        self.qm1 = Wire(256, "qm1")
        self.qm2 = Wire(256, "qm2")

        self.u_qm0 = Mul128x128Pipe("u_qm0")
        self.u_qm1 = Mul128x128Pipe("u_qm1")
        self.u_qm2 = Mul128x128Pipe("u_qm2")
        self.instantiate(self.u_qm0, "u_qm0",
            port_map={
                "clk": self.clk, "rst_n": self.rst_n,
                "a": self.q_r_d, "b": self.M0_d[7],
                "valid_in": self.q_valid_d, "ready_out": Wire(1, "rqm0"),
                "prod": self.qm0, "valid_out": Wire(1, "vqm0"), "ready_in": Const(1, 1)
            })
        self.instantiate(self.u_qm1, "u_qm1",
            port_map={
                "clk": self.clk, "rst_n": self.rst_n,
                "a": self.q_r_d, "b": self.M1_d[7],
                "valid_in": self.q_valid_d, "ready_out": Wire(1, "rqm1"),
                "prod": self.qm1, "valid_out": Wire(1, "vqm1"), "ready_in": Const(1, 1)
            })
        self.instantiate(self.u_qm2, "u_qm2",
            port_map={
                "clk": self.clk, "rst_n": self.rst_n,
                "a": self.q_r_d, "b": self.M2_d[7],
                "valid_in": self.q_valid_d, "ready_out": Wire(1, "rqm2"),
                "prod": self.qm2, "valid_out": Wire(1, "vqm2"), "ready_in": Const(1, 1)
            })

        # Delay q_valid_d by 7 cycles to match FullMult latency (q_r_d at cycle 7 -> qm at cycle 12)
        self.qv_d = [Reg(1, f"qv_d{i}") for i in range(7)]
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _delay_qv():
            with If(self.rst_n == 0):
                for i in range(7):
                    self.qv_d[i] <<= 0
            with Else():
                for i in range(6, 0, -1):
                    self.qv_d[i] <<= self.qv_d[i - 1]
                self.qv_d[0] <<= self.q_valid_d

        # ------------------------------------------------------------------
        # Stage 12: capture FullMult outputs and compute updated Z vector
        # ------------------------------------------------------------------
        self.out_valid = Reg(1, "out_valid")
        self.out_Z0 = Reg(265, "out_Z0")
        self.out_Z1 = Reg(263, "out_Z1")
        self.out_Z2 = Reg(260, "out_Z2")
        self.out_Z3 = Reg(257, "out_Z3")

        self.Z0_d = [Reg(265, f"Z0_d{i}") for i in range(14)]
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _delay_Z0():
            with If(self.rst_n == 0):
                for i in range(14):
                    self.Z0_d[i] <<= 0
            with Else():
                for i in range(13, 0, -1):
                    self.Z0_d[i] <<= self.Z0_d[i - 1]
                self.Z0_d[0] <<= self.Z0

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _out_seq():
            with If(self.rst_n == 0):
                self.out_valid <<= 0
            with Else():
                with If((~self.out_valid) | self.ready_in):
                    self.out_valid <<= self.qv_d[5]
                    with If(self.qv_d[5]):
                        z0_full = PadLeft(self.Z0_d[13], 266) + PadLeft(self.qm0, 266)
                        carry = z0_full[265:128]
                        z0_sum = PadLeft(carry, 266) + _sign_ext(self.Z1_d[13], 266) + PadLeft(self.qm1, 266)
                        self.out_Z0 <<= z0_sum[264:0]
                        z1_sum = _sign_ext(self.Z2_d[13], 261) + PadLeft(self.qm2, 261)
                        self.out_Z1 <<= _sign_ext(z1_sum[260:0], 263)
                        self.out_Z2 <<= self.Z3_d[13]
                        self.out_Z3 <<= self.Z4_d[13]

        @self.comb
        def _out_comb():
            self.Z0_out <<= self.out_Z0
            self.Z1_out <<= self.out_Z1
            self.Z2_out <<= self.out_Z2
            self.Z3_out <<= self.out_Z3
            self.valid_out <<= self.out_valid

        # Need Z0 delay line too (for addition at stage 12)
        @self.comb
        def _ready_comb():
            self.ready_out <<= (~self.out_valid) | self.ready_in



if __name__ == "__main__":
    top = MontgomeryMult384()
    emitter = VerilogEmitter()
    sv = emitter.emit_design(top)
    print(sv)
