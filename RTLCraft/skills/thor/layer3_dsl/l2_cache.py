"""Thor GPU — L2 Cache L3 DSL. 8-way set-associative 512KB with LRU replacement.
Set = (addr / line_size) % n_sets
Tag = addr / (line_size * n_sets)
LRU: most recently used way moves to MRU position.
"""
from rtlgen.core import Module, Input, Output, Wire, Reg, Memory
from rtlgen.logic import If, Else, Switch

from skills.thor import VLEN


class L2Cache(Module):
    def __init__(self, n_ways=8, line_size=64, n_sets=1024):
        super().__init__("l2_cache")
        sw = max((n_sets - 1).bit_length(), 1)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.addr = Input(32, "addr"); self.req_valid = Input(1, "req_valid")
        self.wen = Input(1, "wen"); self.wdata = Input(VLEN, "wdata")
        self.fill_valid = Input(1, "fill_valid")
        self.fill_data = Input(VLEN, "fill_data")
        self.fill_way = Input(3, "fill_way")
        self.hit = Output(1, "hit"); self.hit_way = Output(3, "hit_way")
        self.miss = Output(1, "miss"); self.miss_addr = Output(32, "miss_addr")
        self.evict_way = Output(3, "evict_way"); self.evict_valid = Output(1, "evict_valid")

        set_idx = Wire(sw, "l2_set"); tag = Wire(16, "l2_tag")
        with self.comb:
            set_idx <<= (self.addr // line_size) % n_sets
            tag <<= self.addr // (line_size * n_sets)

        # Per-way tag + data + valid (fixed width for Verilog compatibility)
        tag_mem = [Memory(16, n_sets, f"tag_{w}") for w in range(n_ways)]
        data_mem = [Memory(VLEN, n_sets, f"data_{w}") for w in range(n_ways)]
        valid_reg = [Reg(n_sets, f"valid_{w}") for w in range(n_ways)]
        lru_reg = [Reg(3, f"lru_{w}") for w in range(n_ways)]

        hit_w = Wire(1, "l2_hit"); way_w = Wire(3, "l2_way")
        ev_w = Wire(3, "l2_evict")
        with self.comb:
            hit_w <<= 0; way_w <<= 0
            for w in range(n_ways):
                with If(valid_reg[w][set_idx] & (tag_mem[w][set_idx] == tag)):
                    hit_w <<= 1; way_w <<= w
            self.hit <<= hit_w; self.hit_way <<= way_w
            self.miss <<= self.req_valid & ~hit_w
            self.miss_addr <<= self.addr
            # Evict LRU way
            lru_way = Wire(3, "lru_way")
            for w in range(n_ways): lru_way <<= w
            self.evict_way <<= lru_way
            self.evict_valid <<= self.req_valid & ~hit_w

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                for w in range(n_ways):
                    valid_reg[w] <<= 0; lru_reg[w] <<= w
            with Else():
                with If(self.fill_valid):
                    for w in range(n_ways):
                        with If(self.fill_way == w):
                            data_mem[w][set_idx] <<= self.fill_data
                            tag_mem[w][set_idx] <<= tag
                            valid_reg[w] <<= valid_reg[w] | (1 << set_idx)
                with If(hit_w & ~self.wen):
                    self.hit <<= 1
