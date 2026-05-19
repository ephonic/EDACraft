"""
skills.gpgpu.skeleton_templates — GPGPU PE Type → Implementation Steps

PE type → implementation step mappings for GPGPU pipeline stages.
Used by ArchSkeletonGenerator when generating AgentPackage for GPGPU PEs.
"""

CTA_SCHEDULER_STEPS = [
    "1. 实现 inflight_wg_buffer：host 请求接收 + 缓冲（valid/ready 握手）",
    "2. 实现 allocator_neo：VGPR/SGPR/LDS 资源分配（CAM 查找空闲块）",
    "3. 实现 top_resource_table：全局资源跟踪表（已分配 VGPR/SGPR/LDS 起始地址和大小）",
    "4. 实现 dis_controller：dispatch FSM（idle → alloc → dispatch → flush）",
    "5. 实现 gpu_interface：将 workgroup 分发到 CU（CU 就绪检查 + round-robin 选择）",
    "6. 实现 workgroup 完成处理（warp_done 计数 → 释放资源 → 通知 host）",
    "7. 验证：对比 behavior model 的资源分配和 dispatch 序列",
]

WARP_SCHEDULER_STEPS = [
    "1. 实现 warp_active 跟踪寄存器（warpReq 置位，warp_end 清零）",
    "2. 实现 pc_control 实例的 generate 循环（per-warp PC 管理：jump/stall/halt/normal）",
    "3. 实现 fixed priority arbiter：从就绪 warp 中选择下一个取指 warp",
    "4. 实现 barrier 同步状态机（warp_bar_belong + warp_bar_data）",
    "5. 实现 warpRsp 完成信号（warp_end → 通知 CTA scheduler）",
    "6. 实现 flush 生成（branch_jump 或 warp_end → 冲刷 I-buffer）",
    "7. 验证：对比 behavior model 的 warp 调度序列和 barrier 行为",
]

PC_CONTROL_STEPS = [
    "1. 实现 PC 选择器（pc_src: 1=新warp, 2=正常递增, 3=stall, 4=branch）",
    "2. 实现 PC 递增逻辑（pc_next = pc + NUM_FETCH * 4）",
    "3. 实现 fetch mask 生成（哪些 instruction lane 有效）",
    "4. 实现 stall/jump/halt 状态切换",
    "5. 验证：对比 behavior model 的 PC 序列",
]

SM_WRAPPER_STEPS = [
    "1. 实现 cta2warp：接收 CTA dispatch → 生成 warp 请求（warpReq 握手）",
    "2. 实例化 pipe：SM 流水线（fetch/decode/IBuffer/Issue/OperandCollect/Execute/Writeback）",
    "3. 实现 instruction_cache：指令缓存 + 取指请求",
    "4. 实现 shared_mem：LDS 内存 + bank 冲突检测",
    "5. 实现 l1_dcache：数据缓存 + miss/refill 状态机",
    "6. 实现 LSU→D-cache FIFO 队列（缓冲 LSU 内存请求）",
    "7. 实现 cache invalidation（workgroup 完成时冲刷 L1 I-cache）",
    "8. 验证：对比 behavior model 的 warp 执行和内存访问模式",
]

PIPE_STEPS = [
    "1. 实现 Fetch 级：从 I-cache 取指 → 送入 Decode",
    "2. 实现 Decode 级：2-wide 解码 → 生成控制信号",
    "3. 实现 IBuffer 级：指令缓冲 + warp 选择",
    "4. 实现 Issue 级：发射到执行单元 + 依赖检查",
    "5. 实现 OperandCollect 级：收集操作数（寄存器读 + 前递）",
    "6. 实现 Execute 级：分发到 vALU/LSU/sALU/CSR/SIMT/SFU/MUL/TC/vFPU",
    "7. 实现 Writeback 级：写回结果 + 释放 scoreboard",
    "8. 验证：对比 behavior model 的流水线执行序列",
]

ARBITER_STEPS = [
    "1. 实现请求输入（req_i × N）",
    "2. 实现仲裁算法（round-robin / fixed-priority / LRU）",
    "3. 实现 grant 输出一热编码（grant_o × N）",
    "4. 实现 ready 反馈（用于握手）",
    "5. 验证：对比 behavior model 的仲裁序列",
]

SHARED_MEM_STEPS = [
    "1. 实现多 bank SRAM 阵列（NUM_BANK × DEPTH × WIDTH）",
    "2. 实现 bank 冲突检测（同一 bank 多请求 → stall 或 serialize）",
    "3. 实现地址到 bank 的映射（地址低位 → bank 索引）",
    "4. 实现读写端口（每 bank 独立访问）",
    "5. 验证：对比 behavior model 的 bank 访问模式",
]

POP_CNT_STEPS = [
    "1. 实现位计数逻辑（count number of 1s in input vector）",
    "2. 实现组合逻辑或流水线版本（根据宽度选择）",
    "3. 验证：对所有输入模式计数正确",
]


def register_gpgpu_skeleton_steps(template_steps: dict):
    """Register GPGPU skeleton steps into arch_skel._TEMPLATE_STEPS.

    Usage:
        from rtlgen import arch_skel
        from skills.gpgpu.skeleton_templates import register_gpgpu_skeleton_steps
        register_gpgpu_skeleton_steps(arch_skel._TEMPLATE_STEPS)
    """
    template_steps["cta_scheduler"] = CTA_SCHEDULER_STEPS
    template_steps["warp_scheduler"] = WARP_SCHEDULER_STEPS
    template_steps["pc_control"] = PC_CONTROL_STEPS
    template_steps["sm_wrapper"] = SM_WRAPPER_STEPS
    template_steps["pipe"] = PIPE_STEPS
    template_steps["arbiter"] = ARBITER_STEPS
    template_steps["shared_mem"] = SHARED_MEM_STEPS
    template_steps["pop_cnt"] = POP_CNT_STEPS
