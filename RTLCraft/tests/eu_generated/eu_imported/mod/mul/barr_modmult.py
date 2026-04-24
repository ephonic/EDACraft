"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class barr_modmult(Module):
    def __init__(self, name: str = "barr_modmult"), F_WIDTH: int = (self.DATA_WIDTH * 2), M_SHIFT: int = 5, F_SHIFT: int = ((self.M_SHIFT * 2) - 1), V_SHIFT: int = ((self.M_SHIFT * 3) + 2):
        super().__init__(name or "barr_modmult")

        self.add_param("DATA_WIDTH", 256)
        self.add_param("E_WIDTH", 2)
        self.add_param("VALID_WIDTH", 1)
        self.add_localparam("F_WIDTH", (self.DATA_WIDTH * 2))
        self.add_localparam("M_SHIFT", 5)
        self.add_localparam("F_SHIFT", ((self.M_SHIFT * 2) - 1))
        self.add_localparam("V_SHIFT", ((self.M_SHIFT * 3) + 2))
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.en = Input(1, "en")
        self.i_valid = Input(((self.VALID_WIDTH - 1) - 0 + 1), "i_valid")
        self.mul_a = Input(((self.DATA_WIDTH - 1) - 0 + 1), "mul_a")
        self.mul_b = Input(((self.DATA_WIDTH - 1) - 0 + 1), "mul_b")
        self.pre_c = Input((self.DATA_WIDTH - 0 + 1), "pre_c")
        self.prime = Input(((self.DATA_WIDTH - 1) - 0 + 1), "prime")
        self.o_valid = Output(((self.VALID_WIDTH - 1) - 0 + 1), "o_valid")
        self.res = Output(((self.DATA_WIDTH - 1) - 0 + 1), "res")

        self.full_mul_res = Wire(((self.F_WIDTH - 1) - 0 + 1), "full_mul_res")
        self.approx_a = Wire(((self.DATA_WIDTH - 1) - 0 + 1), "approx_a")
        self.approx_b = Reg((self.DATA_WIDTH - 0 + 1), "approx_b")
        self.approx_res = Wire(((self.DATA_WIDTH - 1) - 0 + 1), "approx_res")
        self.lsb_mul_a = Wire(((self.DATA_WIDTH - 1) - 0 + 1), "lsb_mul_a")
        self.lsb_mul_b = Wire(((self.DATA_WIDTH - 1) - 0 + 1), "lsb_mul_b")
        self.lsb_mul_res = Wire((((self.DATA_WIDTH + self.E_WIDTH) - 1) - 0 + 1), "lsb_mul_res")
        self.r_alpha = Wire((((self.DATA_WIDTH + self.E_WIDTH) - 1) - 0 + 1), "r_alpha")
        self.r_alpha_tmp = Wire(((self.DATA_WIDTH + self.E_WIDTH) - 0 + 1), "r_alpha_tmp")
        self.full_mul_res_arr = Array((((self.DATA_WIDTH + self.E_WIDTH) - 1) - 0 + 1), (self.F_SHIFT - 0 + 1), "full_mul_res_arr", vtype=Reg)
        self.prime_t = Reg(((self.DATA_WIDTH - 1) - 0 + 1), "prime_t")
        self.r_alpha_t = Reg((((self.DATA_WIDTH + self.E_WIDTH) - 1) - 0 + 1), "r_alpha_t")
        self.r_tmp1 = Wire(((self.DATA_WIDTH + self.E_WIDTH) - 0 + 1), "r_tmp1")
        self.r_tmp2 = Wire((((self.DATA_WIDTH + self.E_WIDTH) - 1) - 0 + 1), "r_tmp2")
        self.r_tmp3 = Wire(((self.DATA_WIDTH + self.E_WIDTH) - 0 + 1), "r_tmp3")
        self.res_tmp = Wire(((self.DATA_WIDTH - 1) - 0 + 1), "res_tmp")
        self.valid_array = Array(((self.VALID_WIDTH - 1) - 0 + 1), (self.V_SHIFT - 0 + 1), "valid_array", vtype=Reg)


        u_full_mul = js_zk_mul_level3(None=self.F_WIDTH)
        self.instantiate(
            u_full_mul,
            "u_full_mul",
            params={None: self.F_WIDTH},
            port_map={
                "clk": self.clk,
                "rstn": self.rst_n,
                "a": self.mul_a,
                "b": self.mul_b,
                "en0": self.en,
                "en1": self.en,
                "en2": self.en,
                "en3": self.en,
                "en4": self.en,
                "res": self.full_mul_res,
            },
        )
        self.approx_a <<= self.full_mul_res[(self.F_WIDTH - 1):self.DATA_WIDTH]

        @self.seq(self.clk, None)
        def _seq_logic():
            with If(self.en):
                self.approx_b <<= self.pre_c

        u_approx_msb_mul = approx_msb_mul_level3(None=self.DATA_WIDTH)
        self.instantiate(
            u_approx_msb_mul,
            "u_approx_msb_mul",
            params={None: self.DATA_WIDTH},
            port_map={
                "clk": self.clk,
                "rst_n": self.rst_n,
                "a": self.approx_a,
                "b": self.approx_b,
                "en0": self.en,
                "en1": self.en,
                "en2": self.en,
                "en3": self.en,
                "en4": self.en,
                "res": self.approx_res,
            },
        )

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rst_n)):
                self.full_mul_res_arr[0] <<= 0
            with Else():
                with If(self.en):
                    self.full_mul_res_arr[0] <<= self.full_mul_res[((self.DATA_WIDTH + self.E_WIDTH) - 1):0]
        # for-loop (non-generate) - parameter-driven
        for shft in range(0, self.F_SHIFT):
            with If((~self.rst_n)):
                self.full_mul_res_arr[(shft + 1)] <<= 0
            with Else():
                with If(self.en):
                    self.full_mul_res_arr[(shft + 1)] <<= self.full_mul_res_arr[shft]

        @self.seq(self.clk, None)
        def _seq_logic():
            with If(self.en):
                self.prime_t <<= self.prime
        self.lsb_mul_a <<= self.approx_res
        self.lsb_mul_b <<= self.prime_t

        u_lsb_mul = lsb_half_mul_level3(None=self.E_WIDTH)
        self.instantiate(
            u_lsb_mul,
            "u_lsb_mul",
            params={None: self.E_WIDTH},
            port_map={
                "clk": self.clk,
                "rst_n": self.rst_n,
                "a": self.lsb_mul_a,
                "b": self.lsb_mul_b,
                "en0": self.en,
                "en1": self.en,
                "en2": self.en,
                "en3": self.en,
                "en4": self.en,
                "res": self.lsb_mul_res,
            },
        )
        self.r_alpha_tmp <<= (self.full_mul_res_arr[self.F_SHIFT] - self.lsb_mul_res)
        self.r_alpha <<= Mux(self.r_alpha_tmp[(self.DATA_WIDTH + self.E_WIDTH)], (self.r_alpha_tmp + Cat(1, Rep(Cat(0), (self.DATA_WIDTH + self.E_WIDTH)))), self.r_alpha_tmp[((self.DATA_WIDTH + self.E_WIDTH) - 1):0])

        @self.seq(self.clk, None)
        def _seq_logic():
            with If(self.en):
                self.r_alpha_t <<= self.r_alpha
        self.r_tmp1 <<= (self.r_alpha_t - Cat(self.prime_t, 0))
        self.r_tmp2 <<= Mux(self.r_tmp1[(self.DATA_WIDTH + self.E_WIDTH)], self.r_alpha_t, self.r_tmp1[((self.DATA_WIDTH + self.E_WIDTH) - 1):0])
        self.r_tmp3 <<= (self.r_tmp2 - self.prime_t)
        self.res_tmp <<= Mux(self.r_tmp3[(self.DATA_WIDTH + self.E_WIDTH)], self.r_tmp2[(self.DATA_WIDTH - 1):0], self.r_tmp3[(self.DATA_WIDTH - 1):0])

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rst_n)):
                self.res <<= 0
            with Else():
                with If(self.en):
                    self.res <<= self.res_tmp
        self.o_valid <<= self.valid_array[self.V_SHIFT]

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rst_n)):
                self.valid_array[0] <<= 0
            with Else():
                with If(self.en):
                    self.valid_array[0] <<= self.i_valid
        # for-loop (non-generate) - parameter-driven
        for v_shft in range(0, self.V_SHIFT):
            with If((~self.rst_n)):
                self.valid_array[(v_shft + 1)] <<= 0
            with Else():
                with If(self.en):
                    self.valid_array[(v_shft + 1)] <<= self.valid_array[v_shft]
