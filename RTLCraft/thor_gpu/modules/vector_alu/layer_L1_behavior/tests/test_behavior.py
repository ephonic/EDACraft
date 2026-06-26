"""L1 behavior model tests for ThorVectorALU."""

import pytest

from thor_gpu.modules.vector_alu import (
    ALU_ADD, ALU_SUB, ALU_AND, ALU_OR, ALU_XOR, ALU_SLL, ALU_SRL, ALU_SLT, ALU_SLTU,
    valu_lane, valu_functional,
)
from thor_gpu.modules.common.utils import _pack_u32_lanes, _unpack_u32_lanes


class TestVectorALUBehavior:
    def _vec(self, lanes):
        return _pack_u32_lanes(lanes)

    def test_add_lanes(self):
        a = self._vec([i + 1 for i in range(8)])
        b = self._vec([10] * 8)
        r = valu_functional(ALU_ADD, a, b)["result"]
        assert _unpack_u32_lanes(r) == [((i + 1) + 10) & 0xFFFFFFFF for i in range(8)]

    def test_add_overflow_wraps(self):
        a = self._vec([0xFFFFFFFF] * 8)
        b = self._vec([1] * 8)
        r = valu_functional(ALU_ADD, a, b)["result"]
        assert _unpack_u32_lanes(r) == [0] * 8

    def test_sub_wraps(self):
        a = self._vec([0] * 8)
        b = self._vec([1] * 8)
        r = valu_functional(ALU_SUB, a, b)["result"]
        assert _unpack_u32_lanes(r) == [0xFFFFFFFF] * 8

    def test_and_or_xor(self):
        a = self._vec([0xFF00FF00] * 8)
        b = self._vec([0x00FF00FF] * 8)
        assert _unpack_u32_lanes(valu_functional(ALU_AND, a, b)["result"]) == [0] * 8
        assert _unpack_u32_lanes(valu_functional(ALU_OR, a, b)["result"]) == [0xFFFFFFFF] * 8
        assert _unpack_u32_lanes(valu_functional(ALU_XOR, a, b)["result"]) == [0xFFFFFFFF] * 8

    def test_shifts(self):
        a = self._vec([0x00000001] * 8)
        sh = self._vec([4] * 8)
        assert _unpack_u32_lanes(valu_functional(ALU_SLL, a, sh)["result"]) == [0x10] * 8
        big = self._vec([0x80000000] * 8)
        assert _unpack_u32_lanes(valu_functional(ALU_SRL, big, sh)["result"]) == [0x08000000] * 8

    def test_slt_sltu_signed_vs_unsigned(self):
        a = self._vec([0xFFFFFFFF] * 8)  # -1 signed, 4294967295 unsigned
        b = self._vec([1] * 8)
        assert _unpack_u32_lanes(valu_functional(ALU_SLT, a, b)["result"]) == [1] * 8   # -1 < 1
        assert _unpack_u32_lanes(valu_functional(ALU_SLTU, a, b)["result"]) == [0] * 8  # big < 1 false

    def test_active_mask_predication(self):
        a = self._vec([5] * 8)
        b = self._vec([3] * 8)
        res = valu_functional(ALU_ADD, a, b, active_mask=0b00000001)
        lanes = _unpack_u32_lanes(res["result"])
        assert lanes[0] == 8
        assert all(v == 0 for v in lanes[1:])
        assert res["result_mask"] == 0b00000001

    def test_shift_amount_masked_to_5_bits(self):
        assert valu_lane(ALU_SLL, 1, 32) == 1  # 32 & 0x1F = 0 -> no shift


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
