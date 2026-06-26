"""
Thor GPU — Warp Scheduler L3 DSL module.
Round-robin warp selection with idle/stall awareness.
"""
from __future__ import annotations
from rtlgen.core import Module, Input, Output, Wire, Reg, Mux
from rtlgen.logic import If, Else, Switch, ForGen

WARP_PER_SCHED = 4


class WarpScheduler(Module):
    """Round-robin warp scheduler managing WARP_PER_SCHED warps."""

    def __init__(self, name="warp_scheduler"):
        super().__init__(name)
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.warp_ready = Input(WARP_PER_SCHED, "warp_ready")
        self.warp_stall = Input(WARP_PER_SCHED, "warp_stall")
        self.selected_warp = Output(2, "selected_warp")
        self.select_valid = Output(1, "select_valid")

        self._last = Reg(2, "last_warp")
        self._avail = Wire(WARP_PER_SCHED, "avail")

        with self.comb:
            self._avail <<= self.warp_ready & ~self.warp_stall
            self.select_valid <<= (self._avail != 0)
            sel = Wire(2, "sel")
            with ForGen('i', 0, WARP_PER_SCHED) as i:
                idx = Wire(2, "idx")
                idx <<= (self._last + i + 1) & 3
                with If((self._avail >> self._last) & 1):
                    sel <<= self._last
            self.selected_warp <<= sel

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._last <<= 0
            with Else():
                with If(self.select_valid):
                    self._last <<= self.selected_warp
