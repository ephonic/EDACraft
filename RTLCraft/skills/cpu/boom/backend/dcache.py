"""
BOOM D-Cache

Simple direct-mapped data cache with single MSHR.
- num_sets: number of cache sets (direct-mapped)
- Each set stores one 32-bit word + valid bit + tag
- Write-through for stores (always write to memory)
- Load miss allocates cache line from memory

Simplifications:
- No write-back (write-through only)
- Single MSHR (serial miss handling)
- No eviction dirty bit tracking
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Reg, Wire
from rtlgen.logic import If, Else, Mux


class DCache(Module):
    """Direct-mapped data cache with single MSHR."""

    def __init__(self, xlen: int = 32, num_sets: int = 4, name: str = "DCache"):
        super().__init__(name)
        self.xlen = xlen
        self.num_sets = num_sets
        self.index_bits = max(num_sets.bit_length() - 1, 1)
        self.offset_bits = 2  # byte offset within word
        self.tag_bits = xlen - self.index_bits - self.offset_bits

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # LSU interface
        self.req_valid = Input(1, "req_valid")
        self.req_addr = Input(xlen, "req_addr")
        self.req_we = Input(1, "req_we")
        self.req_wdata = Input(xlen, "req_wdata")
        self.resp_valid = Output(1, "resp_valid")
        self.resp_data = Output(xlen, "resp_data")
        self.ready = Output(1, "ready")

        # Memory interface
        self.mem_req_valid = Output(1, "mem_req_valid")
        self.mem_req_addr = Output(xlen, "mem_req_addr")
        self.mem_req_we = Output(1, "mem_req_we")
        self.mem_req_wdata = Output(xlen, "mem_req_wdata")
        self.mem_resp_valid = Input(1, "mem_resp_valid")
        self.mem_resp_data = Input(xlen, "mem_resp_data")

        # Cache arrays
        self.valid = [Reg(1, f"v{i}") for i in range(num_sets)]
        self.tags = [Reg(self.tag_bits, f"tag{i}") for i in range(num_sets)]
        self.data = [Reg(xlen, f"d{i}") for i in range(num_sets)]

        # MSHR
        self.mshr_valid = Reg(1, "mshr_valid")
        self.mshr_addr = Reg(xlen, "mshr_addr")

        # Address decode
        addr = self.req_addr
        # index = addr[index_bits+1:2], tag = addr[xlen-1:index_bits+2]
        # Use helper wires for index/tag
        self.index_wire = Wire(self.index_bits, "index_wire")
        self.tag_wire = Wire(self.tag_bits, "tag_wire")

        @self.comb
        def _decode():
            self.index_wire <<= addr[self.index_bits + 1:2]
            self.tag_wire <<= addr[xlen - 1:self.index_bits + 2]

        # Hit detection
        self.hit = Wire(1, "hit")

        @self.comb
        def _hit():
            self.hit <<= 0
            for i in range(num_sets):
                with If((self.index_wire == i) & self.valid[i] & (self.tags[i] == self.tag_wire)):
                    self.hit <<= 1

        # Cache read
        self.cache_data = Wire(xlen, "cache_data")

        @self.comb
        def _read():
            self.cache_data <<= 0
            for i in range(num_sets):
                with If(self.index_wire == i):
                    self.cache_data <<= self.data[i]

        # State machine: 0=IDLE, 1=MISS_WAIT
        self.state = Reg(2, "state")

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq():
            with If(self.rst_n == 0):
                for i in range(num_sets):
                    self.valid[i] <<= 0
                self.mshr_valid <<= 0
                self.state <<= 0
            with Else():
                with If(self.state == 0):
                    with If(self.req_valid & ~self.hit & ~self.mshr_valid & ~self.req_we):
                        # Load miss: allocate MSHR
                        self.state <<= 1
                        self.mshr_valid <<= 1
                        self.mshr_addr <<= addr

                with If(self.state == 1):
                    with If(self.mem_resp_valid):
                        # Fill cache from memory response
                        for i in range(num_sets):
                            with If(self.index_wire == i):
                                self.valid[i] <<= 1
                                self.tags[i] <<= self.tag_wire
                                self.data[i] <<= self.mem_resp_data
                        self.state <<= 0
                        self.mshr_valid <<= 0

        # Write-through for stores (update cache on hit)
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _write_hit():
            with If(self.rst_n != 0):
                with If(self.req_valid & self.hit & self.req_we):
                    for i in range(num_sets):
                        with If(self.index_wire == i):
                            self.data[i] <<= self.req_wdata

        # Outputs
        self.resp_valid <<= (self.state == 0) & self.req_valid & self.hit
        self.resp_data <<= self.cache_data
        self.ready <<= (self.state == 0) & ~self.mshr_valid

        # Memory request: store always goes to mem; load miss also goes to mem
        self.mem_req_valid <<= (self.req_valid & self.req_we) | self.mshr_valid
        self.mem_req_addr <<= Mux(self.mshr_valid, self.mshr_addr, addr)
        self.mem_req_we <<= self.req_we
        self.mem_req_wdata <<= self.req_wdata
