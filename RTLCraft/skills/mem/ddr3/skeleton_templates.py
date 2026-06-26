"""
skills.mem.ddr3.skeleton_templates — DDR3 Skeleton Steps

PE type → implementation step mappings for DDR3 controller PEs.
Registered at import time via register_ddr3_skeleton_steps().
"""
from __future__ import annotations

from typing import Dict, List

from rtlgen.arch_skel import _TEMPLATE_STEPS


_DDR3_SKELETON_STEPS: Dict[str, List[str]] = {
    "memory_controller": [
        "1. 实现初始化 FSM（POWERUP → CKE low → LOAD_MODE → ZQCL → PRECHARGE_ALL）",
        "2. 实现 refresh 定时器（64ms/8192 行倒计时 + 自动刷新触发）",
        "3. 实现 row buffer 管理（per-bank open row 跟踪 + hit/miss 检测）",
        "4. 实现命令调度 FSM（IDLE → ACTIVATE → READ/WRITE → PRECHARGE）",
        "5. 实现地址解码（RBC/BRC 模式：addr → row/bank/col）",
        "6. 实现 write ack / read data 返回逻辑",
        "7. 验证：对比 behavioral model 的状态序列和行缓冲区行为",
    ],
    "dfi_sequencer": [
        "1. 实现命令时序延迟（tRCD, tRP, tRFC 等 JEDEC 时序）",
        "2. 实现写数据序列化（128-bit → 32-bit DFI burst）",
        "3. 实现读数据组装（32-bit → 128-bit 拼合）",
        "4. 实现 shift register 延迟跟踪（accept/early-accept）",
        "5. 实现 DFI 输出映射（command → cs_n/ras_n/cas_n/we_n）",
        "6. 验证：对比 behavioral model 的 DFI 信号序列",
    ],
    "fifo": [
        "1. 实现同步 FIFO 指针管理（rd_ptr/wr_ptr/count）",
        "2. 实现 push/pop 操作：push 时写入 RAM 并递增 wr_ptr，pop 时递增 rd_ptr",
        "3. 实现 full/empty 检测：count == depth 为满，count == 0 为空",
        "4. 实现接受/有效信号：accept = not full, valid = not empty",
        "5. 验证：push N 个数据后 pop N 个，数据顺序一致",
    ],
}


def register_ddr3_skeleton_steps():
    """Register DDR3 PE type implementation steps into the skeleton template registry."""
    _TEMPLATE_STEPS.update(_DDR3_SKELETON_STEPS)


# Auto-register on import
register_ddr3_skeleton_steps()

# Legacy alias for backward compatibility
def register_memory_skeleton_steps(template_steps: dict):
    """Register memory skeleton steps into arch_skel._TEMPLATE_STEPS (legacy)."""
    template_steps["memory_controller"] = _DDR3_SKELETON_STEPS["memory_controller"]
    template_steps["dfi_sequencer"] = _DDR3_SKELETON_STEPS["dfi_sequencer"]


__all__ = ["register_ddr3_skeleton_steps", "register_memory_skeleton_steps", "_DDR3_SKELETON_STEPS"]
