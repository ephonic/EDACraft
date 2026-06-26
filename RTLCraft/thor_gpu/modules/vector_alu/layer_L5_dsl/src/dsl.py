"""L5 DSL module for the ThorVectorALU.

RTL-ready rtlgen description of the 8-lane INT32 vector ALU. Each lane is built
from per-lane Python-generated logic so the result is a flat combinational tree
captured in a 1-stage result register.
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
from rtlgen import Cat, Mux
from rtlgen.logic import If, Else, SRA
from rtlgen.codegen import ModuleDocTemplate, fill_doc_template

from thor_gpu.modules.vector_alu.layer_L1_behavior.src.behavior import (
    ALU_ADD, ALU_SLL, ALU_XOR, ALU_SRL, ALU_OR, ALU_AND, ALU_SUB, ALU_SLT, ALU_SLTU,
)

XLEN = 32
NLANE = 8
VLEN = XLEN * NLANE  # 256


def _priority_mux(cases, default):
    """Build a balanced (O(log n) depth) select Mux tree.

    ``cases`` is a list of ``(condition, value)`` pairs. The conditions are
    assumed mutually exclusive (e.g. distinct function codes), so first-match
    priority equals a balanced select. A right-nested Mux chain of depth N is
    not reliably resolved by the framework simulator at large N, so this helper
    splits the list in half and recurses, yielding ~log2(N) nesting depth.
    """
    if not cases:
        return default
    if len(cases) == 1:
        cond, val = cases[0]
        return Mux(cond, val, default)
    mid = len(cases) // 2
    hi_cases = cases[:mid]
    lo_cases = cases[mid:]
    hi = _priority_mux(hi_cases, default)
    lo = _priority_mux(lo_cases, default)
    # Select lo subtree when any lo-condition holds; otherwise the hi subtree.
    any_lo = _any_cond([c for c, _ in lo_cases])
    return Mux(any_lo, lo, hi)


def _any_cond(conds):
    """OR-reduce a list of boolean conditions into one Signal."""
    result = conds[0]
    for c in conds[1:]:
        result = result | c
    return result


def _signed_lt(a, b, width):
    """Signed (two's-complement) less-than built from the framework's unsigned ``<``.

    The framework ``<`` operator is unsigned even when operands are cast via
    ``as_sint()``, so we reconstruct signed comparison: if the sign bits differ,
    the negative operand is smaller; otherwise compare as unsigned.
    Returns a 1-bit Signal usable as a Mux condition.
    """
    sa = a[width - 1]
    sb = b[width - 1]
    sign_diff = sa ^ sb
    # sign bits differ -> a<b when a is negative (sa==1)
    # sign bits same  -> unsigned a<b
    return Mux(sign_diff, sa, (a < b))


class ThorVectorALU(Module):
    """8-lane INT32 vector ALU with per-lane active-mask predication.

    1-cycle registered result. Opcodes: ADD0/SLL1/XOR4/SRL5/OR6/AND7/SUB10/SLT12/SLTU14.
    """

    def __init__(self):
        super().__init__("thor_vector_alu")

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        self.src1 = Input(VLEN, "src1")
        self.src2 = Input(VLEN, "src2")
        self.active_mask = Input(NLANE, "active_mask")
        self.alu_fn = Input(4, "alu_fn")
        self.valid_in = Input(1, "valid_in")

        self.result = Output(VLEN, "result")
        self.result_mask = Output(NLANE, "result_mask")
        self.valid = Output(1, "valid")

        # Combinational per-lane compute.
        lane_results = []
        lane_enables = []
        for lane in range(NLANE):
            lo = lane * XLEN
            s1 = self.src1[lo + XLEN - 1:lo]
            s2 = self.src2[lo + XLEN - 1:lo]
            en = self.active_mask[lane]
            lane_enables.append(en)

            sh = s2[4:0]
            add_r = (s1.as_sint() + s2.as_sint()).as_uint()[XLEN - 1:0]
            sub_r = (s1.as_sint() - s2.as_sint()).as_uint()[XLEN - 1:0]
            sll_r = (s1 << sh)[XLEN - 1:0]
            srl_r = s1 >> sh
            and_r = s1 & s2
            or_r = s1 | s2
            xor_r = s1 ^ s2
            slt_r = Mux(_signed_lt(s1, s2, XLEN), Const(1, XLEN), Const(0, XLEN))
            sltu_r = Mux(s1 < s2, Const(1, XLEN), Const(0, XLEN))

            # Select the per-lane result with a BALANCED Mux tree. The framework's
            # simulator does not reliably resolve deeply right-nested Mux chains
            # (depth 7+), so we build an O(log n) priority-select tree instead.
            cases = [
                (self.alu_fn == Const(ALU_ADD, 4), add_r),
                (self.alu_fn == Const(ALU_SLL, 4), sll_r),
                (self.alu_fn == Const(ALU_XOR, 4), xor_r),
                (self.alu_fn == Const(ALU_SRL, 4), srl_r),
                (self.alu_fn == Const(ALU_OR, 4), or_r),
                (self.alu_fn == Const(ALU_AND, 4), and_r),
                (self.alu_fn == Const(ALU_SUB, 4), sub_r),
                (self.alu_fn == Const(ALU_SLT, 4), slt_r),
                (self.alu_fn == Const(ALU_SLTU, 4), sltu_r),
            ]
            lane_r = _priority_mux(cases, Const(0, XLEN))
            # Predication: disabled lanes produce zero.
            lane_results.append(Mux(en, lane_r, Const(0, XLEN)))

        comb_result = Cat(*reversed(lane_results))
        # Build the result_mask vector (bit i = enable of lane i).
        rmask_bits = [lane_enables[NLANE - 1 - i] for i in range(NLANE)]
        comb_mask = Cat(*rmask_bits)

        # NOTE: this framework requires seq() If() conditions to be driven via a
        # Wire/Reg, not a bare Input port. Gate valid_in through a Wire.
        en_w = Wire(1, "en_w")
        with self.comb:
            en_w <<= self.valid_in
            self.valid <<= self.valid_in

        with self.seq(self.clk, ~self.rst_n):
            # The seq() reset condition already clears registers on reset;
            # here we only describe the non-reset behavior.
            with If(en_w):
                self.result <<= comb_result
                self.result_mask <<= comb_mask

        tpl = ModuleDocTemplate(
            source="thor_gpu/modules/vector_alu/layer_L5_dsl/src/dsl.py",
            description="8-lane INT32 vector ALU with per-lane predication; 1-cycle registered.",
            author="RTLCraft Agent", version="0.1",
            timing="1 cycle latency; disabled lanes zeroed.",
        )
        fill_doc_template(tpl, self)


def describe():
    from typing import Any, Dict
    return {
        "name": "ThorVectorALU",
        "layer": "L5_dsl",
        "status": "implemented",
        "description": "RTL-ready 8-lane INT32 vector ALU (1-cycle registered, predicated).",
        "dsl_class": "ThorVectorALU",
        "ports": "src1[256], src2[256], active_mask[8], alu_fn[4], valid_in -> result[256], result_mask[8], valid",
    }


__all__ = ["ThorVectorALU", "describe"]
