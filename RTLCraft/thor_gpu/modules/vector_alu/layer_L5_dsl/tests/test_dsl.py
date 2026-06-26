"""L5 DSL simulation tests for ThorVectorALU (cross-layer vs L1)."""

import pytest

from rtlgen import Simulator
from thor_gpu.modules.vector_alu.layer_L5_dsl.src.dsl import ThorVectorALU, describe
from thor_gpu.modules.vector_alu import (
    ALU_ADD, ALU_SUB, ALU_AND, ALU_XOR, ALU_SLL, ALU_SRL, ALU_SLT, ALU_SLTU, valu_functional,
)
from thor_gpu.modules.common.utils import _pack_u32_lanes, _unpack_u32_lanes


def _run(dut, fn, a_lanes, b_lanes, mask=0xFF):
    sim = Simulator(dut)
    sim.reset(rst="rst_n")
    a = _pack_u32_lanes(a_lanes)
    b = _pack_u32_lanes(b_lanes)
    sim.poke("alu_fn", fn)
    sim.poke("src1", a)
    sim.poke("src2", b)
    sim.poke("active_mask", mask)
    sim.poke("valid_in", 1)
    sim.step()
    result = sim.peek("result")
    rmask = sim.peek("result_mask")
    expected = valu_functional(fn, a, b, mask)
    return result, rmask, expected


class TestVectorALUDSL:
    def test_describe(self):
        info = describe()
        assert info["dsl_class"] == "ThorVectorALU"

    def test_add_cross_layer(self):
        dut = ThorVectorALU()
        result, rmask, exp = _run(dut, ALU_ADD,
                                  [i + 1 for i in range(8)], [10] * 8)
        assert result == exp["result"]
        assert rmask == exp["result_mask"]

    def test_sub_cross_layer(self):
        dut = ThorVectorALU()
        a = [100, 50, 1, 0, 0xFFFFFFFF, 5, 8, 7]
        b = [1, 1, 1, 1, 1, 10, 3, 7]
        result, rmask, exp = _run(dut, ALU_SUB, a, b)
        assert result == exp["result"]
        assert _unpack_u32_lanes(result)[0] == 99

    def test_and_xor_cross_layer(self):
        dut = ThorVectorALU()
        r1, _, e1 = _run(dut, ALU_AND, [0xFF00FF00] * 8, [0x00FF00FF] * 8)
        assert r1 == e1["result"]
        r2, _, e2 = _run(dut, ALU_XOR, [0xFF00FF00] * 8, [0x00FF00FF] * 8)
        assert r2 == e2["result"]

    def test_shifts_cross_layer(self):
        dut = ThorVectorALU()
        r, _, e = _run(dut, ALU_SLL, [1] * 8, [4] * 8)
        assert r == e["result"]
        assert _unpack_u32_lanes(r) == [0x10] * 8
        r, _, e = _run(dut, ALU_SRL, [0x80000000] * 8, [4] * 8)
        assert r == e["result"]

    def test_slt_sltu_cross_layer(self):
        dut = ThorVectorALU()
        r, _, e = _run(dut, ALU_SLT, [0xFFFFFFFF] * 8, [1] * 8)
        assert r == e["result"]
        assert _unpack_u32_lanes(r) == [1] * 8
        r, _, e = _run(dut, ALU_SLTU, [0xFFFFFFFF] * 8, [1] * 8)
        assert r == e["result"]
        assert _unpack_u32_lanes(r) == [0] * 8

    def test_predication_cross_layer(self):
        dut = ThorVectorALU()
        r, rmask, e = _run(dut, ALU_ADD, [5] * 8, [3] * 8, mask=0b00000001)
        assert r == e["result"]
        assert rmask == 0b00000001
        assert _unpack_u32_lanes(r)[0] == 8
        assert all(v == 0 for v in _unpack_u32_lanes(r)[1:])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
