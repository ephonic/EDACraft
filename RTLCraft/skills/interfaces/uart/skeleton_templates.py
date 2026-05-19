"""
skills.interfaces.uart.skeleton_templates — UART DSL Skeleton Steps

PE type → implementation step descriptions for ArchSkeletonGenerator.
Registered on import via register_uart_skeleton_steps().
"""
from __future__ import annotations

from rtlgen.arch_skel import _TEMPLATE_STEPS

_UART_SKELETON_STEPS: dict[str, list[str]] = {
    "uart_tx": [
        "1. 实现 prescale 计数器（prescale << 3 作为每 bit 周期）",
        "2. 实现空闲状态检测（bit_cnt=0 时 s_axis_tready=1）",
        "3. 实现帧格式：start(0) + {data_width} + stop(1)，data_reg 初始化为 {1'b1, data}",
        "4. 实现移位输出：{data_reg, txd_reg} <= {1'b0, data_reg} 右移",
        "5. 实现 busy 信号（bit_cnt > 0 时为 1）",
        "6. 验证：对比 behavioral model 的 txd 波形和 timing",
    ],
    "uart_rx": [
        "1. 实现 start bit 检测（rxd 下降沿触发，prescale 设为半周期）",
        "2. 实现 data 采样：rxd_reg 移入 data_reg，LSB first",
        "3. 实现 stop bit 校验（rxd=1 → valid, rxd=0 → frame_error）",
        "4. 实现 overrun 检测（m_axis_tvalid 未被消费时收到新数据）",
        "5. 实现 busy 信号（bit_cnt > 0 时为 1）",
        "6. 验证：对比 behavioral model 的接收数据序列",
    ],
    "uart_top": [
        "1. 实例化 uart_tx 和 uart_rx",
        "2. 将 TX 输出 txd 连接到外部，RX 输入 rxd 来自外部",
        "3. 透传 AXI-Stream 接口（s_axis → tx, rx → m_axis）",
        "4. 输出 tx_busy 和 rx_busy 状态",
        "5. 验证：loopback 测试（txd → rxd 短接）",
    ],
}


def register_uart_skeleton_steps():
    """Register UART skeleton steps into the global template steps."""
    for key, steps in _UART_SKELETON_STEPS.items():
        _TEMPLATE_STEPS[key] = steps


# Auto-register on import
register_uart_skeleton_steps()

__all__ = ["register_uart_skeleton_steps", "_UART_SKELETON_STEPS"]
