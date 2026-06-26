"""Thor GPU — L1 Cache L3 DSL. 2-cycle direct-mapped 64KB data cache.
Cycle 0: tag compare + way select
Cycle 1: data read / write
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Memory, Array
from rtlgen.logic import If, Else


class L1Cache(Module):
    def __init__(self, name="l1_cache", size=65536, line_size=64):
        super().__init__(name)
        n_lines = size // line_size
        aw = max((n_lines - 1).bit_length(), 1)
        tag_w = max((line_size * n_lines).bit_length(), 1)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.addr = Input(32, "addr"); self.req_valid = Input(1, "req_valid")
        self.wen = Input(1, "wen"); self.wdata = Input(512, "wdata")
        self.fill_valid = Input(1, "fill_valid")
        self.fill_data = Input(512, "fill_data")
        self.fill_line = Input(aw, "fill_line")
        self.hit = Output(1, "hit"); self.rdata = Output(512, "rdata")
        self.miss = Output(1, "miss"); self.miss_addr = Output(32, "miss_addr")

        self._tag = Memory(tag_w, n_lines, "tag")
        self._data = Memory(512, n_lines, "data")
        self._valid = Reg(n_lines, "valid_bits")

        idx = Wire(aw, "cache_idx"); tag = Wire(tag_w, "cache_tag")
        with self.comb:
            idx <<= (self.addr // line_size) % n_lines
            tag <<= self.addr // (line_size * n_lines)

        vld_bit = Wire(1, "vld_bit")
        with self.comb:
            vld_bit <<= (self._valid >> idx) & 1

        with self.comb:
            self.hit <<= vld_bit & (self._tag[idx] == tag)
            self.rdata <<= self._data[idx]
            self.miss <<= self.req_valid & ~(vld_bit & (self._tag[idx] == tag))
            self.miss_addr <<= self.addr

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._valid <<= 0
            with Else():
                with If(self.fill_valid):
                    self._data[self.fill_line] <<= self.fill_data
                    self._valid <<= self._valid | (1 << self.fill_line)
                    self._tag[self.fill_line] <<= tag
                with If(self.wen & vld_bit & (self._tag[idx] == tag)):
                    self._data[idx] <<= self.wdata
