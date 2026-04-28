"""
GPGPU Memory Subsystem —?Coalescer + L1 Cache + Shared Memory

MemoryCoalescer:
  - Takes per-lane addresses from a warp
  - Groups contiguous addresses into wide burst requests
  - Output: up to N coalesced requests per cycle

L1Cache:
  - Set-associative data cache
  - Handles coalesced requests from coalescer
  - On miss: forwards to L2 / global memory

SharedMemory:
  - Dedicated on-chip scratchpad for LDS/STS
  - Banked to support parallel access
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from rtlgen import Module, Input, Output, Reg, Wire, Memory, Array
from rtlgen.logic import If, Else, Mux

from skills.gpgpu.common.params import GPGPUParams


class MemoryCoalescer(Module):
    """Warp-level memory address coalescing unit."""

    def __init__(self, params: GPGPUParams = None, name: str = "MemoryCoalescer"):
        super().__init__(name)
        if params is None:
            params = GPGPUParams()
        self.params = params
        self.warp_size = params.warp_size
        self.addr_width = 32
        self.data_width = params.data_width
        self.coalescer_width = params.coalescer_width  # 128 bits = 4×32-bit words
        self.words_per_req = self.coalescer_width // self.data_width  # 4

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Request from execution unit
        self.req_valid = Input(1, "req_valid")
        self.req_is_store = Input(1, "req_is_store")
        self.req_addr = [Input(self.addr_width, f"req_addr_{i}") for i in range(self.warp_size)]
        self.req_data = [Input(self.data_width, f"req_data_{i}") for i in range(self.warp_size)]
        self.req_mask = Input(self.warp_size, "req_mask")

        # Coalesced output to L1 / global memory
        self.out_valid = Output(1, "out_valid")
        self.out_is_store = Output(1, "out_is_store")
        self.out_addr = Output(self.addr_width, "out_addr")
        self.out_data = [Output(self.data_width, f"out_data_{i}") for i in range(self.words_per_req)]
        self.out_mask = Output(self.words_per_req, "out_mask")
        self.out_done = Output(1, "out_done")

        # Coalescing state
        self.coal_state = Reg(1, "coal_state")
        self.lane_ptr = Reg(max((self.warp_size - 1).bit_length(), 1), "lane_ptr")

        # Detect contiguous run starting from lane_ptr
        self.base_addr = Wire(self.addr_width, "base_addr")
        self.run_len = Wire(max((self.words_per_req + 1).bit_length(), 1), "run_len")
        self.run_mask = Wire(self.words_per_req, "run_mask")

        def _mux_list(items, sel):
            result = items[0]
            for i in range(1, len(items)):
                result = Mux(sel == i, items[i], result)
            return result

        @self.comb
        def _detect_run():
            base = _mux_list(self.req_addr, self.lane_ptr)
            self.base_addr <<= base
            len_run = 0
            mask_run = 0
            for i in range(self.words_per_req):
                lane = self.lane_ptr + i
                with If(lane < self.warp_size):
                    expected = base + (i * (self.data_width // 8))
                    req_addr_lane = _mux_list(self.req_addr, lane)
                    req_mask_lane = self.req_mask[lane]  # bit-select on multi-bit signal
                    match = (req_addr_lane == expected) & req_mask_lane
                    with If(match):
                        len_run = len_run + 1
                        mask_run = mask_run | (1 << i)
            self.run_len <<= len_run
            self.run_mask <<= mask_run

        # Sequential: emit coalesced requests
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _emit():
            with If(self.rst_n == 0):
                self.coal_state <<= 0
                self.lane_ptr <<= 0
            with Else():
                with If(self.coal_state == 0):
                    with If(self.req_valid):
                        self.coal_state <<= 1
                        self.lane_ptr <<= 0
                with Else():
                    with If(self.lane_ptr + self.run_len >= self.warp_size):
                        self.coal_state <<= 0
                        self.lane_ptr <<= 0
                    with Else():
                        self.lane_ptr <<= self.lane_ptr + self.run_len

        # Output assignments
        self.out_valid <<= (self.coal_state == 1) & (self.run_len > 0)
        self.out_is_store <<= self.req_is_store
        self.out_addr <<= self.base_addr
        self.out_mask <<= self.run_mask
        self.out_done <<= (self.coal_state == 1) & (self.lane_ptr + self.run_len >= self.warp_size)

        for i in range(self.words_per_req):
            lane = self.lane_ptr + i
            with If(lane < self.warp_size):
                self.out_data[i] <<= _mux_list(self.req_data, lane)
            with Else():
                self.out_data[i] <<= 0


class L1Cache(Module):
    """Set-associative L1 data cache."""

    def __init__(self, params: GPGPUParams = None, name: str = "L1Cache"):
        super().__init__(name)
        if params is None:
            params = GPGPUParams()
        self.params = params
        self.line_size = params.l1_line_size
        self.sets = params.l1_sets
        self.ways = params.l1_ways
        self.data_width = params.data_width
        self.addr_width = 32
        self.set_width = max((self.sets - 1).bit_length(), 1)
        self.way_width = max((self.ways - 1).bit_length(), 1)
        self.tag_width = self.addr_width - self.set_width - (self.line_size.bit_length() - 1)

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Request interface
        self.req_valid = Input(1, "req_valid")
        self.req_is_store = Input(1, "req_is_store")
        self.req_addr = Input(self.addr_width, "req_addr")
        self.req_data = Input(self.data_width, "req_data")
        self.req_mask = Input(self.data_width // 8, "req_mask")

        # Response interface
        self.resp_valid = Output(1, "resp_valid")
        self.resp_data = Output(self.data_width, "resp_data")
        self.resp_miss = Output(1, "resp_miss")

        # Miss interface to L2
        self.miss_valid = Output(1, "miss_valid")
        self.miss_addr = Output(self.addr_width, "miss_addr")
        self.fill_valid = Input(1, "fill_valid")
        self.fill_addr = Input(self.addr_width, "fill_addr")
        self.fill_data = [Input(self.data_width, f"fill_data_{i}") for i in range(self.line_size // (self.data_width // 8))]

        # Cache arrays
        self.tags = [
            [Reg(self.tag_width, f"tag_s{s}_w{w}") for w in range(self.ways)]
            for s in range(self.sets)
        ]
        self.valid = [
            [Reg(1, f"valid_s{s}_w{w}") for w in range(self.ways)]
            for s in range(self.sets)
        ]
        self.data = [
            [
                Memory(self.data_width, self.line_size // (self.data_width // 8), f"data_s{s}_w{w}")
                for w in range(self.ways)
            ]
            for s in range(self.sets)
        ]
        for s in range(self.sets):
            for w in range(self.ways):
                self.add_memory(self.data[s][w], f"data_s{s}_w{w}")

        # Address decomposition
        self.req_set = Wire(self.set_width, "req_set")
        self.req_tag = Wire(self.tag_width, "req_tag")
        self.req_offset = Wire(self.line_size.bit_length() - 1, "req_offset")

        @self.comb
        def _decompose():
            offset_bits = self.line_size.bit_length() - 1
            self.req_offset <<= self.req_addr[offset_bits - 1:0] if offset_bits > 0 else 0
            self.req_set <<= (self.req_addr >> offset_bits) & ((1 << self.set_width) - 1) if self.set_width > 0 else 0
            self.req_tag <<= self.req_addr >> (offset_bits + self.set_width)

        # Hit detection
        self.hit = Wire(1, "hit")
        self.hit_way = Wire(self.way_width, "hit_way")
        self.hit_data = Wire(self.data_width, "hit_data")

        @self.comb
        def _hit_detect():
            hit = 0
            way = 0
            data = 0
            for s in range(self.sets):
                for w in range(self.ways):
                    with If((self.req_set == s) & self.valid[s][w] & (self.tags[s][w] == self.req_tag)):
                        hit = 1
                        way = w
                        data = self.data[s][w][self.req_offset]
            self.hit <<= hit
            self.hit_way <<= way
            self.hit_data <<= data

        # State machine
        self.state = Reg(2, "state")
        ST_IDLE = 0
        ST_MISS = 1
        ST_FILL = 2

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _fsm():
            with If(self.rst_n == 0):
                self.state <<= ST_IDLE
                for s in range(self.sets):
                    for w in range(self.ways):
                        self.valid[s][w] <<= 0
            with Else():
                with If(self.state == ST_IDLE):
                    with If(self.req_valid):
                        with If(self.hit):
                            self.state <<= ST_IDLE
                        with Else():
                            self.state <<= ST_MISS

                with If(self.state == ST_MISS):
                    self.miss_valid <<= 1
                    self.miss_addr <<= self.req_addr
                    with If(self.fill_valid):
                        self.miss_valid <<= 0
                        self.state <<= ST_FILL

                with If(self.state == ST_FILL):
                    # Simple direct-map fill (way 0)
                    for s in range(self.sets):
                        with If(self.req_set == s):
                            self.valid[s][0] <<= 1
                            self.tags[s][0] <<= self.req_tag
                            for i in range(self.line_size // (self.data_width // 8)):
                                self.data[s][0][i] <<= self.fill_data[i]
                    self.state <<= ST_IDLE

        self.resp_valid <<= self.req_valid & self.hit & (self.state == ST_IDLE)
        self.resp_data <<= self.hit_data
        self.resp_miss <<= self.req_valid & ~self.hit & (self.state == ST_IDLE)


class SharedMemory(Module):
    """Banked shared memory scratchpad for LDS/STS instructions."""

    def __init__(self, params: GPGPUParams = None, name: str = "SharedMemory"):
        super().__init__(name)
        if params is None:
            params = GPGPUParams()
        self.params = params
        self.size = params.shared_mem_size
        self.data_width = params.data_width
        self.addr_width = max((self.size - 1).bit_length(), 1)
        self.num_banks = 16
        self.bank_addr_width = max(((self.size // self.num_banks) - 1).bit_length(), 1)

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Read port
        self.rd_addr = Input(self.addr_width, "rd_addr")
        self.rd_valid = Input(1, "rd_valid")
        self.rd_data = Output(self.data_width, "rd_data")

        # Write port
        self.wr_addr = Input(self.addr_width, "wr_addr")
        self.wr_data = Input(self.data_width, "wr_data")
        self.wr_en = Input(1, "wr_en")

        # Banked memory
        self.banks = [
            Memory(self.data_width, self.size // self.num_banks, f"bank_{i}")
            for i in range(self.num_banks)
        ]
        for i in range(self.num_banks):
            self.add_memory(self.banks[i], f"bank_{i}")

        # Bank select
        self.bank_sel = Wire(max((self.num_banks - 1).bit_length(), 1), "bank_sel")
        self.bank_addr = Wire(self.bank_addr_width, "bank_addr")

        @self.comb
        def _bank_decode():
            bank_bits = max((self.num_banks - 1).bit_length(), 1)
            self.bank_sel <<= self.rd_addr[bank_bits - 1:0] if bank_bits > 0 else 0
            self.bank_addr <<= self.rd_addr >> bank_bits

        def _mux_list(items, sel):
            result = items[0]
            for i in range(1, len(items)):
                result = Mux(sel == i, items[i], result)
            return result

        # Sequential read/write
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _access():
            for i in range(self.num_banks):
                with If(self.bank_sel == i):
                    with If(self.wr_en):
                        self.banks[i][self.bank_addr] <<= self.wr_data

        bank_reads = [self.banks[i][self.bank_addr] for i in range(self.num_banks)]
        self.rd_data <<= _mux_list(bank_reads, self.bank_sel)
