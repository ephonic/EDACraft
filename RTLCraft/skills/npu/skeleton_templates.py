"""
skills.npu.skeleton_templates — NPU PE Type → Implementation Steps

PE type → implementation step mappings for NPU pipeline stages.
Used by ArchSkeletonGenerator when generating AgentPackage for NPU PEs.
"""

SCHEDULER_STEPS = [
    "1. 实现指令寄存器（macro instruction write + ack handshake）",
    "2. 实现宏→微指令译码逻辑（字段提取 + 参数映射）",
    "3. 实现循环展开计数器（loop counter + depth 比较）",
    "4. 实现 micro instruction FIFO 输出（ready/valid 握手）",
    "5. 实现状态机（IDLE → DECODE → LOOP → DONE）",
    "6. 验证：对比 behavior model 的指令译码和展开序列",
]

TOP_SCHEDULER_STEPS = [
    "1. 实现指令链 RAM（指令存储 + 写端口）",
    "2. 实现 PC 计数器和状态机（IDLE → RUNNING → DONE）",
    "3. 实现多单元就绪检查（所有下游 FIFO 有空闲）",
    "4. 实现指令分发到各单元调度器",
    "5. 实现完成信号生成",
    "6. 验证：对比 behavior model 的 dispatch 序列",
]

MAC_DATAPATH_STEPS = [
    "1. 实现 NTILE × NDPE 乘法阵列（generate 循环实例化 DPE）",
    "2. 实现累加器（per-DPE INT32 累加）",
    "3. 实现 VRF 寄存器文件（多端口读写）",
    "4. 实现 tile 间流水控制（tile_ptr 递增 + 完成检测）",
    "5. 实现写回接口（accumulator → VRF writeback）",
    "6. 验证：对比 behavior model 的 MAC 计算结果",
]

FUNC_DATAPATH_STEPS = [
    "1. 实现函数选择器（func_op → 对应激活/运算单元）",
    "2. 实现各函数单元（ReLU/Sigmoid/Tanh/Add/Sub/Mul/Max）",
    "3. 实现流水线级延迟匹配（pipeline_stages 对齐）",
    "4. 实现输入/输出 FIFO 接口",
    "5. 验证：对比 behavior model 的函数输出",
]

EXT_VRF_STEPS = [
    "1. 实现多 bank VRF 阵列（num_banks × DEPTH × WIDTH）",
    "2. 实现 bank 访问仲裁（多请求 → bank 选择）",
    "3. 实现流水线延迟（bank_latency 周期访问）",
    "4. 实现读/写端口（独立读写 handshake）",
    "5. 验证：对比 behavior model 的 bank 访问和延迟",
]

LD_DATAPATH_STEPS = [
    "1. 实现输入 FIFO（in_fifo_depth 缓冲）",
    "2. 实现输出 FIFO（out_fifo_depth 缓冲）",
    "3. 实现 writeback FIFO（wb_fifo_depth 中间缓冲）",
    "4. 实现 VRF 写回接口（wr_en + wr_addr + wr_data）",
    "5. 实现流控（input→result→output 流水线）",
    "6. 验证：对比 behavior model 的 FIFO 计数和流控",
]


def register_npu_skeleton_steps(template_steps: dict):
    """Register NPU skeleton steps into arch_skel._TEMPLATE_STEPS.

    Usage:
        from rtlgen import arch_skel
        from skills.npu.skeleton_templates import register_npu_skeleton_steps
        register_npu_skeleton_steps(arch_skel._TEMPLATE_STEPS)
    """
    template_steps["npu_scheduler"] = SCHEDULER_STEPS
    template_steps["npu_top_scheduler"] = TOP_SCHEDULER_STEPS
    template_steps["npu_mac_datapath"] = MAC_DATAPATH_STEPS
    template_steps["npu_func_datapath"] = FUNC_DATAPATH_STEPS
    template_steps["npu_ext_vrf"] = EXT_VRF_STEPS
    template_steps["npu_ld_datapath"] = LD_DATAPATH_STEPS
