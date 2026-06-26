"""
skills.interfaces.axi.skeleton_templates — AXI DSL Skeleton Steps
"""
from __future__ import annotations

from rtlgen.arch_skel import _TEMPLATE_STEPS

_AXI_SKELETON_STEPS: dict[str, list[str]] = {
    "axi_dp_ram_simple": [
        "1. 实现共享 memory array（2^addr_width × data_width）",
        "2. 实现 Port A 写通道：awvalid+wvalid → awready+wready+bvalid",
        "3. 实现 Port A 读通道：arvalid → arready+rvalid+data from mem",
        "4. 实现 Port B 写通道：与 Port A 独立的 AXI-Lite 握手",
        "5. 实现 Port B 读通道：与 Port A 独立的 AXI-Lite 握手",
        "6. 实现 response 清除：bready/bvalid, rready/rvalid",
        "7. 验证：双端口同时读写不冲突",
    ],
}


def register_axi_skeleton_steps():
    for key, steps in _AXI_SKELETON_STEPS.items():
        _TEMPLATE_STEPS[key] = steps


register_axi_skeleton_steps()

__all__ = ["register_axi_skeleton_steps", "_AXI_SKELETON_STEPS"]
