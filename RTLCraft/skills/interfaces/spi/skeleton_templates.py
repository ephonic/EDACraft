"""
skills.interfaces.spi.skeleton_templates — SPI DSL Skeleton Steps

PE type → implementation step descriptions for ArchSkeletonGenerator.
Registered on import via register_spi_skeleton_steps().
"""
from __future__ import annotations

from rtlgen.arch_skel import _TEMPLATE_STEPS

_SPI_SKELETON_STEPS: dict[str, list[str]] = {
    "spi_clock_divider": [
        "1. 实现自由运行计数器，位宽为 DIV_N",
        "2. 输出 clk_out 取计数器最高位（MSB）",
        "3. 复位时计数器清零，is_ready 置 1",
        "4. 验证：对比 behavioral model 的 clk_out 分频波形",
    ],
    "spi_module": [
        "1. 实现边沿检测器（pos_edge_det / neg_edge_det）实例",
        "2. 实现 CPOL/CPHA 组合逻辑：delay_pol, get_number_edge, switch_number_edge",
        "3. 实现 2-state FSM：IDLE(0) → CYCLE_BITS(7) → IDLE",
        "4. 实现 bit_counter 移位计数（支持 MSB/LSB first 由 INVERT_DATA_ORDER 控制）",
        "5. 实现 MOSI 输出（data_word_send[bit_counter]）和 MISO 采样",
        "6. 实现 Master/Slave 模式选择（SPI_MASTER 控制 SCLK_OUT / SS_OUT 来源）",
        "7. 验证：对比 behavioral model 在所有 4 种 SPI 模式下的波形",
    ],
    "spi_top": [
        "1. 实例化 spi_clock_divider 和 spi_module",
        "2. Master 模式下 sclk_in 接分频器输出，Slave 模式下接外部 sclk",
        "3. 实现 is_ready 门控（Master 时 = core_ready & divider_ready）",
        "4. 将 SPI 引脚 sclk/ss/mosi/miso 连接到外部",
        "5. 验证：Master-Slave loopback 测试",
    ],
}


def register_spi_skeleton_steps():
    """Register SPI skeleton steps into the global template steps."""
    for key, steps in _SPI_SKELETON_STEPS.items():
        _TEMPLATE_STEPS[key] = steps


# Auto-register on import
register_spi_skeleton_steps()

__all__ = ["register_spi_skeleton_steps", "_SPI_SKELETON_STEPS"]
