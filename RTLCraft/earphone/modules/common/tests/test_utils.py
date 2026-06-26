"""Tests for shared EarphoneCommon utility helpers."""

import pytest

from earphone.modules.common.utils import (
    _to_u32,
    _to_s32,
    _sign_extend,
    _pack_u16_lanes,
    _unpack_u16_lanes,
)


class TestCommonUtils:
    def test_to_u32_truncates(self):
        assert _to_u32(0) == 0
        assert _to_u32(0xFFFFFFFF) == 0xFFFFFFFF
        assert _to_u32(0x1FFFFFFFF) == 0xFFFFFFFF
        assert _to_u32(-1) == 0xFFFFFFFF

    def test_to_s32_sign_extend(self):
        assert _to_s32(0) == 0
        assert _to_s32(0x7FFFFFFF) == 0x7FFFFFFF
        assert _to_s32(0xFFFFFFFF) == -1
        assert _to_s32(0x80000000) == -0x80000000

    def test_sign_extend_various_widths(self):
        assert _sign_extend(0x7FFF, 16) == 0x7FFF
        assert _sign_extend(0xFFFF, 16) == 0xFFFFFFFF
        assert _sign_extend(0xFF, 8) == 0xFFFFFFFF
        assert _sign_extend(0x7F, 8) == 0x7F
        assert _sign_extend(0b100, 3) == 0xFFFFFFFC  # -4 sign-extended

    def test_pack_unpack_u16_lanes(self):
        lanes = list(range(16))  # 0..15
        packed = _pack_u16_lanes(lanes)
        assert _unpack_u16_lanes(packed) == lanes

    def test_pack_unpack_arbitrary_values(self):
        lanes = [0xFFFF - i for i in range(16)]
        packed = _pack_u16_lanes(lanes)
        assert _unpack_u16_lanes(packed) == lanes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
