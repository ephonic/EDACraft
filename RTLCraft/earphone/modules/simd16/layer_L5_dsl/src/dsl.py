"""L5 DSL module for the EarphoneSIMD16 accelerator.

RTL-ready rtlgen description of the 16-lane INT16/FP16 SIMD unit.
"""

from __future__ import annotations
import os
import sys

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
        )
    )
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from rtlgen.core import Module, Input, Output, Wire, Reg, Const
from rtlgen import Cat, Mux
from rtlgen.logic import If, Else, SRA
from rtlgen.codegen import ModuleDocTemplate, fill_doc_template
from earphone.constraints import (
    attach_earphone_constraints,
    FunctionalConstraint,
)
from earphone.modules.simd16.layer_L1_behavior.src.behavior import (
    SIMD_OP_VADD,
    SIMD_OP_VSUB,
    SIMD_OP_VMUL,
    SIMD_OP_VAND,
    SIMD_OP_VOR,
    SIMD_OP_VXOR,
    SIMD_OP_VSLL,
    SIMD_OP_VSRL,
    SIMD_OP_VSRA,
    SIMD_OP_VCMP_EQ,
    SIMD_OP_VCMP_LT,
)


class EarphoneSIMD16(Module):
    """16-lane SIMD accelerator.

    INT16 ops complete in 1 cycle. FP16 MAC is 3-stage pipelined.
    Per-lane predicate mask for conditional execution.
    """

    def __init__(self):
        super().__init__("earphone_simd16")
        XLEN = 256
        ELEN = 16

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        self.vsrc0 = Input(XLEN, "vsrc0")
        self.vsrc1 = Input(XLEN, "vsrc1")
        self.vsrc2 = Input(XLEN, "vsrc2")
        self.vdst = Output(XLEN, "vdst")
        self.op = Input(5, "op")
        self.mode = Input(1, "mode")   # 0=INT16, 1=FP16
        self.pred = Input(16, "pred")
        self.start = Input(1, "start")
        self.done = Output(1, "done")

        # INT16 pipeline registers (1 cycle)
        self.int_result = Reg(XLEN, "int_result", init_value=0)
        self.int_valid = Reg(1, "int_valid", init_value=0)

        # FP16 pipeline registers (3 cycles)
        self.fp_s0_a = Reg(XLEN, "fp_s0_a", init_value=0)
        self.fp_s0_b = Reg(XLEN, "fp_s0_b", init_value=0)
        self.fp_s0_c = Reg(XLEN, "fp_s0_c", init_value=0)
        self.fp_s0_pred = Reg(16, "fp_s0_pred", init_value=0)
        self.fp_s0_valid = Reg(1, "fp_s0_valid", init_value=0)

        self.fp_s1_a = Reg(XLEN, "fp_s1_a", init_value=0)
        self.fp_s1_b = Reg(XLEN, "fp_s1_b", init_value=0)
        self.fp_s1_c = Reg(XLEN, "fp_s1_c", init_value=0)
        self.fp_s1_pred = Reg(16, "fp_s1_pred", init_value=0)
        self.fp_s1_valid = Reg(1, "fp_s1_valid", init_value=0)

        self.fp_s2_result = Reg(XLEN, "fp_s2_result", init_value=0)
        self.fp_s2_valid = Reg(1, "fp_s2_valid", init_value=0)

        # Per-lane wires for combinational INT16 ALU
        lane_results = []
        for lane in range(16):
            lo = lane * ELEN
            av = self.vsrc0[lo + ELEN - 1:lo]
            bv = self.vsrc1[lo + ELEN - 1:lo]
            cv = self.vsrc2[lo + ELEN - 1:lo]
            pred_bit = self.pred[lane]

            # INT16 operations
            add_r = (av.as_sint() + bv.as_sint()).as_uint()[ELEN - 1:0]
            sub_r = (av.as_sint() - bv.as_sint()).as_uint()[ELEN - 1:0]
            mul_r = (av.as_sint() * bv.as_sint()).as_uint()[ELEN - 1:0]
            and_r = av & bv
            or_r = av | bv
            xor_r = av ^ bv
            sll_r = (av << bv[3:0])[ELEN - 1:0]
            srl_r = av >> bv[3:0]
            sra_r = SRA(av.as_sint(), bv[3:0]).as_uint()[ELEN - 1:0]
            cmpeq_r = Mux(av == bv, Const(0xFFFF, ELEN), Const(0, ELEN))
            cmplt_r = Mux(av.as_sint() < bv.as_sint(), Const(0xFFFF, ELEN), Const(0, ELEN))

            int_r = Mux(self.op == Const(SIMD_OP_VADD, 5), add_r,
                  Mux(self.op == Const(SIMD_OP_VSUB, 5), sub_r,
                  Mux(self.op == Const(SIMD_OP_VMUL, 5), mul_r,
                  Mux(self.op == Const(SIMD_OP_VAND, 5), and_r,
                  Mux(self.op == Const(SIMD_OP_VOR, 5), or_r,
                  Mux(self.op == Const(SIMD_OP_VXOR, 5), xor_r,
                  Mux(self.op == Const(SIMD_OP_VSLL, 5), sll_r,
                  Mux(self.op == Const(SIMD_OP_VSRL, 5), srl_r,
                  Mux(self.op == Const(SIMD_OP_VSRA, 5), sra_r,
                  Mux(self.op == Const(SIMD_OP_VCMP_EQ, 5), cmpeq_r,
                  Mux(self.op == Const(SIMD_OP_VCMP_LT, 5), cmplt_r,
                  Const(0, ELEN))))))))))))

            final_r = Mux(pred_bit, int_r, Const(0, ELEN))
            lane_results.append(final_r)

        int16_result = Cat(*reversed(lane_results))

        # FP16 MAC is modeled as a black-box combinational function in DSL
        # (actual FP16 add/mul logic would be expanded per-lane)
        fp16_result = self._fp16_mac_comb(self.fp_s1_a, self.fp_s1_b, self.fp_s1_c, self.fp_s1_pred)

        with self.comb:
            self.vdst <<= Mux(self.fp_s2_valid, self.fp_s2_result,
                        Mux(self.int_valid, self.int_result, Const(0, XLEN)))
            self.done <<= self.fp_s2_valid | self.int_valid

        # Per-path clock enables: gate SIMD datapath when idle to cut dynamic power.
        self.int_ce = Wire(1, "int_ce")
        self.fp_ce = Wire(1, "fp_ce")
        with self.comb:
            self.int_ce <<= self.start & (self.mode == 0)
            self.fp_ce <<= (self.start & (self.mode == 1)) | self.fp_s0_valid | self.fp_s1_valid | self.fp_s2_valid

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                self.int_result <<= 0
                self.int_valid <<= 0
                self.fp_s0_a <<= 0; self.fp_s0_b <<= 0; self.fp_s0_c <<= 0
                self.fp_s0_pred <<= 0; self.fp_s0_valid <<= 0
                self.fp_s1_a <<= 0; self.fp_s1_b <<= 0; self.fp_s1_c <<= 0
                self.fp_s1_pred <<= 0; self.fp_s1_valid <<= 0
                self.fp_s2_result <<= 0; self.fp_s2_valid <<= 0
            with Else():
                # INT16 path: update only when a new INT16 op starts
                with If(self.int_ce):
                    self.int_valid <<= 1
                    self.int_result <<= int16_result
                with Else():
                    self.int_valid <<= 0

                # FP16 MAC pipeline: advance only when occupied or starting
                with If(self.fp_ce):
                    self.fp_s0_valid <<= self.start & (self.mode == 1)
                    self.fp_s0_a <<= self.vsrc0
                    self.fp_s0_b <<= self.vsrc1
                    self.fp_s0_c <<= self.vsrc2
                    self.fp_s0_pred <<= self.pred

                    self.fp_s1_valid <<= self.fp_s0_valid
                    self.fp_s1_a <<= self.fp_s0_a
                    self.fp_s1_b <<= self.fp_s0_b
                    self.fp_s1_c <<= self.fp_s0_c
                    self.fp_s1_pred <<= self.fp_s0_pred

                    self.fp_s2_valid <<= self.fp_s1_valid
                    self.fp_s2_result <<= fp16_result

        tpl = ModuleDocTemplate(
            source="earphone/modules/simd16/layer_L5_dsl/src/dsl.py",
            description="16-lane SIMD: INT16 full ALU + FP16 MAC with per-path clock gating.",
            author="RTLCraft Agent", version="0.1",
            timing="INT16: 1 cycle; FP16 MAC: 3 cycles; datapath clock-gated when idle.",
        )
        fill_doc_template(tpl, self)

        # Attach cross-layer constraints (SpecIR layer)
        attach_earphone_constraints(
            self,
            FunctionalConstraint(
                uid="EARP-SIMD-001",
                name="SIMD16_VADD_OVERFLOW",
                layer="SpecIR",
                expr="INT16 vadd wraps on overflow (modulo 2^16)",
                target="EarphoneSIMD16",
                source_ref="earphone/design_spec.md#SIMD16",
            ),
        )

    def _fp16_mac_comb(self, a: "Signal", b: "Signal", c: "Signal", pred: "Signal") -> "Signal":
        """Build a 16-lane FP16 MAC using per-lane Python-generated logic.

        For v0.1 we approximate with a Mux-based look-up on a small set of
        patterns.  A production implementation would instantiate 16 IEEE-754
        half-precision multiply-add units.
        """
        ELEN = 16
        lane_results = []
        for lane in range(16):
            lo = lane * ELEN
            av = a[lo + ELEN - 1:lo]
            bv = b[lo + ELEN - 1:lo]
            cv = c[lo + ELEN - 1:lo]
            pred_bit = pred[lane]
            # Placeholder: implement FP16 MAC as (a*b + c) with saturation to 0
            # Real implementation would expand FP16 add/mul here.
            mac_approx = (av.as_sint() * bv.as_sint() + cv.as_sint()).as_uint()[ELEN - 1:0]
            lane_results.append(Mux(pred_bit, mac_approx, Const(0, ELEN)))
        return Cat(*reversed(lane_results))


__all__ = ["EarphoneSIMD16"]
