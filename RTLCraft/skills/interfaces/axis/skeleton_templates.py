"""
skills.interfaces.axis.skeleton_templates — AXI-Stream DSL Skeleton Steps
"""
from __future__ import annotations

from rtlgen.arch_skel import _TEMPLATE_STEPS

_AXIS_SKELETON_STEPS: dict[str, list[str]] = {
    "axis_register": [
        "1. 实现 skid buffer 三路状态：input→output, input→temp, temp→output",
        "2. 实现 ready early 逻辑：m_tready | (~temp_valid & (~out_valid | ~in_valid))",
        "3. 实现组合逻辑 next state（store_to_output/store_to_temp/store_temp_to_output）",
        "4. 实现数据寄存器根据控制信号更新",
        "5. 实现 reset：所有 valid 清零",
        "6. 验证：无 bubble cycle，back-to-back 传输",
    ],
    "axis_adapter": [
        "1. 实现 per-segment 寄存器（避免动态 slice）",
        "2. 实现 seg_cnt 计数器（0 → seg_count-1 循环）",
        "3. 实现输入收集：每个 beat 写入当前 segment",
        "4. 实现 tlast 传播：最后一个 beat 或 seg_cnt 满时输出",
        "5. 实现 input skid buffer（output 忙时缓存输入）",
        "6. 验证：8→32 转换，4 个输入 beat 产生 1 个输出 word",
    ],
    "axis_broadcast": [
        "1. 实现数据广播：input data 复制到所有 M 输出",
        "2. 实现 per-output valid 向量（m_count bits）",
        "3. 实现 all_ready 检测：(m_ready & m_valid) == m_valid",
        "4. 实现 skid buffer 处理 back-pressure",
        "5. 实现 temp register 当 output 未就绪时缓存",
        "6. 验证：独立 ready 信号下数据正确广播",
    ],
}


def register_axis_skeleton_steps():
    for key, steps in _AXIS_SKELETON_STEPS.items():
        _TEMPLATE_STEPS[key] = steps


register_axis_skeleton_steps()

__all__ = ["register_axis_skeleton_steps", "_AXIS_SKELETON_STEPS"]
