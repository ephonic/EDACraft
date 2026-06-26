"""
skills.interfaces.axi_lite.skeleton_templates — AXI-Lite RAM DSL Skeleton Steps

PE type -> implementation step descriptions for ArchSkeletonGenerator.
Registered on import via register_axil_skeleton_steps().
"""
from __future__ import annotations

from rtlgen.arch_skel import _TEMPLATE_STEPS

_AXIL_SKELETON_STEPS: dict[str, list[str]] = {
    "axil_ram": [
        "1. 实现写地址通道握手：awvalid & wvalid & !bvalid 时 awready=1",
        "2. 实现写数据通道握手：awvalid & wvalid & !bvalid 时 wready=1",
        "3. 实现写响应：awvalid & wvalid & !bvalid 时 bvalid=1，bresp=OK",
        "4. 实现写地址锁存（awaddr_reg）和写数据到内存（mem[awaddr] = wdata）",
        "5. 实现写响应清除：bready & bvalid 时 bvalid_reg=0",
        "6. 实现读地址通道握手：arvalid & (!rvalid | rready) 时 arready=1",
        "7. 实现读响应：arvalid & (!rvalid | rready) 时 rvalid=1，rresp=OK",
        "8. 实现读地址锁存（araddr_reg）和读数据（rdata = mem[araddr]）",
        "9. 实现读响应清除：rready & rvalid 时 rvalid_reg=0",
        "10. 实现复位：所有 ready/valid 寄存器清零",
        "11. 验证：write-then-read 回环测试，数据一致性检查",
    ],
}


def register_axil_skeleton_steps():
    """Register AXI-Lite skeleton steps into the global template steps."""
    for key, steps in _AXIL_SKELETON_STEPS.items():
        _TEMPLATE_STEPS[key] = steps


# Auto-register on import
register_axil_skeleton_steps()

__all__ = ["register_axil_skeleton_steps", "_AXIL_SKELETON_STEPS"]
