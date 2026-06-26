"""L1 behavior model tests for ThorVectorFPU."""

import pytest

from thor_gpu.modules.vector_fpu import (
    FPU_ADD, FPU_MUL, FPU_FMADD, vfpu_lane, vfpu_functional,
)
from thor_gpu.modules.common.utils import (
    _pack_u32_lanes, _unpack_u32_lanes, _fp32_to_f32_bits, _f32_bits_to_fp32,
)


class TestVectorFPUBehavior:
    def _vec(self, lanes):
        return _pack_u32_lanes(lanes)

    def test_fadd(self):
        a = self._vec([_fp32_to_f32_bits(1.5)] * 8)
        b = self._vec([_fp32_to_f32_bits(2.5)] * 8)
        r = vfpu_functional(FPU_ADD, a, b)["result"]
        assert _unpack_u32_lanes(r) == [_fp32_to_f32_bits(4.0)] * 8

    def test_fmul(self):
        a = self._vec([_fp32_to_f32_bits(3.0)] * 8)
        b = self._vec([_fp32_to_f32_bits(4.0)] * 8)
        r = vfpu_functional(FPU_MUL, a, b)["result"]
        assert _unpack_u32_lanes(r) == [_fp32_to_f32_bits(12.0)] * 8

    def test_fmadd(self):
        a = self._vec([_fp32_to_f32_bits(2.0)] * 8)
        b = self._vec([_fp32_to_f32_bits(3.0)] * 8)
        c = self._vec([_fp32_to_f32_bits(1.0)] * 8)
        r = vfpu_functional(FPU_FMADD, a, b, c)["result"]
        assert _unpack_u32_lanes(r) == [_fp32_to_f32_bits(7.0)] * 8  # 2*3+1

    def test_lane_direct(self):
        one = _fp32_to_f32_bits(1.0)
        two = _fp32_to_f32_bits(2.0)
        assert _f32_bits_to_fp32(vfpu_lane(FPU_ADD, one, two)) == 3.0

    def test_predication(self):
        a = self._vec([_fp32_to_f32_bits(1.0)] * 8)
        b = self._vec([_fp32_to_f32_bits(1.0)] * 8)
        res = vfpu_functional(FPU_ADD, a, b, active_mask=0b00000010)
        lanes = _unpack_u32_lanes(res["result"])
        assert _f32_bits_to_fp32(lanes[1]) == 2.0
        assert all(v == 0 for i, v in enumerate(lanes) if i != 1)
        assert res["result_mask"] == 0b00000010


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
