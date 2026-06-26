"""
skills.interfaces.spi.skeleton_templates — DSL Skeleton Steps for SPI Controller

Maps PE types to implementation step lists for the ArchSkeletonGenerator.
Registered at import time via register_spi_skeleton_steps().
"""
from __future__ import annotations

from typing import Dict, List

from rtlgen.arch_skel import _TEMPLATE_STEPS


_SPI_SKELETON_STEPS: Dict[str, List[str]] = {
    "spi_registers": [
        "1. 实现 APB 接口：psel/penable/pwrite/paddr 的 2-cycle 读写时序（setup + access phase）",
        "2. 实现 CONFIG 寄存器（0x00）：master/cpol/cpha/cks/pdec/ss/datasize/baud_rate/man_cs/man_start_en/man_start/modf_en/bsr/m_shiften_del_en 字段",
        "3. 实现 STATUS 寄存器（0x04）：tx_empty/tx_notfull/rx_notempty/rx_full/tx_underflow/s_modf/m_modf 标志位",
        "4. 实现 IMASK 寄存器（0x08）：7-bit 中断掩码（rx_full/rx_notempty/tx_notfull/tx_empty/tx_underflow/s_modf/m_modf）",
        "5. 实现 ENABLE 寄存器（0x0C）：单 bit spi_enable",
        "6. 实现 DELAY 寄存器（0x10）：4×8-bit 延迟字段（d_init/d_after/d_btwn/d_nss）",
        "7. 实现 TXD 写操作（0x14）：TX FIFO push，带 tx_full 保护",
        "8. 实现 RXD 读操作（0x18）：RX FIFO pop，带 rx_notempty 保护",
        "9. 实现 SIC/TX_THRESH/RX_THRESH 寄存器（0x1C/0x20/0x24）",
        "10. 实现中断输出：OR 7 个 masked 中断源",
        "11. 验证：APB 读写所有寄存器字段，中断掩码生效",
    ],
    "spi_control": [
        "1. 实现 12 状态 FSM：RESET(0) → M_IDLE(1) → M_PREAMBLE(2) → M_SHIFT1(3) → M_SHIFT2(4) → M_POSTAMBLE(5) → M_PAUSE(6) → S_IDLE(7) → S_PREAMBLE(8) → S_SHIFT(9) → S_POSTAMBLE(10) → S_DONE(11)",
        "2. 实现 master_count 倒计时器：用于 preamble/postamble/pause/delay 计时，由 m_clocken 门控",
        "3. 实现 m_txsel 比特选择计数器：每个 sclk 边沿递减，到 datasize 边界时自动重载",
        "4. 实现 ds_txsel 字计数器：跟踪 FIFO word 内的数据传输数量",
        "5. 实现 master shift enable 生成：由 master_count + baud_rate 分频控制",
        "6. 实现 slave 同步逻辑：idle_count（sic_reg 倒计时）、sync_in_burst、sync_immed 状态机",
        "7. 实现 busfree 计数器：检测 n_ss_in 空闲以触发自动传输",
        "8. 实现 mode-fail 检测：master 模式下 n_ss_in 被拉低、slave 模式下 n_ss_in 被拉高",
        "9. 实现 tx_underflow 检测和 gate_tx 保护",
        "10. 实现 shift-enable sample-point 延迟计数器（m_shiften_del_en）",
        "11. 实现 manual start 支持（man_start_en + man_start 触发传输）",
        "12. 验证：对比 behavioral model 的 FSM 状态序列和时序",
    ],
    "spi_transmit": [
        "1. 实现 TX FIFO（8-entry × 32-bit）：wr_clk/rd_clk 双时钟域，push/pop/clear 操作",
        "2. 实现 master_out 寄存器：仅在 m_out_change 时加载 FIFO 数据（无毛刺输出）",
        "3. 实现 so_reg（3-bit）：slave 模式下寄存 TX FIFO 低 3 位用于尾部数据保持",
        "4. 实现 32:1 并行到串行 MUX（cdnsspi_mux_wto1）：由 m_txsel/s_txsel 选择输出位",
        "5. 实现输出使能：n_mo_en/n_so_en/n_ss_en/n_sclk_en（active-low tri-state control）",
        "6. 实现 slave select 解码：4-bit one-hot 编码（0xE/0xD/0xB/0x7）或 pass-through",
        "7. 实现 FIFO 状态标志：tx_empty/tx_notfull/tx_full/threshold",
        "8. 验证：TX FIFO push → 串行输出正确，master/slave 切换无毛刺",
    ],
    "spi_receive": [
        "1. 实现输入 MUX：master 模式选 mi_i，slave 模式选 si_sync3_i",
        "2. 实现 32-bit 串行到并行移位寄存器：左移输入，s_shiften/m_shiften 控制",
        "3. 实现 RX FIFO（8-entry × 32-bit）：push/pop/clear 操作",
        "4. 实现 FIFO 状态标志：rx_notempty/rx_full/threshold",
        "5. 验证：串行输入 → 移位 → FIFO push → APB 读取数据一致",
    ],
    "spi_slave_sync": [
        "1. 实现 SI 输入 3-flop 同步链：防止亚稳态传播",
        "2. 实现 n_ss_in 同步链 + 下降沿检测：生成 s_inprogress 信号",
        "3. 实现 slave 时钟生成：sclk_in 经 CPOL/CPHA 极性/相位调整后作为 slave_out_clk",
        "4. 实现 spi_enable 3-cycle 延迟链：spi_enable_del3",
        "5. 实现 s_shiften 生成：n_ss_in 下降沿在 burst 中触发移位使能",
        "6. 实现 tx_underflow 检测：TX FIFO empty 且 slave 传输进行中",
        "7. 验证：si_i 经过 3 拍延迟到 si_sync3，n_ss_in 下降沿触发 s_inprogress",
    ],
    "spi_slave_tx": [
        "1. 实现 s_txsel 5-bit 递减计数器：初值为 FIFO_W_SIZE-1，每次 sclk 递减",
        "2. 实现 wrap-around：计数到 0 后回到 FIFO_W_SIZE-1",
        "3. 实现 s_txsel_start：n_ss_in 下降沿或 CPHA=0 时初始化",
        "4. 验证：s_txsel 在每个 sclk 周期正确递减，word 边界 wrap 正确",
    ],
    "spi_ext_sync": [
        "1. 实现 ext_clk 2-flop 同步链：外部时钟同步到 pclk 域",
        "2. 实现上升沿检测：~ext_clk_sync3 & ext_clk_sync2",
        "3. 实现 m_clocken 输出：cks=0 时恒为 1，cks=1 时为 ext_clk 上升沿脉冲",
        "4. 验证：cks 切换时 m_clocken 行为正确，无毛刺",
    ],
}


def register_spi_skeleton_steps():
    """Register SPI PE type implementation steps into the skeleton template registry."""
    _TEMPLATE_STEPS.update(_SPI_SKELETON_STEPS)


# Auto-register on import
register_spi_skeleton_steps()

__all__ = ["register_spi_skeleton_steps", "_SPI_SKELETON_STEPS"]
