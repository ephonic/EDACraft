"""
skills.interfaces.wishbone.skeleton_templates — Wishbone DSL Skeleton Steps
"""
from __future__ import annotations

from rtlgen.arch_skel import _TEMPLATE_STEPS

_WISHBONE_SKELETON_STEPS: dict[str, list[str]] = {
    "wb_reg": [
        "1. 实现双向寄存器（master→slave 和 slave→master）",
        "2. 实现 idle 状态：master 信号直通到 slave",
        "3. 实现 cycle 状态：wbs_cyc_o & wbs_stb_o 时保持值",
        "4. 实现响应传递：ack/err/rty 到来时 slave→master",
        "5. 实现 we/stb 门控：防止重叠事务",
        "6. 验证：对比 reference 的事务时序",
    ],
    "wb_mux_2": [
        "1. 实现地址匹配：match = ~|((adr ^ addr) & addr_msk)",
        "2. 实现优先级：slave0 优先于 slave1",
        "3. 实现数据 MUX：选中 slave 的 dat 到 master",
        "4. 实现响应 OR 归约：ack/err/rty 从所有 slave 汇总",
        "5. 实现 select_error：无匹配地址时报错",
        "6. 验证：地址解码正确性和优先级",
    ],
}


def register_wishbone_skeleton_steps():
    for key, steps in _WISHBONE_SKELETON_STEPS.items():
        _TEMPLATE_STEPS[key] = steps


register_wishbone_skeleton_steps()

__all__ = ["register_wishbone_skeleton_steps", "_WISHBONE_SKELETON_STEPS"]
