"""L1 behavior model tests for EarphoneSIMD16."""

import pytest

from earphone.modules.simd16 import (
    SIMD_OP_VADD,
    SIMD_OP_VSUB,
    SIMD_OP_VAND,
    SIMD_OP_VSRA,
    SIMD_OP_VCMP_EQ,
    SIMD_OP_VCMP_LT,
    simd16_int16_functional,
    simd16_fp16_mac_functional,
)
from earphone.modules.common.utils import _pack_u16_lanes, _unpack_u16_lanes


class TestSIMD16Behavior:
    def _vec(self, lanes):
        return _pack_u16_lanes(lanes)

    def test_vadd_lanes(self):
        a = self._vec([i + 1 for i in range(16)])
        b = self._vec([i + 2 for i in range(16)])
        r = simd16_int16_functional(SIMD_OP_VADD, a, b)
        lanes = _unpack_u16_lanes(r)
        expected = [((i + 1) + (i + 2)) & 0xFFFF for i in range(16)]
        assert lanes == expected

    def test_vsub_lanes(self):
        a = self._vec([10] * 16)
        b = self._vec([3] * 16)
        r = simd16_int16_functional(SIMD_OP_VSUB, a, b)
        lanes = _unpack_u16_lanes(r)
        assert lanes == [7] * 16

    def test_vand_lanes(self):
        a = self._vec([0xFF00] * 16)
        b = self._vec([0x00FF] * 16)
        r = simd16_int16_functional(SIMD_OP_VAND, a, b)
        lanes = _unpack_u16_lanes(r)
        assert lanes == [0] * 16

    def test_vcmp_eq_lanes(self):
        a = self._vec([0x1234] * 16)
        b = self._vec([0x1234] * 16)
        r = simd16_int16_functional(SIMD_OP_VCMP_EQ, a, b)
        lanes = _unpack_u16_lanes(r)
        assert lanes == [0xFFFF] * 16

    def test_vcmp_lt_uses_signed_16bit_lane_ordering(self):
        a = self._vec([0x8000] + [0] * 15)  # -32768 on lane 0
        b = self._vec([0x0001] + [0] * 15)  # +1 on lane 0
        r = simd16_int16_functional(SIMD_OP_VCMP_LT, a, b, pred=0x0001)
        lanes = _unpack_u16_lanes(r)
        assert lanes[0] == 0xFFFF
        assert all(l == 0 for l in lanes[1:])

    def test_vsra_uses_signed_16bit_lane_shift(self):
        a = self._vec([0xFF00] + [0] * 15)  # -256 on lane 0
        b = self._vec([0x0003] + [0] * 15)
        r = simd16_int16_functional(SIMD_OP_VSRA, a, b, pred=0x0001)
        lanes = _unpack_u16_lanes(r)
        assert lanes[0] == 0xFFE0
        assert all(l == 0 for l in lanes[1:])

    def test_predicate_mask(self):
        a = self._vec([1] * 16)
        b = self._vec([2] * 16)
        pred = 0x0001  # only lane 0 enabled
        r = simd16_int16_functional(SIMD_OP_VADD, a, b, pred=pred)
        lanes = _unpack_u16_lanes(r)
        assert lanes[0] == 3
        assert all(l == 0 for l in lanes[1:])

    def test_fp16_mac_lane(self):
        # 1.0 + 2.0*3.0 = 7.0 in FP16 lane 0 only
        from earphone.modules.simd16.layer_L1_behavior.src.behavior import _f32_to_fp16
        one = _f32_to_fp16(1.0)
        two = _f32_to_fp16(2.0)
        three = _f32_to_fp16(3.0)
        a = self._vec([two] + [0] * 15)
        b = self._vec([three] + [0] * 15)
        c = self._vec([one] + [0] * 15)
        r = simd16_fp16_mac_functional(a, b, c, pred=0xFFFF)
        lanes = _unpack_u16_lanes(r)
        assert lanes[0] == _f32_to_fp16(7.0)
        assert all(l == 0 for l in lanes[1:])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
