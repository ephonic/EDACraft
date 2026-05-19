"""
skills.cpu.skeleton_templates — CPU PE Type → Implementation Steps

PE type → implementation step mappings for CPU pipeline stages.
Used by ArchSkeletonGenerator when generating AgentPackage for CPU PEs.
"""

IFU_STEPS = [
    "1. 实现 PC 寄存器（seq block with reset）",
    "2. 实现 PC 递增逻辑（pc_next = pc + 4 * issue_width）",
    "3. 实现分支预测结构（BTB/BHT/RAS 查找）",
    "4. 整合预测结果到 PC 选择器",
    "5. 实现取指数据打包（指令 bundle 输出）",
    "6. 实现停顿/冲刷处理",
    "7. 验证：对比 behavior model 的 PC 序列和指令流",
]

IDU_STEPS = [
    "1. 实现指令解码逻辑（opcode → func）",
    "2. 实现寄存器重命名表（arch → preg）",
    "3. 实现分发队列（dispatch queue）",
    "4. 实现到各 pipe 的信号分发",
    "5. 实现 stall 处理（ROB full → stall IFU）",
    "6. 验证：对比 behavior model 的分发序列",
]

ALU_STEPS = [
    "1. 实现多 pipe 分发逻辑（opcode → pipe）",
    "2. 实现各 pipe 的算子（ALU/Mult/BJU）",
    "3. 实现旁路网络（bypass/forwarding）",
    "4. 实现 completion 信号到 RTU",
    "5. 实现异常/中断处理",
    "6. 验证：对比 behavior model 的运算结果",
]

LSU_STEPS = [
    "1. 实现地址计算（base + offset）",
    "2. 实现 Load Queue / Store Queue",
    "3. 实现 D-Cache 接口",
    "4. 实现数据前递（load → ALU bypass）",
    "5. 实现内存序约束（fence/acquire/release）",
    "6. 验证：对比 behavior model 的访存序列",
]

RTU_STEPS = [
    "1. 实现 ROB 队列（create → complete → retire）",
    "2. 实现 commit/retire 逻辑",
    "3. 实现异常/flush 生成",
    "4. 实现物理寄存器状态管理",
    "5. 验证：对比 behavior model 的 retire 序列",
]

REGFILE_STEPS = [
    "1. 实现多读多写寄存器文件",
    "2. 实现读写端口仲裁",
    "3. 实现 bypass 逻辑（同时读写同一寄存器）",
    "4. 验证：对比 behavior model 的寄存器状态",
]

BPU_STEPS = [
    "1. 实现 BTB（Branch Target Buffer）查找表",
    "2. 实现 BHT/TAGE 预测器（全局/局部历史）",
    "3. 实现 RAS（Return Address Stack）",
    "4. 实现预测结果合并和输出",
    "5. 实现反馈更新机制（执行结果 → 预测器训练）",
    "6. 验证：对比 behavior model 的预测准确率",
]

ISSUE_QUEUE_STEPS = [
    "1. 实现 reservation station 条目管理",
    "2. 实现操作数就绪检测（wakeup 端口）",
    "3. 实现 select 逻辑（从就绪条目中选择发射）",
    "4. 实现发射队列满/空标志",
    "5. 验证：对比 behavior model 的发射序列",
]

CACHE_STEPS = [
    "1. 实现 tag/data 阵列",
    "2. 实现 LRU 替换逻辑",
    "3. 实现 miss/refill 状态机",
    "4. 实现写策略（write-through/write-back）",
    "5. 验证：对比行为模型的 hit/miss 模式",
]


def register_cpu_skeleton_steps(template_steps: dict):
    """Register CPU skeleton steps into arch_skel._TEMPLATE_STEPS.

    Usage:
        from rtlgen import arch_skel
        from skills.cpu.skeleton_templates import register_cpu_skeleton_steps
        register_cpu_skeleton_steps(arch_skel._TEMPLATE_STEPS)
    """
    template_steps["ifu"] = IFU_STEPS
    template_steps["idu"] = IDU_STEPS
    template_steps["alu"] = ALU_STEPS
    template_steps["lsu"] = LSU_STEPS
    template_steps["rtu"] = RTU_STEPS
    template_steps["regfile"] = REGFILE_STEPS
    template_steps["bpu"] = BPU_STEPS
    template_steps["issue_queue"] = ISSUE_QUEUE_STEPS
    template_steps["cache"] = CACHE_STEPS
