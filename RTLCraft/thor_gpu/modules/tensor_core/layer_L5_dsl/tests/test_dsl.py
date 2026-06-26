"""L5 DSL simulation tests for ThorTensorCore (cross-layer vs L1)."""

import pytest

from rtlgen import Simulator
from thor_gpu.modules.tensor_core.layer_L5_dsl.src.dsl import ThorTensorCore, describe
from thor_gpu.modules.tensor_core import tc_mma_reference
from thor_gpu.modules.common.utils import (
    _pack_i8_matrix, _unpack_i32_matrix, _pack_i32_matrix,
)


def _run(dut, a, b, c=0, acc_en=0):
    sim = Simulator(dut)
    sim.reset(rst="rst_n")
    sim.poke("a", a)
    sim.poke("b", b)
    sim.poke("c", c)
    sim.poke("acc_en", acc_en)
    sim.poke("start", 1)
    sim.step()
    return sim.peek("result"), sim.peek("done")


class TestTensorCoreDSL:
    def test_describe(self):
        info = describe()
        assert info["dsl_class"] == "ThorTensorCore"

    def test_identity_cross_layer(self):
        dut = ThorTensorCore()
        I = [[1 if i == j else 0 for j in range(8)] for i in range(8)]
        X = [[i * 8 + j for j in range(8)] for i in range(8)]
        a = _pack_i8_matrix(I)
        b = _pack_i8_matrix(X)
        result, done = _run(dut, a, b, acc_en=0)
        assert done == 1
        expected = tc_mma_reference(a, b, 0, 0)["result"]
        assert result == expected
        assert _unpack_i32_matrix(result) == X

    def test_all_ones_cross_layer(self):
        dut = ThorTensorCore()
        ones = [[1] * 8 for _ in range(8)]
        a = _pack_i8_matrix(ones)
        b = _pack_i8_matrix(ones)
        result, done = _run(dut, a, b, acc_en=0)
        assert result == tc_mma_reference(a, b, 0, 0)["result"]
        assert _unpack_i32_matrix(result) == [[8] * 8 for _ in range(8)]

    def test_negative_int8_cross_layer(self):
        dut = ThorTensorCore()
        neg = [[-1] * 8 for _ in range(8)]
        ones = [[1] * 8 for _ in range(8)]
        a = _pack_i8_matrix(neg)
        b = _pack_i8_matrix(ones)
        result, done = _run(dut, a, b, acc_en=0)
        assert result == tc_mma_reference(a, b, 0, 0)["result"]

    def test_accumulate_cross_layer(self):
        dut = ThorTensorCore()
        ones = [[1] * 8 for _ in range(8)]
        c = [[100] * 8 for _ in range(8)]
        a = _pack_i8_matrix(ones)
        b = _pack_i8_matrix(ones)
        cpack = _pack_i32_matrix(c)
        result, done = _run(dut, a, b, cpack, acc_en=1)
        assert result == tc_mma_reference(a, b, cpack, 1)["result"]
        assert _unpack_i32_matrix(result) == [[108] * 8 for _ in range(8)]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
