"""
BOOM Load/Store Unit (LSU)

Handles out-of-order loads and stores with:
- Load Queue (LQ): tracks in-flight loads
- Store Queue (SQ): buffers stores until commit
- Store-to-load forwarding

Simplifications:
- No cache, direct memory interface
- No MMU
- Single memory port
"""

import sys
sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Module, Input, Output, Reg, Wire
from rtlgen.logic import If, Else, Mux


class LSU(Module):
    """Load/Store Unit with store queue and load queue."""

    def __init__(
        self,
        xlen: int = 32,
        lq_entries: int = 8,
        sq_entries: int = 8,
        name: str = "LSU",
    ):
        super().__init__(name)
        self.xlen = xlen
        self.lq_entries = lq_entries
        self.lq_bits = max(lq_entries.bit_length(), 1)
        self.sq_entries = sq_entries
        self.sq_bits = max(sq_entries.bit_length(), 1)

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Dispatch / Issue interface
        self.issue_valid = Input(1, "issue_valid")
        self.issue_is_load = Input(1, "issue_is_load")
        self.issue_addr = Input(xlen, "issue_addr")
        self.issue_wdata = Input(xlen, "issue_wdata")
        self.issue_size = Input(2, "issue_size")
        self.issue_signed = Input(1, "issue_signed")
        self.issue_sq_idx = Input(self.sq_bits, "issue_sq_idx")
        self.issue_ready = Output(1, "issue_ready")

        # Commit interface
        self.commit_valid = Input(1, "commit_valid")
        self.commit_sq_idx = Input(self.sq_bits, "commit_sq_idx")

        # Memory interface
        self.mem_req_valid = Output(1, "mem_req_valid")
        self.mem_req_addr = Output(xlen, "mem_req_addr")
        self.mem_req_wdata = Output(xlen, "mem_req_wdata")
        self.mem_req_we = Output(1, "mem_req_we")
        self.mem_req_size = Output(2, "mem_req_size")
        self.mem_resp_valid = Input(1, "mem_resp_valid")
        self.mem_resp_data = Input(xlen, "mem_resp_data")

        # Writeback
        self.wb_valid = Output(1, "wb_valid")
        self.wb_data = Output(xlen, "wb_data")
        self.wb_lq_idx = Output(self.lq_bits, "wb_lq_idx")

        # Store-to-load forwarding
        self.forward_valid = Output(1, "forward_valid")
        self.forward_data = Output(xlen, "forward_data")

        # Store Queue
        self.sq_valid = [Reg(1, f"sq_v{i}") for i in range(sq_entries)]
        self.sq_addr = [Reg(xlen, f"sq_a{i}") for i in range(sq_entries)]
        self.sq_data = [Reg(xlen, f"sq_d{i}") for i in range(sq_entries)]
        self.sq_size = [Reg(2, f"sq_sz{i}") for i in range(sq_entries)]
        self.sq_committed = [Reg(1, f"sq_c{i}") for i in range(sq_entries)]
        self.sq_head = Reg(self.sq_bits, "sq_head")
        self.sq_tail = Reg(self.sq_bits, "sq_tail")
        self.sq_count = Reg(self.sq_bits + 1, "sq_count")

        # Load Queue
        self.lq_valid = [Reg(1, f"lq_v{i}") for i in range(lq_entries)]
        self.lq_addr = [Reg(xlen, f"lq_a{i}") for i in range(lq_entries)]
        self.lq_size = [Reg(2, f"lq_sz{i}") for i in range(lq_entries)]
        self.lq_signed = [Reg(1, f"lq_sg{i}") for i in range(lq_entries)]
        self.lq_done = [Reg(1, f"lq_dn{i}") for i in range(lq_entries)]
        self.lq_head = Reg(self.lq_bits, "lq_head")
        self.lq_tail = Reg(self.lq_bits, "lq_tail")
        self.lq_count = Reg(self.lq_bits + 1, "lq_count")

        # Space check
        self.issue_ready <<= (self.sq_count < sq_entries) & (self.lq_count < lq_entries)

        # Store-to-load forwarding (simplified: not fully implemented)
        self.forward_valid <<= 0
        self.forward_data <<= 0

        # Memory request arbitration: prioritize committed stores, then loads
        self.mem_req_store = Wire(1, "mem_req_store")
        self.mem_req_load = Wire(1, "mem_req_load")
        self.selected_sq = Wire(self.sq_bits, "selected_sq")
        self.selected_lq = Wire(self.lq_bits, "selected_lq")
        self.selected_lq_size = Wire(2, "selected_lq_size")
        self.selected_lq_signed = Wire(1, "selected_lq_signed")

        @self.comb
        def _arbitrate():
            self.mem_req_store <<= 0
            self.mem_req_load <<= 0
            self.selected_sq <<= 0
            self.selected_lq <<= 0
            self.selected_lq_size <<= 0
            self.selected_lq_signed <<= 0

            # Committed stores first
            for i in range(sq_entries):
                with If(self.sq_valid[i] & self.sq_committed[i] & ~self.mem_req_store):
                    self.mem_req_store <<= 1
                    self.selected_sq <<= i

            # Then ready loads
            with If(~self.mem_req_store):
                for i in range(lq_entries):
                    with If(self.lq_valid[i] & ~self.lq_done[i] & ~self.mem_req_load):
                        self.mem_req_load <<= 1
                        self.selected_lq <<= i
                        self.selected_lq_size <<= self.lq_size[i]
                        self.selected_lq_signed <<= self.lq_signed[i]

            self.mem_req_valid <<= self.mem_req_load | self.mem_req_store
            self.mem_req_we <<= self.mem_req_store
            self.mem_req_addr <<= 0
            self.mem_req_wdata <<= 0
            self.mem_req_size <<= 0

            for i in range(sq_entries):
                with If(self.selected_sq == i):
                    self.mem_req_addr <<= self.sq_addr[i]
                    self.mem_req_wdata <<= self.sq_data[i]
                    self.mem_req_size <<= self.sq_size[i]

            for i in range(lq_entries):
                with If(self.selected_lq == i):
                    self.mem_req_addr <<= self.lq_addr[i]
                    self.mem_req_size <<= self.lq_size[i]

        # Writeback
        self.wb_valid <<= self.mem_resp_valid & self.mem_req_load
        self.wb_lq_idx <<= self.selected_lq

        # Load response sign/zero extension
        self.wb_byte = Wire(xlen, "wb_byte")
        self.wb_half = Wire(xlen, "wb_half")
        self.wb_byte_sext = Wire(xlen, "wb_byte_sext")
        self.wb_half_sext = Wire(xlen, "wb_half_sext")

        @self.comb
        def _extend():
            self.wb_byte <<= self.mem_resp_data[7:0]
            self.wb_half <<= self.mem_resp_data[15:0]
            self.wb_byte_sext <<= self.wb_byte | (((1 << (xlen - 8)) - 1) << 8)
            self.wb_half_sext <<= self.wb_half | (((1 << (xlen - 16)) - 1) << 16)

            self.wb_data <<= self.mem_resp_data
            with If(self.selected_lq_size == 0):
                self.wb_data <<= Mux(self.selected_lq_signed, self.wb_byte_sext, self.wb_byte)
            with Else():
                with If(self.selected_lq_size == 1):
                    self.wb_data <<= Mux(self.selected_lq_signed, self.wb_half_sext, self.wb_half)

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _seq():
            with If(self.rst_n == 0):
                self.sq_head <<= 0
                self.sq_tail <<= 0
                self.sq_count <<= 0
                self.lq_head <<= 0
                self.lq_tail <<= 0
                self.lq_count <<= 0
                for i in range(sq_entries):
                    self.sq_valid[i] <<= 0
                    self.sq_committed[i] <<= 0
                for i in range(lq_entries):
                    self.lq_valid[i] <<= 0
                    self.lq_done[i] <<= 0
            with Else():
                # Dispatch into SQ / LQ
                with If(self.issue_valid & self.issue_ready):
                    with If(self.issue_is_load):
                        for i in range(lq_entries):
                            with If(self.lq_tail == i):
                                self.lq_valid[i] <<= 1
                                self.lq_done[i] <<= 0
                                self.lq_addr[i] <<= self.issue_addr
                                self.lq_size[i] <<= self.issue_size
                                self.lq_signed[i] <<= self.issue_signed
                        self.lq_tail <<= self.lq_tail + 1
                        self.lq_count <<= self.lq_count + 1
                    with Else():
                        for i in range(sq_entries):
                            with If(self.sq_tail == i):
                                self.sq_valid[i] <<= 1
                                self.sq_committed[i] <<= 0
                                self.sq_addr[i] <<= self.issue_addr
                                self.sq_data[i] <<= self.issue_wdata
                                self.sq_size[i] <<= self.issue_size
                        self.sq_tail <<= self.sq_tail + 1
                        self.sq_count <<= self.sq_count + 1

                # Commit store
                with If(self.commit_valid):
                    for i in range(sq_entries):
                        with If(self.commit_sq_idx == i):
                            self.sq_committed[i] <<= 1

                # Mark load as sent
                with If(self.mem_req_load):
                    for i in range(lq_entries):
                        with If(self.selected_lq == i):
                            self.lq_done[i] <<= 1

                # Complete store after memory write
                with If(self.mem_req_store):
                    for i in range(sq_entries):
                        with If(self.selected_sq == i):
                            self.sq_valid[i] <<= 0
                    self.sq_head <<= self.sq_head + 1
                    self.sq_count <<= self.sq_count - 1

                # Complete load after response
                with If(self.mem_resp_valid & self.mem_req_load):
                    for i in range(lq_entries):
                        with If(self.selected_lq == i):
                            self.lq_valid[i] <<= 0
                    self.lq_head <<= self.lq_head + 1
                    self.lq_count <<= self.lq_count - 1
