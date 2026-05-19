"""
skills.interfaces.ethernet.skeleton_templates — Ethernet DSL Skeleton Steps
"""
from __future__ import annotations

from rtlgen.arch_skel import _TEMPLATE_STEPS

_ETHERNET_SKELETON_STEPS: dict[str, list[str]] = {
    "ptp_ts_extract": [
        "1. 实现 timestamp 提取：tuser[ts_offset+ts_width-1 : ts_offset]",
        "2. 实现 frame 跟踪寄存器：tvalid 时 frame_reg <= ~tlast",
        "3. 实现 valid 输出：s_axis_tvalid & ~frame_reg（首拍有效）",
        "4. 验证：每帧第一个 beat 输出 timestamp valid",
    ],
}


def register_ethernet_skeleton_steps():
    for key, steps in _ETHERNET_SKELETON_STEPS.items():
        _TEMPLATE_STEPS[key] = steps


register_ethernet_skeleton_steps()

__all__ = ["register_ethernet_skeleton_steps", "_ETHERNET_SKELETON_STEPS"]
