"""L5 DSL module for the ThorSIMTStack.

RTL-ready rtlgen description of the SIMT divergence/reconvergence stack. The
stack is implemented as two arrays (reconverge_pc[32], not_taken_mask[8])
addressed by a stack-pointer register.
"""

from __future__ import annotations
import os
import sys

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from rtlgen.core import Module, Input, Output, Wire, Array, Reg, Const
from rtlgen import Mux
from rtlgen.logic import If, Elif, Else
from rtlgen.codegen import ModuleDocTemplate, fill_doc_template

PC_W = 32
MASK_W = 8
MAX_DEPTH = 8


class ThorSIMTStack(Module):
    """SIMT divergence/reconvergence stack (depth 8).

    push: store (reconverge_pc, active & ~taken) at sp, sp++,
          next_pc=branch_pc, next_mask=active & taken.
    pop:  sp--, read frame at sp, next_pc=frame_pc, next_mask=frame_mask.
    """

    def __init__(self):
        super().__init__("thor_simt_stack")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        self.push = Input(1, "push")
        self.pop = Input(1, "pop")
        self.branch_pc = Input(PC_W, "branch_pc")
        self.reconverge_pc = Input(PC_W, "reconverge_pc")
        self.taken_mask = Input(MASK_W, "taken_mask")
        self.active_mask = Input(MASK_W, "active_mask")

        self.next_pc = Output(PC_W, "next_pc")
        self.next_mask = Output(MASK_W, "next_mask")
        self.stack_depth = Output(4, "stack_depth")

        self.pc_mem = Array(PC_W, MAX_DEPTH, "pc_mem")
        self.mask_mem = Array(MASK_W, MAX_DEPTH, "mask_mem")

        self.sp_reg = Reg(4, "sp_reg", init_value=0)
        self.depth = Reg(4, "depth", init_value=0)

        # Combinational read of the top frame (index sp_reg - 1).
        top_idx = (self.sp_reg - 1) & 0x7
        top_pc = self.pc_mem[top_idx]
        top_mask = self.mask_mem[top_idx]

        not_taken = self.active_mask & (~self.taken_mask & ((1 << MASK_W) - 1))
        taken = self.active_mask & self.taken_mask

        # Outputs depend on push/pop.
        with self.comb:
            with If(self.push):
                self.next_pc <<= self.branch_pc
                self.next_mask <<= taken
            with Elif(self.pop):
                self.next_pc <<= top_pc
                self.next_mask <<= top_mask
            with Else():
                self.next_pc <<= 0
                self.next_mask <<= self.active_mask
            self.stack_depth <<= self.depth

        # Gate control through Wires (framework seq() If() requirement).
        push_w = Wire(1, "push_w")
        pop_w = Wire(1, "pop_w")
        with self.comb:
            push_w <<= self.push
            pop_w <<= self.pop

        with self.seq(self.clk, ~self.rst_n):
            with If(push_w):
                self.pc_mem[self.sp_reg & 0x7] <<= self.reconverge_pc
                self.mask_mem[self.sp_reg & 0x7] <<= not_taken
                self.sp_reg <<= (self.sp_reg + 1) & 0xF
                self.depth <<= self.depth + 1
            with Elif(pop_w):
                self.sp_reg <<= (self.sp_reg - 1) & 0xF
                self.depth <<= self.depth - 1 if self.depth != 0 else 0

        tpl = ModuleDocTemplate(
            source="thor_gpu/modules/simt_stack/layer_L5_dsl/src/dsl.py",
            description="SIMT divergence/reconvergence stack (depth 8).",
            author="RTLCraft Agent", version="0.1",
            timing="1-cycle push/pop; combinational next_pc/next_mask.",
        )
        fill_doc_template(tpl, self)


def describe():
    from typing import Any, Dict
    return {
        "name": "ThorSIMTStack",
        "layer": "L5_dsl",
        "status": "implemented",
        "description": "RTL-ready SIMT divergence/reconvergence stack (depth 8).",
        "dsl_class": "ThorSIMTStack",
        "ports": "push, pop, branch_pc[32], reconverge_pc[32], taken_mask[8], active_mask[8] -> next_pc[32], next_mask[8], stack_depth[4]",
    }


__all__ = ["ThorSIMTStack", "describe"]
