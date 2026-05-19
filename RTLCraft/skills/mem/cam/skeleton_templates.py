"""
skills.mem.cam.skeleton_templates — DSL Skeleton Steps for CAM

Maps PE types to implementation step lists for the ArchSkeletonGenerator.
Registered at import time via register_cam_skeleton_steps().
"""
from __future__ import annotations

from typing import Dict, List

from rtlgen.arch_skel import _TEMPLATE_STEPS


_CAM_SKELETON_STEPS: Dict[str, List[str]] = {
    "priority_encoder": [
        "1. 实现参数化优先级编码器：WIDTH 输入，$clog2(WIDTH) 位编码输出",
        "2. 实现 LSB_PRIORITY 参数：\"HIGH\"=最低位优先，\"LOW\"=最高位优先",
        "3. 实现递归树结构：WIDTH=1 时直接输出，WIDTH=2 时用 OR+MUX，WIDTH>2 时 split 为两半并递归",
        "4. 实现 power-of-two 填充：非 2 的幂次宽度时用零填充到最近的 2 的幂次",
        "5. 实现 output_unencoded：1 << output_encoded",
        "6. 实现 output_valid：valid1 | valid2（任一子树有效即有效）",
        "7. 验证：输入 8'b00100100，LSB_PRIORITY=\"HIGH\" 输出 encoded=2, unencoded=8'b00000100",
        "8. 验证：输入 8'b00100100，LSB_PRIORITY=\"LOW\"  输出 encoded=5, unencoded=8'b00100000",
    ],
    "ram_dp": [
        "1. 实现双端口 RAM：Port A 和 Port B 各有独立的 clk/we/addr/din/dout",
        "2. 实现 read-first 行为：先读旧值，写时同时更新输出寄存器为新值",
        "3. 实现独立时钟域：a_clk 控制 Port A 操作，b_clk 控制 Port B 操作",
        "4. 实现零初始化：initial 块用嵌套循环将 mem 全部清零（合成器友好）",
        "5. 实现输出寄存器：a_dout_reg 和 b_dout_reg 在时钟边沿更新",
        "6. 验证：Port A 写入地址 X 的数据 D，Port B 读取地址 X 得到 D",
        "7. 验证：Port A 和 Port B 同时写入不同地址无冲突",
    ],
    "cam_srl": [
        "1. 实现 4 状态 FSM：INIT(0) → IDLE(1) → WRITE(2) / DELETE(3) → IDLE",
        "2. 实现 INIT 状态：count_reg 从 (2^SLICE_WIDTH-1) 递减到 0，shift_en 全 1，shift_data 全 0",
        "3. 实现 IDLE 状态：检测 write_enable，根据 write_delete 选择 WRITE 或 DELETE 路径",
        "4. 实现 WRITE 状态：shift_en = 1 << write_addr，shift_data[s] = (count_reg == write_data 的 slice s)",
        "5. 实现 DELETE 状态：shift_en = 1 << write_addr，shift_data 全 0（移入零即删除）",
        "6. 实现 SRL 存储阵列：RAM_DEPTH × SLICE_COUNT 个 SRL，每个深度 2^SLICE_WIDTH",
        "7. 实现 SRL 移位：shift_en[row] 为 1 时，srl_mem[row][slice] <= {srl_mem[row][slice][WIDTH-2:0], shift_data[slice]}",
        "8. 实现匹配逻辑：match_raw_out[s][row] = srl_mem[row][s][compare_data 的 slice s]",
        "9. 实现 match_many_raw：~shift_en AND 所有 match_raw_out[s] 的 AND",
        "10. 实现 match 流水线寄存器：match_many_reg <= match_many_raw（延迟一拍）",
        "11. 实例化 PriorityEncoder（LSB_PRIORITY=\"HIGH\"）：match_many_reg → match_addr + match_single",
        "12. 实现数据填充：compare_data/write_data 高位补零到 SLICE_COUNT*SLICE_WIDTH",
        "13. 验证：写入 0x1234 到地址 0，compare_data=0x1234 时 match=1，其他值 match=0",
        "14. 验证：删除地址 0 后，compare_data=0x1234 时 match=0",
    ],
    "cam_bram": [
        "1. 实现 6 状态 FSM：INIT(0) → IDLE(1) → DELETE_1(2) → DELETE_2(3) → WRITE_1(4) → WRITE_2(5) → IDLE",
        "2. 实现 INIT 状态：count_reg 递减，ram_addr = {SLICE_COUNT{count_reg}} 掩码后清零所有 BRAM slice",
        "3. 实现 IDLE 状态：write_enable 时进入 DELETE_1，缓存 write_addr/write_data/write_delete",
        "4. 实现 DELETE_1：等待 erase_ram 读数据（一拍延迟）",
        "5. 实现 DELETE_2：clear_bit = 1 << write_addr，wr_en=1 清除旧条目",
        "6. 实现 WRITE_1：等待一拍",
        "7. 实现 WRITE_2：set_bit = 1 << write_addr，wr_en=1 写入新条目",
        "8. 实现 erase_ram：data_width × ram_depth 阵列，跟踪每个地址最后写入的数据",
        "9. 实现 erase_ram 读写：write 时更新，read 时用 write_addr_next 作为地址",
        "10. 实现 BRAM slice 阵列：每个 slice 是 RamDP(DATA_WIDTH=RAM_DEPTH, ADDR_WIDTH=slice_width)",
        "11. 实现匹配逻辑：match_many_raw = AND 所有 slice 的 RamDP 读输出",
        "12. 实现 RamDP 端口映射：port A 用于匹配读（compare_data 为地址），port B 用于写（ram_addr 为地址）",
        "13. 实现写数据计算：b_din = (ram_data & ~clear_bit) | set_bit（读-改-写）",
        "14. 实例化 PriorityEncoder（LSB_PRIORITY=\"HIGH\"）：match_many_raw → match_addr + match_single",
        "15. 验证：写入 0x1234 到地址 0，compare_data=0x1234 时 match=1",
        "16. 验证：覆盖写入地址 0 为 0x5678，compare_data=0x1234 时 match=0，compare_data=0x5678 时 match=1",
    ],
    "cam_top": [
        "1. 实现 CAM_STYLE 参数：0=SRL，1=BRAM（整数编码，字符串不支持 generate-if 表达式）",
        "2. 实现 generate-if：CAM_STYLE==0 实例化 CamSRL，否则实例化 CamBRAM",
        "3. 实现端口透传：clk/rst/write_addr/write_data/write_delete/write_enable/compare_data → match_many/match_single/match_addr/match",
        "4. 验证：CAM_STYLE=0 时行为等价于 CamSRL",
        "5. 验证：CAM_STYLE=1 时行为等价于 CamBRAM",
    ],
}


def register_cam_skeleton_steps():
    """Register CAM PE type implementation steps into the skeleton template registry."""
    _TEMPLATE_STEPS.update(_CAM_SKELETON_STEPS)


# Auto-register on import
register_cam_skeleton_steps()

__all__ = ["register_cam_skeleton_steps", "_CAM_SKELETON_STEPS"]
