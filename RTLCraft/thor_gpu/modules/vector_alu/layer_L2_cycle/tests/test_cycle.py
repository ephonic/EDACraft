"""L2 cycle model tests for ThorVectorALU."""

import pytest

from rtlgen import CycleContext
from thor_gpu.modules.vector_alu.layer_L2_cycle.src.cycle import valu_cycle_model, describe
from thor_gpu.modules.vector_alu import ALU_ADD, ALU_SUB, valu_functional
from thor_gpu.modules.common.utils import _pack_u32_lanes, _unpack_u32_lanes


class TestVectorALUCycle:
    def test_describe(self):
        info = describe()
        assert info["name"] == "ThorVectorALU"
        assert info["layer"] == "L2_cycle"
        assert info["latency_cycles"] == 1

    def test_reset_clears_state(self):
        model = valu_cycle_model()
        ctx = CycleContext()
        ctx.inputs = {"rst_n": 0}
        model(ctx)
        assert ctx.outputs["result"] == 0
        assert ctx.outputs["valid"] == 0

    def test_add_one_cycle(self):
        model = valu_cycle_model()
        ctx = CycleContext()
        a = _pack_u32_lanes([i + 1 for i in range(8)])
        b = _pack_u32_lanes([10] * 8)
        ctx.inputs = {
            "rst_n": 1, "valid_in": 1, "alu_fn": ALU_ADD,
            "src1": a, "src2": b, "active_mask": 0xFF,
        }
        model(ctx)
        # L2 == L1 for the same inputs.
        expected = valu_functional(ALU_ADD, a, b)["result"]
        assert ctx.outputs["result"] == expected
        assert ctx.outputs["result_mask"] == 0xFF

    def test_sub_matches_l1(self):
        model = valu_cycle_model()
        ctx = CycleContext()
        a = _pack_u32_lanes([100, 50, 1, 0, 0xFFFFFFFF, 5, 8, 7])
        b = _pack_u32_lanes([1, 1, 1, 1, 1, 10, 3, 7])
        ctx.inputs = {
            "rst_n": 1, "valid_in": 1, "alu_fn": ALU_SUB,
            "src1": a, "src2": b, "active_mask": 0xFF,
        }
        model(ctx)
        assert ctx.outputs["result"] == valu_functional(ALU_SUB, a, b)["result"]

    def test_predication_matches_l1(self):
        model = valu_cycle_model()
        ctx = CycleContext()
        a = _pack_u32_lanes([5] * 8)
        b = _pack_u32_lanes([3] * 8)
        ctx.inputs = {
            "rst_n": 1, "valid_in": 1, "alu_fn": ALU_ADD,
            "src1": a, "src2": b, "active_mask": 0b10000000,
        }
        model(ctx)
        assert ctx.outputs["result_mask"] == 0b10000000
        assert ctx.outputs["result"] == valu_functional(ALU_ADD, a, b, 0b10000000)["result"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
