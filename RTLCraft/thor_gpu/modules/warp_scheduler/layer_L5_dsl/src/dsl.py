"""L5 DSL module for the ThorWarpScheduler.

RTL-ready rtlgen description of the sticky round-robin warp scheduler with
barrier synchronization. warp_sel is a registered output; it advances by one
only when the currently selected warp is idle.
"""

from __future__ import annotations
import os
import sys

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from rtlgen.core import Module, Input, Output, Wire, Reg, Const
from rtlgen.logic import If
from rtlgen.codegen import ModuleDocTemplate, fill_doc_template

NWARP = 4


class ThorWarpScheduler(Module):
    """Sticky round-robin warp scheduler (4 warps) with barrier sync.

    - warp_sel advances to (warp_sel + 1) only when the selected warp is idle.
    - barrier_release asserts when every warp is at-barrier or done.
    - sm_done asserts when every warp is done.
    """

    def __init__(self):
        super().__init__("thor_warp_scheduler")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        self.warp_idle = Input(NWARP, "warp_idle")
        self.warp_done = Input(NWARP, "warp_done")
        self.warp_at_barrier = Input(NWARP, "warp_at_barrier")

        self.warp_sel = Output(2, "warp_sel")
        self.barrier_release = Output(1, "barrier_release")
        self.sm_done = Output(1, "sm_done")

        self.sel = Reg(2, "sel", init_value=0)

        # Per-warp "at barrier or done" bits, AND-reduced for barrier_release.
        at_or_done_bits = [self.warp_at_barrier[w] | self.warp_done[w] for w in range(NWARP)]
        all_at_or_done = at_or_done_bits[0]
        for w in range(1, NWARP):
            all_at_or_done = all_at_or_done & at_or_done_bits[w]

        all_done = self.warp_done[0]
        for w in range(1, NWARP):
            all_done = all_done & self.warp_done[w]

        # Current selected warp idle bit (selected from warp_idle by sel).
        sel0 = (self.sel == Const(0, 2))
        sel1 = (self.sel == Const(1, 2))
        sel2 = (self.sel == Const(2, 2))
        cur_idle = sel0 & self.warp_idle[0]
        cur_idle = cur_idle | (sel1 & self.warp_idle[1])
        cur_idle = cur_idle | (sel2 & self.warp_idle[2])
        cur_idle = cur_idle | ((~(self.sel == Const(0, 2)) & ~(self.sel == Const(1, 2)) & ~(self.sel == Const(2, 2))) & self.warp_idle[3])

        # Gate cur_idle through a Wire (framework seq() If() requirement).
        cur_idle_w = Wire(1, "cur_idle_w")
        with self.comb:
            cur_idle_w <<= cur_idle
            self.warp_sel <<= self.sel
            self.barrier_release <<= all_at_or_done
            self.sm_done <<= all_done

        with self.seq(self.clk, ~self.rst_n):
            with If(cur_idle_w):
                self.sel <<= (self.sel + 1) & 0x3

        tpl = ModuleDocTemplate(
            source="thor_gpu/modules/warp_scheduler/layer_L5_dsl/src/dsl.py",
            description="Sticky round-robin warp scheduler (4 warps) with barrier sync.",
            author="RTLCraft Agent", version="0.1",
            timing="Registered warp_sel; advance when current warp idle.",
        )
        fill_doc_template(tpl, self)


def describe():
    from typing import Any, Dict
    return {
        "name": "ThorWarpScheduler",
        "layer": "L5_dsl",
        "status": "implemented",
        "description": "RTL-ready sticky-RR warp scheduler (4 warps) with barrier sync.",
        "dsl_class": "ThorWarpScheduler",
        "ports": "warp_idle[4], warp_done[4], warp_at_barrier[4] -> warp_sel[2], barrier_release, sm_done",
    }


__all__ = ["ThorWarpScheduler", "describe"]
