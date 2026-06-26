"""EarphoneCommon shared utility package.

Public API:
    - _to_u32, _to_s32, _sign_extend, _pack_u16_lanes, _unpack_u16_lanes
"""

from __future__ import annotations

from earphone.modules.common.utils import (
    _to_u32,
    _to_s32,
    _sign_extend,
    _pack_u16_lanes,
    _unpack_u16_lanes,
)

__all__ = [
    "_to_u32",
    "_to_s32",
    "_sign_extend",
    "_pack_u16_lanes",
    "_unpack_u16_lanes",
]
