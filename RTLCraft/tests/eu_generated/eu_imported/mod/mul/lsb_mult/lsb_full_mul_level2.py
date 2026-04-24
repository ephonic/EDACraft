"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class lsb_full_mul_level2(Module):
    def __init__(self, name: str = "lsb_full_mul_level2"), A_WIDTH: int = 96, B_WIDTH: int = 96, WIDTH: int = Mux((self.A_WIDTH > self.B_WIDTH), self.A_WIDTH, self.B_WIDTH), WIDTH_ODD: int = (self.WIDTH % 2), WIDTH_HALF: int = ((self.WIDTH - self.WIDTH_ODD) // 2), H_WIDTH: int = (self.WIDTH_HALF + self.WIDTH_ODD), L_WIDTH: int = self.WIDTH_HALF, F_WIDTH: int = (self.H_WIDTH + 1):
        super().__init__(name or "lsb_full_mul_level2")

        self.add_localparam("WIDTH", Mux((self.A_WIDTH > self.B_WIDTH), self.A_WIDTH, self.B_WIDTH))
        self.add_localparam("WIDTH_ODD", (self.WIDTH % 2))
        self.add_localparam("WIDTH_HALF", ((self.WIDTH - self.WIDTH_ODD) // 2))
        self.add_localparam("H_WIDTH", (self.WIDTH_HALF + self.WIDTH_ODD))
        self.add_localparam("L_WIDTH", self.WIDTH_HALF)
        self.add_localparam("F_WIDTH", (self.H_WIDTH + 1))
        self.clk = Input(1, "clk")
        self.rstn = Input(1, "rstn")
        self.a = Input(((self.A_WIDTH - 1) - 0 + 1), "a")
        self.b = Input(((self.B_WIDTH - 1) - 0 + 1), "b")
        self.en0 = Input(1, "en0")
        self.en1 = Input(1, "en1")
        self.en2 = Input(1, "en2")
        self.res = Output((((self.A_WIDTH + self.B_WIDTH) - 1) - 0 + 1), "res")

        self.a0 = Wire(((self.L_WIDTH - 1) - 0 + 1), "a0")
        self.a1 = Wire(((self.H_WIDTH - 1) - 0 + 1), "a1")
        self.b0 = Wire(((self.L_WIDTH - 1) - 0 + 1), "b0")
        self.b1 = Wire(((self.H_WIDTH - 1) - 0 + 1), "b1")
        self.a0b0_r2 = Wire((((self.L_WIDTH * 2) - 1) - 0 + 1), "a0b0_r2")
        self.a1b1_r2 = Wire((((self.H_WIDTH * 2) - 1) - 0 + 1), "a1b1_r2")
        self.a_fold = Wire(((self.F_WIDTH - 1) - 0 + 1), "a_fold")
        self.b_fold = Wire(((self.F_WIDTH - 1) - 0 + 1), "b_fold")
        self.temp0_r2 = Wire((((self.F_WIDTH * 2) - 1) - 0 + 1), "temp0_r2")
        self.a0b0_r3 = Reg((((self.L_WIDTH * 2) - 1) - 0 + 1), "a0b0_r3")
        self.a1b1_r3 = Reg((((self.H_WIDTH * 2) - 1) - 0 + 1), "a1b1_r3")
        self.temp0_r3 = Reg((((self.F_WIDTH * 2) - 1) - 0 + 1), "temp0_r3")
        self.r = Wire((((self.WIDTH * 2) - 1) - 0 + 1), "r")

        # TODO: unpack assignment: Cat(self.a1, self.a0) = self.a
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.b1, self.b0) = self.b
        # Consider using Split() or manual bit slicing

        u0_mul = lsb_full_mul_level1(None=self.L_WIDTH)
        self.instantiate(
            u0_mul,
            "u0_mul",
            params={None: self.L_WIDTH},
            port_map={
                "clk": self.clk,
                "en0": self.en0,
                "en1": self.en1,
                "a": self.a0,
                "b": self.b0,
                "res": self.a0b0_r2,
            },
        )

        u1_mul = lsb_full_mul_level1(None=self.H_WIDTH)
        self.instantiate(
            u1_mul,
            "u1_mul",
            params={None: self.H_WIDTH},
            port_map={
                "clk": self.clk,
                "en0": self.en0,
                "en1": self.en1,
                "a": self.a1,
                "b": self.b1,
                "res": self.a1b1_r2,
            },
        )

        u2_mul = lsb_full_mul_level1(None=self.F_WIDTH)
        self.instantiate(
            u2_mul,
            "u2_mul",
            params={None: self.F_WIDTH},
            port_map={
                "clk": self.clk,
                "en0": self.en0,
                "en1": self.en1,
                "a": self.a_fold,
                "b": self.b_fold,
                "res": self.temp0_r2,
            },
        )

        @self.seq(self.clk, None)
        def _seq_logic():
            with If(self.en2):
                self.a0b0_r3 <<= self.a0b0_r2
                self.a1b1_r3 <<= self.a1b1_r2
                self.temp0_r3 <<= self.temp0_r2
        self.r <<= ((((Cat(self.a1b1_r3, Rep(Cat(0), (2 * self.L_WIDTH))) + Cat(self.temp0_r3, Rep(Cat(0), self.L_WIDTH))) - Cat(self.a0b0_r3, Rep(Cat(0), self.L_WIDTH))) - Cat(self.a1b1_r3, Rep(Cat(0), self.L_WIDTH))) + self.a0b0_r3)
        self.res <<= self.r
