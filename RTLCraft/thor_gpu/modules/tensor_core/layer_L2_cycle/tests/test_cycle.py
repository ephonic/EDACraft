"""L2 cycle model tests for ThorTensorCore."""

import pytest

from rtlgen import CycleContext
from thor_gpu.modules.tensor_core.layer_L2_cycle.src.cycle import tc_cycle_model, describe
from thor_gpu.modules.tensor_core import tc_mma_reference
from thor_gpu.modules.common.utils import _pack_i8_matrix, _pack_i32_matrix


class TestTensorCoreCycle:
    def test_describe(self):
        info = describe()
        assert info["name"] == "ThorTensorCore"
        assert info["latency_cycles"] == 1

    def test_reset_clears(self):
        model = tc_cycle_model()
        ctx = CycleContext()
        ctx.inputs = {"rst_n": 0}
        model(ctx)
        assert ctx.outputs["result"] == 0
        assert ctx.outputs["done"] == 0

    def test_mma_one_cycle_matches_l1(self):
        model = tc_cycle_model()
        ctx = CycleContext()
        ones = [[1] * 8 for _ in range(8)]
        a = _pack_i8_matrix(ones)
        b = _pack_i8_matrix(ones)
        ctx.inputs = {"rst_n": 1, "start": 1, "a": a, "b": b, "c": 0, "acc_en": 0}
        model(ctx)
        expected = tc_mma_reference(a, b, 0, 0)["result"]
        assert ctx.outputs["result"] == expected
        assert ctx.outputs["done"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
