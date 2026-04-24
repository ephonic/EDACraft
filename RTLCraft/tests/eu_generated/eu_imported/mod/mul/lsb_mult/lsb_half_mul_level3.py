"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class lsb_half_mul_level3(Module):
    def __init__(self, name: str = "lsb_half_mul_level3"), R_WIDTH: int = (self.B_WIDTH + self.E_WIDTH), WIDTH_ODD: int = (self.R_WIDTH % 2), WIDTH_HALF: int = ((self.R_WIDTH - self.WIDTH_ODD) // 2), L_WIDTH: int = (self.WIDTH_HALF + self.WIDTH_ODD), H_WIDTH: int = self.WIDTH_HALF, F_WIDTH: int = (self.H_WIDTH + self.L_WIDTH):
        super().__init__(name or "lsb_half_mul_level3")

        self.add_param("A_WIDTH", 385)
        self.add_param("B_WIDTH", 384)
        self.add_param("E_WIDTH", 2)
        self.add_localparam("R_WIDTH", (self.B_WIDTH + self.E_WIDTH))
        self.add_localparam("WIDTH_ODD", (self.R_WIDTH % 2))
        self.add_localparam("WIDTH_HALF", ((self.R_WIDTH - self.WIDTH_ODD) // 2))
        self.add_localparam("L_WIDTH", (self.WIDTH_HALF + self.WIDTH_ODD))
        self.add_localparam("H_WIDTH", self.WIDTH_HALF)
        self.add_localparam("F_WIDTH", (self.H_WIDTH + self.L_WIDTH))
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.a = Input(((self.A_WIDTH - 1) - 0 + 1), "a")
        self.b = Input(((self.B_WIDTH - 1) - 0 + 1), "b")
        self.en0 = Input(1, "en0")
        self.en1 = Input(1, "en1")
        self.en2 = Input(1, "en2")
        self.en3 = Input(1, "en3")
        self.en4 = Input(1, "en4")
        self.res = Output(((self.R_WIDTH - 1) - 0 + 1), "res")

        self.a0 = Wire(((self.L_WIDTH - 1) - 0 + 1), "a0")
        self.a1 = Wire(((self.H_WIDTH - 1) - 0 + 1), "a1")
        self.b0 = Wire(((self.L_WIDTH - 1) - 0 + 1), "b0")
        self.b1 = Wire(((self.H_WIDTH - 1) - 0 + 1), "b1")
        self.a0b1_r2 = Wire(((self.F_WIDTH - 1) - 0 + 1), "a0b1_r2")
        self.a1b0_r2 = Wire(((self.F_WIDTH - 1) - 0 + 1), "a1b0_r2")
        self.a0b0_r2 = Wire((((self.L_WIDTH * 2) - 1) - 0 + 1), "a0b0_r2")
        self.a0b1_r3 = Reg(((self.F_WIDTH - 1) - 0 + 1), "a0b1_r3")
        self.a1b0_r3 = Reg(((self.F_WIDTH - 1) - 0 + 1), "a1b0_r3")
        self.a0b0_r3 = Reg((((self.L_WIDTH * 2) - 1) - 0 + 1), "a0b0_r3")
        self.r = Wire(((self.L_WIDTH + self.F_WIDTH) - 0 + 1), "r")

        # TODO: unpack assignment: Cat(self.a1, self.a0) = self.a
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.b1, self.b0) = self.b
        # Consider using Split() or manual bit slicing

        u0_mul = lsb_half_mul_level2(None=self.H_WIDTH)
        self.instantiate(
            u0_mul,
            "u0_mul",
            params={None: self.H_WIDTH},
            port_map={
                "clk": self.clk,
                "rst_n": self.rst_n,
                "en0": self.en0,
                "en1": self.en1,
                "en2": self.en2,
                "a": self.a0,
                "b": self.b1,
                "res": self.a0b1_r2,
            },
        )

        u1_mul = lsb_half_mul_level2(None=self.L_WIDTH)
        self.instantiate(
            u1_mul,
            "u1_mul",
            params={None: self.L_WIDTH},
            port_map={
                "clk": self.clk,
                "rst_n": self.rst_n,
                "en0": self.en0,
                "en1": self.en1,
                "en2": self.en2,
                "a": self.a1,
                "b": self.b0,
                "res": self.a1b0_r2,
            },
        )

        u2_mul = lsb_full_mul_level2(None=self.L_WIDTH)
        self.instantiate(
            u2_mul,
            "u2_mul",
            params={None: self.L_WIDTH},
            port_map={
                "clk": self.clk,
                "rstn": self.rst_n,
                "en0": self.en0,
                "en1": self.en1,
                "en2": self.en2,
                "a": self.a0,
                "b": self.b0,
                "res": self.a0b0_r2,
            },
        )

        @self.seq(self.clk, None)
        def _seq_logic():
            with If(self.en3):
                self.a0b1_r3 <<= self.a0b1_r2
                self.a1b0_r3 <<= self.a1b0_r2
                self.a0b0_r3 <<= self.a0b0_r2
        self.r <<= ((Cat(self.a0b1_r3, Rep(Cat(0), self.L_WIDTH)) + Cat(self.a1b0_r3, Rep(Cat(0), self.L_WIDTH))) + self.a0b0_r3)

        @self.seq(self.clk, None)
        def _seq_logic():
            with If(self.en4):
                self.res <<= self.r[(self.R_WIDTH - 1):0]
