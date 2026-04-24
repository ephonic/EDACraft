"""Auto-generated from Verilog by rtlgen.verilog_import."""
from rtlgen import Module, Input, Output, Wire, Reg, Memory, Array, Parameter, LocalParam
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class mod_inverse(Module):
    def __init__(self, name: str = "mod_inverse"):
        super().__init__(name or "mod_inverse")

        self.add_param("MODULU_LENGTH", 384)
        self.clk = Input(1, "clk")
        self.rstn = Input(1, "rstn")
        self.go = Input(1, "go")
        self.valid = Output(1, "valid")
        self.prime_q = Input(((self.MODULU_LENGTH - 1) - 0 + 1), "prime_q")
        self.a = Input(((self.MODULU_LENGTH - 1) - 0 + 1), "a")
        self.R = Output(((self.MODULU_LENGTH - 1) - 0 + 1), "R")

        self.u = Wire(((self.MODULU_LENGTH - 1) - 0 + 1), "u")
        self.v = Wire(((self.MODULU_LENGTH - 1) - 0 + 1), "v")
        self.u_v_minus_result = Wire((self.MODULU_LENGTH - 0 + 1), "u_v_minus_result")
        self.v_u_minus_result = Wire((self.MODULU_LENGTH - 0 + 1), "v_u_minus_result")
        self.u_or_divide_2 = Wire(((self.MODULU_LENGTH - 1) - 0 + 1), "u_or_divide_2")
        self.v_or_divide_2 = Wire(((self.MODULU_LENGTH - 1) - 0 + 1), "v_or_divide_2")
        self.u_v_final_select = Wire(1, "u_v_final_select")
        self.v_u_final_select = Wire(1, "v_u_final_select")
        self.new_u = Reg(((self.MODULU_LENGTH - 1) - 0 + 1), "new_u")
        self.new_v = Reg(((self.MODULU_LENGTH - 1) - 0 + 1), "new_v")
        self.q_reg = Reg(((self.MODULU_LENGTH - 1) - 0 + 1), "q_reg")
        self.x = Wire(((self.MODULU_LENGTH - 1) - 0 + 1), "x")
        self.y = Wire(((self.MODULU_LENGTH - 1) - 0 + 1), "y")
        self.result_x = Wire(((self.MODULU_LENGTH - 1) - 0 + 1), "result_x")
        self.result_y = Wire(((self.MODULU_LENGTH - 1) - 0 + 1), "result_y")
        self.new_x = Reg(((self.MODULU_LENGTH - 1) - 0 + 1), "new_x")
        self.new_y = Reg(((self.MODULU_LENGTH - 1) - 0 + 1), "new_y")
        self.x_y_minus_result = Wire((self.MODULU_LENGTH - 0 + 1), "x_y_minus_result")
        self.x_or_minus_y = Wire(((self.MODULU_LENGTH - 1) - 0 + 1), "x_or_minus_y")
        self.x_pluse_q = Wire((self.MODULU_LENGTH - 0 + 1), "x_pluse_q")
        self.x_before_divide_2 = Wire((self.MODULU_LENGTH - 0 + 1), "x_before_divide_2")
        self.x_after_divide_2 = Wire(((self.MODULU_LENGTH - 1) - 0 + 1), "x_after_divide_2")
        self.y_x_minus_result = Wire((self.MODULU_LENGTH - 0 + 1), "y_x_minus_result")
        self.y_or_minus_x = Wire(((self.MODULU_LENGTH - 1) - 0 + 1), "y_or_minus_x")
        self.y_pluse_q = Wire((self.MODULU_LENGTH - 0 + 1), "y_pluse_q")
        self.y_before_divide_2 = Wire((self.MODULU_LENGTH - 0 + 1), "y_before_divide_2")
        self.y_after_divide_2 = Wire(((self.MODULU_LENGTH - 1) - 0 + 1), "y_after_divide_2")
        self.state = Reg(1, "state")

        self.u_v_minus_result <<= (self.u - self.v)
        self.u_or_divide_2 <<= Mux(self.u[0], self.u, (self.u >> 1))
        self.v_u_minus_result <<= (self.v - self.u)
        self.v_or_divide_2 <<= Mux(((~self.v[0]) & self.u[0]), (self.v >> 1), self.v)
        self.v <<= self.new_v
        self.u <<= self.new_u
        self.u_v_final_select <<= ((self.u[0] & self.v[0]) & (~self.u_v_minus_result[self.MODULU_LENGTH]))
        self.v_u_final_select <<= ((self.u[0] & self.v[0]) & (~self.v_u_minus_result[self.MODULU_LENGTH]))

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.new_v <<= 0
                self.new_u <<= 0
            with Else():
                with If(self.go):
                    self.new_v <<= self.prime_q
                    self.new_u <<= self.a
                with Else():
                    self.new_v <<= Mux(self.v_u_final_select, self.v_u_minus_result, self.v_or_divide_2)
                    self.new_u <<= Mux(self.u_v_final_select, self.u_v_minus_result, self.u_or_divide_2)

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.q_reg <<= 0
            with Else():
                with If(self.go):
                    self.q_reg <<= self.prime_q
        self.x <<= self.new_x
        self.y <<= self.new_y
        self.x_y_minus_result <<= (self.x - self.y)
        self.x_or_minus_y <<= Mux(self.u_v_final_select, self.x_y_minus_result, self.x)
        self.x_pluse_q <<= (self.x_or_minus_y + self.q_reg)
        self.x_before_divide_2 <<= Mux((((self.x[0] == 1) & (self.u[0] == 0)) | (self.x_y_minus_result[self.MODULU_LENGTH] & self.u_v_final_select)), self.x_pluse_q, self.x_or_minus_y)
        self.x_after_divide_2 <<= self.x_before_divide_2[self.MODULU_LENGTH:1]
        self.y_x_minus_result <<= (self.y - self.x)
        self.y_or_minus_x <<= Mux(self.v_u_final_select, self.y_x_minus_result, self.y)
        self.y_pluse_q <<= (self.y_or_minus_x + self.q_reg)
        self.y_before_divide_2 <<= Mux((((self.y[0] == 1) & ((self.v[0] == 0) & (self.u[0] == 1))) | (self.y_x_minus_result[self.MODULU_LENGTH] & self.v_u_final_select)), self.y_pluse_q, self.y_or_minus_x)
        self.y_after_divide_2 <<= self.y_before_divide_2[self.MODULU_LENGTH:1]

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.new_x <<= 1
                self.new_y <<= 0
            with Else():
                with If(self.go):
                    self.new_x <<= 1
                    self.new_y <<= 0
                with Else():
                    self.new_x <<= Mux((self.u[0] == 0), self.x_after_divide_2, self.x_before_divide_2)
                    self.new_y <<= Mux(((self.v[0] == 0) & (self.u[0] == 1)), self.y_after_divide_2, self.y_before_divide_2)
        self.result_x <<= Mux((self.x > self.q_reg), (self.x - self.q_reg), self.x)
        self.result_y <<= Mux((self.y > self.q_reg), (self.y - self.q_reg), self.y)
        self.valid <<= (((self.u == 1) | (self.v == 1)) & self.state)
        self.R <<= Mux((self.u == 1), self.result_x, Mux((self.v == 1), self.result_y, 0))

        @self.seq(self.clk, self.rstn, reset_async=True, reset_active_low=True)
        def _seq_logic():
            with If((~self.rstn)):
                self.state <<= 0
            with Else():
                with If(self.go):
                    self.state <<= 1
                with Else():
                    with If(self.valid):
                        self.state <<= 0
