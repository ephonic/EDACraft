"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class approx_msb_mul_level2(Module):
    def __init__(self, name: str = "approx_msb_mul_level2"), WIDTH_ODD: int = (self.R_WIDTH % 2), WIDTH_HALF: int = ((self.R_WIDTH - self.WIDTH_ODD) // 2), L_WIDTH: int = self.WIDTH_HALF, A_H_WIDTH: int = (self.A_WIDTH - self.L_WIDTH), B_H_WIDTH: int = (self.B_WIDTH - self.L_WIDTH):
        super().__init__(name or "approx_msb_mul_level2")

        self.add_param("A_WIDTH", 96)
        self.add_param("B_WIDTH", 96)
        self.add_param("R_WIDTH", 96)
        self.add_localparam("WIDTH_ODD", (self.R_WIDTH % 2))
        self.add_localparam("WIDTH_HALF", ((self.R_WIDTH - self.WIDTH_ODD) // 2))
        self.add_localparam("L_WIDTH", self.WIDTH_HALF)
        self.add_localparam("A_H_WIDTH", (self.A_WIDTH - self.L_WIDTH))
        self.add_localparam("B_H_WIDTH", (self.B_WIDTH - self.L_WIDTH))
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.a = Input(((self.A_WIDTH - 1) - 0 + 1), "a")
        self.b = Input(((self.B_WIDTH - 1) - 0 + 1), "b")
        self.en0 = Input(1, "en0")
        self.en1 = Input(1, "en1")
        self.en2 = Input(1, "en2")
        self.res = Output((((self.A_WIDTH + self.B_WIDTH) - 1) - 0 + 1), "res")

        self.a0 = Wire(((self.L_WIDTH - 1) - 0 + 1), "a0")
        self.a1 = Wire(((self.A_H_WIDTH - 1) - 0 + 1), "a1")
        self.b0 = Wire(((self.L_WIDTH - 1) - 0 + 1), "b0")
        self.b1 = Wire(((self.B_H_WIDTH - 1) - 0 + 1), "b1")
        self.a0b1_r2 = Wire((((self.L_WIDTH + self.B_H_WIDTH) - 1) - 0 + 1), "a0b1_r2")
        self.a1b0_r2 = Wire((((self.L_WIDTH + self.A_H_WIDTH) - 1) - 0 + 1), "a1b0_r2")
        self.a1b1_r2 = Wire((((self.A_H_WIDTH + self.B_H_WIDTH) - 1) - 0 + 1), "a1b1_r2")
        self.a0b1_r3 = Reg((((self.L_WIDTH + self.B_H_WIDTH) - 1) - 0 + 1), "a0b1_r3")
        self.a1b0_r3 = Reg((((self.L_WIDTH + self.A_H_WIDTH) - 1) - 0 + 1), "a1b0_r3")
        self.a1b1_r3 = Reg((((self.A_H_WIDTH + self.B_H_WIDTH) - 1) - 0 + 1), "a1b1_r3")
        self.r = Wire((((self.A_WIDTH + self.B_WIDTH) - 1) - 0 + 1), "r")

        # TODO: unpack assignment: Cat(self.a1, self.a0) = self.a
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.b1, self.b0) = self.b
        # Consider using Split() or manual bit slicing

        u0_mul = approx_msb_mul_level1(None=self.L_WIDTH)
        self.instantiate(
            u0_mul,
            "u0_mul",
            params={None: self.L_WIDTH},
            port_map={
                "clk": self.clk,
                "en0": self.en0,
                "en1": self.en1,
                "a": self.a0,
                "b": self.b1,
                "res": self.a0b1_r2,
            },
        )

        u1_mul = approx_msb_mul_level1(None=self.L_WIDTH)
        self.instantiate(
            u1_mul,
            "u1_mul",
            params={None: self.L_WIDTH},
            port_map={
                "clk": self.clk,
                "en0": self.en0,
                "en1": self.en1,
                "a": self.a1,
                "b": self.b0,
                "res": self.a1b0_r2,
            },
        )

        u2_mul = approx_full_mul_level1(None=self.B_H_WIDTH)
        self.instantiate(
            u2_mul,
            "u2_mul",
            params={None: self.B_H_WIDTH},
            port_map={
                "clk": self.clk,
                "en0": self.en0,
                "en1": self.en1,
                "a": self.a1,
                "b": self.b1,
                "res": self.a1b1_r2,
            },
        )

        @self.seq(self.clk, None)
        def _seq_logic():
            with If(self.en2):
                self.a0b1_r3 <<= self.a0b1_r2
                self.a1b0_r3 <<= self.a1b0_r2
                self.a1b1_r3 <<= self.a1b1_r2
        self.r <<= ((Cat(self.a1b1_r3, Rep(Cat(0), (2 * self.L_WIDTH))) + Cat(self.a0b1_r3, Rep(Cat(0), self.L_WIDTH))) + Cat(self.a1b0_r3, Rep(Cat(0), self.L_WIDTH)))
        self.res <<= self.r
