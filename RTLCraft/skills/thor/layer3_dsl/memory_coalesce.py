"""Thor GPU — Memory Coalesce L3 DSL. Merge warp lane addresses to cache lines.
Detects which lanes access the same 64B cache line and merges them.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg
from rtlgen.logic import If, Else

from skills.thor import NLANE, XLEN


class MemoryCoalesce(Module):
    def __init__(self):
        super().__init__("memory_coalesce")
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.lane_addr = [Input(32, f"lane_addr_{i}") for i in range(NLANE)]
        self.lane_valid = Input(NLANE, "lane_valid")
        self.lane_wen = [Input(1, f"lane_wen_{i}") for i in range(NLANE)]
        self.lane_wdata = [Input(32, f"lane_wdata_{i}") for i in range(NLANE)]
        self.coalesced_addr = Output(32, "coalesced_addr")
        self.coalesced_mask = Output(64, "coalesced_mask")
        self.coalesced_wdata = Output(512, "coalesced_wdata")
        self.num_transactions = Output(4, "num_transactions")

        # Group lane addresses by cache line (64B alignment)
        line_bits = 6  # 2^6 = 64B
        line_w = 32 - line_bits

        lane_line = [Wire(line_w, f"ll_{i}") for i in range(NLANE)]
        lane_off = [Wire(line_bits, f"lo_{i}") for i in range(NLANE)]
        with self.comb:
            for i in range(NLANE):
                lane_line[i] <<= self.lane_addr[i] >> line_bits
                lane_off[i] <<= self.lane_addr[i] & ((1 << line_bits) - 1)

        # Count unique cache lines among valid lanes
        base_line = Wire(line_w, "base_line"); n_unique = Wire(4, "n_unique")
        mask = Wire(64, "c_mask"); wdata = Wire(512, "c_wdata")
        with self.comb:
            base_line <<= lane_line[0]
            n_unique <<= 1
            mask <<= 0
            wdata <<= 0
            for i in range(NLANE):
                with If(self.lane_valid[i]):
                    off = lane_off[i]
                    word_idx = off // 4
                    mask[word_idx * 4 + 3:word_idx * 4] <<= 0xF
                    wdata[i * 32 + 31:i * 32] <<= self.lane_wdata[i]
            for i in range(1, NLANE):
                with If(self.lane_valid[i] & (lane_line[i] != lane_line[0])):
                    n_unique <<= n_unique + 1

        with self.comb:
            self.coalesced_addr <<= base_line << line_bits
            self.coalesced_mask <<= mask
            self.coalesced_wdata <<= wdata
            self.num_transactions <<= n_unique
