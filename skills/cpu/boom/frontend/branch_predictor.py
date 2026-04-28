"""
Simplified Branch Predictor for BOOM

- BHT (Branch History Table): 2-bit saturating counters
- BTB (Branch Target Buffer): direct-mapped target cache
- RAS (Return Address Stack): simple stack for JALR returns
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Reg, Wire, Parameter
from rtlgen.logic import If, Else, Mux


class BranchPredictor(Module):
    """Combined BHT + BTB + RAS branch predictor.

    Ports
    -----
    clk, rst_n          : clock and async active-low reset
    pc                  : current PC to predict
    predict_valid       : prediction request
    predict_taken       : predicted direction (BHT)
    predict_target      : predicted target (BTB or PC+4)
    predict_is_ret      : predicted return instruction

    update_valid        : branch resolution update
    update_pc           : PC of resolved branch
    update_taken        : actual direction
    update_target       : actual target
    update_mispredict   : whether prediction was wrong
    """

    def __init__(self, bht_entries: int = 64, btb_entries: int = 16, ras_depth: int = 8, xlen: int = 32, name: str = "BranchPredictor"):
        super().__init__(name)
        self.xlen = xlen
        self.bht_addr_w = max(bht_entries.bit_length(), 1)
        self.btb_addr_w = max(btb_entries.bit_length(), 1)
        self.ras_depth = ras_depth

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Predict interface
        self.pc = Input(xlen, "pc")
        self.predict_valid = Input(1, "predict_valid")
        self.predict_taken = Output(1, "predict_taken")
        self.predict_target = Output(xlen, "predict_target")
        self.predict_is_ret = Output(1, "predict_is_ret")

        # Update interface
        self.update_valid = Input(1, "update_valid")
        self.update_pc = Input(xlen, "update_pc")
        self.update_taken = Input(1, "update_taken")
        self.update_target = Input(xlen, "update_target")
        self.update_is_branch = Input(1, "update_is_branch")
        self.update_is_ret = Input(1, "update_is_ret")
        self.update_is_call = Input(1, "update_is_call")
        self.update_mispredict = Input(1, "update_mispredict")

        # BHT: 2-bit saturating counters
        self.bht = [Reg(2, f"bht_{i}") for i in range(bht_entries)]
        bht_idx = self.pc[self.bht_addr_w:0]
        self.bht_val = Wire(2, "bht_val")

        @self.comb
        def _bht_read():
            self.bht_val <<= self.bht[0]  # default
            for i in range(bht_entries):
                with If(bht_idx == i):
                    self.bht_val <<= self.bht[i]

        self.predict_taken <<= (self.bht_val[1] == 1) & self.predict_valid

        # BTB: direct-mapped target cache
        self.btb_valid = [Reg(1, f"btb_v{i}") for i in range(btb_entries)]
        self.btb_tag = [Reg(self.btb_addr_w, f"btb_tag_{i}") for i in range(btb_entries)]
        self.btb_data = [Reg(xlen, f"btb_data_{i}") for i in range(btb_entries)]
        btb_idx = self.pc[self.btb_addr_w:0]
        btb_tag = self.pc[2 * self.btb_addr_w:self.btb_addr_w]

        self.btb_hit = Wire(1, "btb_hit")
        self.btb_target = Wire(xlen, "btb_target")

        @self.comb
        def _btb_read():
            self.btb_hit <<= 0
            self.btb_target <<= (self.pc + 4)
            for i in range(btb_entries):
                with If((btb_idx == i) & self.btb_valid[i] & (self.btb_tag[i] == btb_tag)):
                    self.btb_hit <<= 1
                    self.btb_target <<= self.btb_data[i]

        self.predict_target <<= Mux(self.btb_hit, self.btb_target, self.pc + 4)

        # RAS
        self.ras_stack = [Reg(xlen, f"ras_{i}") for i in range(ras_depth)]
        self.ras_ptr = Reg(max(ras_depth.bit_length(), 1), "ras_ptr")

        self.predict_is_ret <<= 0  # simplified

        # Update logic
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _update():
            with If(self.rst_n == 0):
                for r in self.bht:
                    r <<= 1  # weakly not-taken
                for r in self.btb_valid:
                    r <<= 0
                self.ras_ptr <<= 0
            with Else():
                with If(self.update_valid & self.update_is_branch):
                    # Update BHT
                    self.upd_idx = self.update_pc[self.bht_addr_w:0]
                    for i in range(bht_entries):
                        with If(self.upd_idx == i):
                            with If(self.update_taken):
                                with If(self.bht[i] < 3):
                                    self.bht[i] <<= self.bht[i] + 1
                            with Else():
                                with If(self.bht[i] > 0):
                                    self.bht[i] <<= self.bht[i] - 1

                    # Update BTB
                    self.t_idx = self.update_pc[self.btb_addr_w:0]
                    self.t_tag = self.update_pc[2 * self.btb_addr_w:self.btb_addr_w]
                    for i in range(btb_entries):
                        with If(self.t_idx == i):
                            self.btb_valid[i] <<= 1
                            self.btb_tag[i] <<= self.t_tag
                            self.btb_data[i] <<= self.update_target
