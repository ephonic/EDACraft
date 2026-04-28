"""
GPGPU Frontend —?Instruction fetch + decode

Contains a simple direct-mapped instruction cache and a decoder
that extracts fields from the 64-bit ISA format.

Fetch -> Decode -> Dispatch
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from rtlgen import Module, Input, Output, Reg, Wire, Memory
from rtlgen.logic import If, Else, Mux

from skills.gpgpu.common import isa
from skills.gpgpu.common.params import GPGPUParams


class Frontend(Module):
    """Instruction fetch and decode unit."""

    def __init__(self, params: GPGPUParams = None, name: str = "Frontend"):
        super().__init__(name)
        if params is None:
            params = GPGPUParams()
        self.params = params
        self.pc_width = 16
        self.warp_id_width = max((params.num_warps - 1).bit_length(), 1)
        self.inst_width = params.max_instr_len  # 64 bits
        self.icache_sets = params.icache_sets
        self.icache_ways = params.icache_ways
        self.icache_line_size = params.icache_line_size
        self.icache_depth = (self.icache_sets * self.icache_ways * self.icache_line_size) // (self.inst_width // 8)
        self.icache_addr_width = max(self.icache_depth.bit_length(), 1)

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # -----------------------------------------------------------------
        # Fetch request from scheduler
        # -----------------------------------------------------------------
        self.fetch_valid = Input(1, "fetch_valid")
        self.fetch_warp = Input(self.warp_id_width, "fetch_warp")
        self.fetch_pc = Input(self.pc_width, "fetch_pc")
        self.fetch_ready = Output(1, "fetch_ready")

        # -----------------------------------------------------------------
        # Instruction memory interface (for cache fill / direct access)
        # -----------------------------------------------------------------
        self.imem_req_valid = Output(1, "imem_req_valid")
        self.imem_req_addr = Output(self.pc_width, "imem_req_addr")
        self.imem_resp_valid = Input(1, "imem_resp_valid")
        self.imem_resp_data = Input(self.inst_width, "imem_resp_data")

        # -----------------------------------------------------------------
        # Decoded instruction output
        # -----------------------------------------------------------------
        self.dec_valid = Output(1, "dec_valid")
        self.dec_warp = Output(self.warp_id_width, "dec_warp")
        self.dec_pc = Output(self.pc_width, "dec_pc")
        self.dec_opcode = Output(6, "dec_opcode")
        self.dec_func = Output(6, "dec_func")
        self.dec_dst = Output(6, "dec_dst")
        self.dec_src_a = Output(6, "dec_src_a")
        self.dec_src_b = Output(6, "dec_src_b")
        self.dec_src_c = Output(6, "dec_src_c")
        self.dec_pred_use = Output(1, "dec_pred_use")
        self.dec_pred_reg = Output(5, "dec_pred_reg")
        self.dec_pred_neg = Output(1, "dec_pred_neg")
        self.dec_unit = Output(3, "dec_unit")
        self.dec_imm = Output(18, "dec_imm")

        # -----------------------------------------------------------------
        # Simple instruction cache (direct mapped for MVP)
        # -----------------------------------------------------------------
        self.icache_tag_depth = self.icache_sets
        self.icache_tag = [Reg(self.pc_width - self.icache_addr_width, f"icache_tag_{i}") for i in range(self.icache_sets)]
        self.icache_valid = [Reg(1, f"icache_valid_{i}") for i in range(self.icache_sets)]
        self.icache_data = Memory(self.inst_width, self.icache_sets, "icache_data")
        self.add_memory(self.icache_data, "icache_data")

        # -----------------------------------------------------------------
        # Fetch FSM
        # -----------------------------------------------------------------
        self.state = Reg(2, "state")
        ST_IDLE = 0
        ST_CHECK = 1
        ST_MISS = 2
        ST_DECODE = 3

        self.fetch_warp_r = Reg(self.warp_id_width, "fetch_warp_r")
        self.fetch_pc_r = Reg(self.pc_width, "fetch_pc_r")
        self.inst_r = Reg(self.inst_width, "inst_r")

        # Cache index / tag
        self.cache_idx = Wire(self.icache_addr_width, "cache_idx")
        self.cache_tag = Wire(self.pc_width - self.icache_addr_width, "cache_tag")
        self.cache_hit = Wire(1, "cache_hit")

        def _mux_list(items, sel):
            result = items[0]
            for i in range(1, len(items)):
                result = Mux(sel == i, items[i], result)
            return result

        @self.comb
        def _cache_lookup():
            idx_bits = self.icache_addr_width
            self.cache_idx <<= self.fetch_pc_r[idx_bits - 1:0] if idx_bits > 0 else 0
            self.cache_tag <<= self.fetch_pc_r >> idx_bits if idx_bits > 0 else self.fetch_pc_r
            tag_match = _mux_list(self.icache_tag, self.cache_idx) == self.cache_tag
            valid = _mux_list(self.icache_valid, self.cache_idx)
            self.cache_hit <<= valid & tag_match

        # -----------------------------------------------------------------
        # Sequential FSM
        # -----------------------------------------------------------------
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _fsm():
            with If(self.rst_n == 0):
                self.state <<= ST_IDLE
                self.fetch_warp_r <<= 0
                self.fetch_pc_r <<= 0
                for i in range(self.icache_sets):
                    self.icache_valid[i] <<= 0
            with Else():
                with If(self.state == ST_IDLE):
                    with If(self.fetch_valid):
                        self.state <<= ST_CHECK
                        self.fetch_warp_r <<= self.fetch_warp
                        self.fetch_pc_r <<= self.fetch_pc

                with If(self.state == ST_CHECK):
                    with If(self.cache_hit):
                        self.inst_r <<= self.icache_data[self.cache_idx]
                        self.state <<= ST_DECODE
                    with Else():
                        self.state <<= ST_MISS
                        self.imem_req_valid <<= 1
                        self.imem_req_addr <<= self.fetch_pc_r

                with If(self.state == ST_MISS):
                    self.imem_req_valid <<= 0
                    with If(self.imem_resp_valid):
                        self.inst_r <<= self.imem_resp_data
                        # Fill cache
                        self.icache_data[self.cache_idx] <<= self.imem_resp_data
                        for s in range(self.icache_sets):
                            with If(self.cache_idx == s):
                                self.icache_tag[s] <<= self.cache_tag
                                self.icache_valid[s] <<= 1
                        self.state <<= ST_DECODE

                with If(self.state == ST_DECODE):
                    self.state <<= ST_IDLE

        # -----------------------------------------------------------------
        # Combinational decode
        # -----------------------------------------------------------------
        @self.comb
        def _decode():
            inst = self.inst_r
            self.dec_opcode <<= (inst >> 58) & 0x3F
            self.dec_func <<= (inst >> 52) & 0x3F
            self.dec_dst <<= (inst >> 46) & 0x3F
            self.dec_src_a <<= (inst >> 40) & 0x3F
            self.dec_src_b <<= (inst >> 34) & 0x3F
            self.dec_src_c <<= (inst >> 28) & 0x3F
            self.dec_pred_use <<= (inst >> 27) & 0x1
            self.dec_pred_reg <<= (inst >> 22) & 0x1F
            self.dec_pred_neg <<= (inst >> 21) & 0x1
            self.dec_unit <<= (inst >> 18) & 0x7
            self.dec_imm <<= ((inst >> 10) & 0xFF) << 10 | (inst & 0x3FF)

        self.dec_valid <<= (self.state == ST_DECODE)
        self.dec_warp <<= self.fetch_warp_r
        self.dec_pc <<= self.fetch_pc_r
        self.fetch_ready <<= (self.state == ST_IDLE)
