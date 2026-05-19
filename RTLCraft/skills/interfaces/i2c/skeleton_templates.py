"""
skills.interfaces.i2c.skeleton_templates — I2C DSL Skeleton Steps
"""
from __future__ import annotations

from rtlgen.arch_skel import _TEMPLATE_STEPS

_I2C_SKELETON_STEPS: dict[str, list[str]] = {
    "i2c_single_reg": [
        "1. 实现输入滤波器：FILTER_LEN 位移位寄存器 + 全0/全1判决",
        "2. 实现 start/stop 检测：SDA 边沿在 SCL 高电平时",
        "3. 实现 ADDRESS 状态：移位接收 7-bit 地址 + R/W 位",
        "4. 实现 ACK 状态：地址匹配后拉低 SDA",
        "5. 实现 WRITE 路径：WRITE_1→WRITE_2 两拍接收 8-bit 数据",
        "6. 实现 READ 路径：READ_1→READ_2→READ_3 三拍发送数据",
        "7. 验证：对比 behavioral model 的 SDA 波形",
    ],
}


def register_i2c_skeleton_steps():
    for key, steps in _I2C_SKELETON_STEPS.items():
        _TEMPLATE_STEPS[key] = steps


register_i2c_skeleton_steps()

__all__ = ["register_i2c_skeleton_steps", "_I2C_SKELETON_STEPS"]
