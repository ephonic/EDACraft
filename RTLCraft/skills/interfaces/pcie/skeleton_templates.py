"""
skills.interfaces.pcie.skeleton_templates — PCIe DSL Skeleton Steps
"""
from __future__ import annotations

from rtlgen.arch_skel import _TEMPLATE_STEPS

_PCIE_SKELETON_STEPS: dict[str, list[str]] = {
    "pulse_merge": [
        "1. 实现输入脉冲计数（population count of pulse_in）",
        "2. 实现计数器递减（每周期 -1，直到 0）",
        "3. 实现脉冲累加（count = count_base + pulse_sum）",
        "4. 实现饱和上限（不超过 (1<<count_width)-1）",
        "5. 实现 pulse_out = (count > 0)",
        "6. 验证：多个输入同时脉冲时计数正确",
    ],
    "pcie_ptile_fc": [
        "1. 实现 TDM 索引匹配：tx_cdts_limit_tdm_idx == index 时更新",
        "2. 实现 fc_cap 初始化（首次匹配时设置）",
        "3. 实现 fc_inc = tx_cdts_limit - fc_limit",
        "4. 实现饱和运算：fc_av = clamp(fc_av - fc_dec + fc_inc, 0, fc_cap)",
        "5. 验证：credit 不会超过 fc_cap，不会低于 0",
    ],
}


def register_pcie_skeleton_steps():
    for key, steps in _PCIE_SKELETON_STEPS.items():
        _TEMPLATE_STEPS[key] = steps


register_pcie_skeleton_steps()

__all__ = ["register_pcie_skeleton_steps", "_PCIE_SKELETON_STEPS"]
