"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class js_zk_mul_level3(Module):
    def __init__(self, name: str = "js_zk_mul_level3"), A_WIDTH: int = 384, B_WIDTH: int = 384, R_WIDTH: int = 768, WIDTH: int = Mux((self.A_WIDTH > self.B_WIDTH), self.A_WIDTH, self.B_WIDTH), WIDTH_ODD: int = (self.WIDTH % 2), WIDTH_HALF: int = ((self.WIDTH - self.WIDTH_ODD) // 2), H_WIDTH: int = (self.WIDTH_HALF + self.WIDTH_ODD), L_WIDTH: int = self.WIDTH_HALF, F_WIDTH: int = (self.H_WIDTH + 1):
        super().__init__(name or "js_zk_mul_level3")

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
        self.en3 = Input(1, "en3")
        self.en4 = Input(1, "en4")
        self.res = Output(((self.R_WIDTH - 1) - 0 + 1), "res")

        self.a0 = Wire(((self.L_WIDTH - 1) - 0 + 1), "a0")
        self.a1 = Wire(((self.H_WIDTH - 1) - 0 + 1), "a1")
        self.b0 = Wire(((self.L_WIDTH - 1) - 0 + 1), "b0")
        self.b1 = Wire(((self.H_WIDTH - 1) - 0 + 1), "b1")
        self.a_fold = Wire(((self.F_WIDTH - 1) - 0 + 1), "a_fold")
        self.b_fold = Wire(((self.F_WIDTH - 1) - 0 + 1), "b_fold")
        self.a0_r0 = Reg(((self.L_WIDTH - 1) - 0 + 1), "a0_r0")
        self.b0_r0 = Reg(((self.L_WIDTH - 1) - 0 + 1), "b0_r0")
        self.a1_r0 = Reg(((self.H_WIDTH - 1) - 0 + 1), "a1_r0")
        self.b1_r0 = Reg(((self.H_WIDTH - 1) - 0 + 1), "b1_r0")
        self.a_fold_r0 = Reg(((self.F_WIDTH - 1) - 0 + 1), "a_fold_r0")
        self.b_fold_r0 = Reg(((self.F_WIDTH - 1) - 0 + 1), "b_fold_r0")
        self.a0b0_r3 = Wire((((self.L_WIDTH * 2) - 1) - 0 + 1), "a0b0_r3")
        self.a1b1_r3 = Wire((((self.H_WIDTH * 2) - 1) - 0 + 1), "a1b1_r3")
        self.temp0_r3 = Wire((((self.F_WIDTH * 2) - 1) - 0 + 1), "temp0_r3")
        self.a0b0_r4 = Reg((((self.L_WIDTH * 2) - 1) - 0 + 1), "a0b0_r4")
        self.a1b1_r4 = Reg((((self.H_WIDTH * 2) - 1) - 0 + 1), "a1b1_r4")
        self.temp0_r4 = Reg((((self.F_WIDTH * 2) - 1) - 0 + 1), "temp0_r4")
        self.r = Wire((((self.WIDTH * 2) - 1) - 0 + 1), "r")


        @self.seq(self.clk, None)
        def _seq_logic():
            with If(self.en0):
                Cat(self.a1_r0, self.a0_r0) <<= self.a
                Cat(self.b1_r0, self.b0_r0) <<= self.b
                self.a_fold_r0 <<= self.a_fold
                self.b_fold_r0 <<= self.b_fold
        # TODO: unpack assignment: Cat(self.a1, self.a0) = self.a
        # Consider using Split() or manual bit slicing
        # TODO: unpack assignment: Cat(self.b1, self.b0) = self.b
        # Consider using Split() or manual bit slicing

        u0_mul = js_zk_mul_level2(None=self.L_WIDTH)
        self.instantiate(
            u0_mul,
            "u0_mul",
            params={None: self.L_WIDTH},
            port_map={
                "clk": self.clk,
                "rstn": self.rstn,
                "en0": self.en1,
                "en1": self.en2,
                "en2": self.en3,
                "a": self.a0_r0,
                "b": self.b0_r0,
                "res": self.a0b0_r3,
            },
        )

        u1_mul = js_zk_mul_level2(None=self.H_WIDTH)
        self.instantiate(
            u1_mul,
            "u1_mul",
            params={None: self.H_WIDTH},
            port_map={
                "clk": self.clk,
                "rstn": self.rstn,
                "en0": self.en0,
                "en1": self.en1,
                "en2": self.en2,
                "a": self.a1_r0,
                "b": self.b1_r0,
                "res": self.a1b1_r3,
            },
        )

        u2_mul = js_zk_mul_level2(None=self.F_WIDTH)
        self.instantiate(
            u2_mul,
            "u2_mul",
            params={None: self.F_WIDTH},
            port_map={
                "clk": self.clk,
                "rstn": self.rstn,
                "en0": self.en0,
                "en1": self.en1,
                "en2": self.en2,
                "a": self.a_fold_r0,
                "b": self.b_fold_r0,
                "res": self.temp0_r3,
            },
        )

        @self.seq(self.clk, None)
        def _seq_logic():
            with If(self.en3):
                self.a0b0_r4 <<= self.a0b0_r3
                self.a1b1_r4 <<= self.a1b1_r3
                self.temp0_r4 <<= self.temp0_r3
        self.r <<= (Cat((((Cat(self.a1b1_r4, Rep(Cat(0), self.L_WIDTH)) + self.temp0_r4) - self.a0b0_r4) - self.a1b1_r4), Rep(Cat(0), self.L_WIDTH)) + self.a0b0_r4)

        @self.seq(self.clk, None)
        def _seq_logic():
            with If(self.en4):
                self.res <<= self.r[(self.R_WIDTH - 1):0]
