"""L2 cycle model tests for ThorVectorFPU."""

import pytest

from rtlgen import CycleContext
from thor_gpu.modules.vector_fpu.layer_L2_cycle.src.cycle import vfpu_cycle_model, describe
from thor_gpu.modules.vector_fpu import FPU_ADD, FPU_MUL, FPU_FMADD, vfpu_functional
from thor_gpu.modules.common.utils import _pack_u32_lanes, _unpack_u32_lanes, _fp32_to_f32_bits


class TestVectorFPUCycle:
    def test_describe(self):
        info = describe()
        assert info["name"] == "ThorVectorFPU"
        assert info["latency_cycles"] == 1

    def test_reset_clears(self):
        model = vfpu_cycle_model()
        ctx = CycleContext()
        ctx.inputs = {"rst_n": 0}
        model(ctx)
        assert ctx.outputs["result"] == 0

    def test_fadd_matches_l1(self):
        model = vfpu_cycle_model()
        ctx = CycleContext()
        a = _pack_u32_lanes([_fp32_to_f32_bits(1.5)] * 8)
        b = _pack_u32_lanes([_fp32_to_f32_bits(2.5)] * 8)
        ctx.inputs = {"rst_n": 1, "valid_in": 1, "fpu_fn": FPU_ADD,
                      "src1": a, "src2": b, "src3": 0, "active_mask": 0xFF}
        model(ctx)
        assert ctx.outputs["result"] == vfpu_functional(FPU_ADD, a, b)["result"]

    def test_fmadd_matches_l1(self):
        model = vfpu_cycle_model()
        ctx = CycleContext()
        a = _pack_u32_lanes([_fp32_to_f32_bits(2.0)] * 8)
        b = _pack_u32_lanes([_fp32_to_f32_bits(3.0)] * 8)
        c = _pack_u32_lanes([_fp32_to_f32_bits(1.0)] * 8)
        ctx.inputs = {"rst_n": 1, "valid_in": 1, "fpu_fn": FPU_FMADD,
                      "src1": a, "src2": b, "src3": c, "active_mask": 0xFF}
        model(ctx)
        assert ctx.outputs["result"] == vfpu_functional(FPU_FMADD, a, b, c)["result"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
