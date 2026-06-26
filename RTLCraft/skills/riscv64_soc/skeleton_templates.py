"""
skills.riscv64_soc.skeleton_templates — SoC PE Type → Implementation Steps

PE type → implementation step mappings for 64-core RISC-V SoC.
Used by ArchSkeletonGenerator when generating AgentPackage for SoC PEs.
"""

RV64_CORE_STEPS = [
    "1. 实现 5-stage pipeline 顶层（F/D/E/M/W 寄存器 + 控制逻辑）",
    "2. 实现 Fetch stage（PC 寄存器 + I-Cache 请求/响应接口）",
    "3. 实现 Decode stage（指令译码 + 寄存器读 + 立即数生成 +  forwarding）",
    "4. 实现 Execute stage（ALU Mux chain: ADD/SUB/XOR/OR/AND/SLL/SRL/SRA/SLT/SLTU）",
    "5. 实现 Branch 逻辑（BEQ 比较 + PC 重定向）",
    "6. 实现 Memory stage（D-Cache 接口 + load/store 数据通路）",
    "7. 实现 Writeback stage（结果写回寄存器文件）",
    "8. 实现 Stall/Hazard 检测（ICache stall + DCache stall + branch redirect）",
    "9. 验证：对比 behavioral model 的指令吞吐率和 PC 序列",
]

L1_CACHE_STEPS = [
    "1. 实现 cache 参数化配置（WAYS, SETS, LINE_SIZE）",
    "2. 实现 Tag RAM（tag 比较 + valid 位）",
    "3. 实现 Data RAM（line_size × ways 数据存储）",
    "4. 实现 LRU 替换逻辑（per-set counter）",
    "5. 实现 MSI 状态跟踪（per-line: Invalid/Shared/Modified）",
    "6. 实现 coherence 接口（snoop request/invalidation/fill）",
    "7. 实现 hit/miss 路径（hit → 1 cycle, miss → stall + coherence request）",
    "8. 验证：对比 behavioral model 的 cache hit rate",
]

COHERENCE_DIR_STEPS = [
    "1. 实现 directory entry（tag + state + sharers bitmask + owner）",
    "2. 实现 64-bit sharers 跟踪（per-core bitmask）",
    "3. 实现 Shared 请求处理（添加 sharer, M→S downgrade）",
    "4. 实现 Modified 请求处理（invalidate 当前 owner, 授予新 owner）",
    "5. 实现 invalidation 消息生成（向被驱逐 owner 发送 snoop）",
    "6. 实现 directory 查找（tag match + state decode）",
    "7. 验证：对比 behavioral model 的 coherence state 转换序列",
]

L2_CACHE_STEPS = [
    "1. 实现 L2 bank 参数化配置（WAYS, SETS, BANK_ID）",
    "2. 实现 Tag RAM + Data RAM（比 L1 更大）",
    "3. 实现 LRU 替换逻辑",
    "4. 实现 DRAM 接口（miss → DRAM 请求/响应）",
    "5. 实现 coherence upstream（向 directory 发送 fill ack）",
    "6. 验证：对比 behavioral model 的 L2 hit rate 和 DRAM 访问次数",
]

NOC_ROUTER_STEPS = [
    "1. 实现 5-port router 顶层互连（E/W/N/S/J buffers + crossbar + XY routing）",
    "2. 实现 per-port NoCBuffer 实例化（FIFO + push/pop + empty/full）",
    "3. 实现 XY routing function（坐标比较 → 5-bit valid_out）",
    "4. 实现 crossbar（5 路输入的 5 路输出复用器）",
    "5. 实现 round-robin 仲裁器（per-output-port 请求仲裁）",
    "6. 实现 credit-based flow control（ready/valid handshake）",
    "7. 实现 wormhole switching（header flit 路由决策 + body/tail 跟随）",
    "8. 验证：对比 behavioral model 的 flit 转发路径和延迟",
]

CLUSTER_STEPS = [
    "1. 实现 ClusterTop 互连（RV64Core + L1Cache×2 + CoherenceDir + L2CacheSlice + NoCRouter）",
    "2. 实现 Core → I-Cache 接口连接",
    "3. 实现 Core → D-Cache 接口连接",
    "4. 实现 L1Cache → CoherenceDir 接口连接",
    "5. 实现 CoherenceDir → L2CacheSlice 接口连接",
    "6. 实现 L2CacheSlice → NoCRouter 接口连接",
    "7. 实现 NoCRouter → mesh 接口连接",
    "8. 验证：对比 behavioral model 的 cluster 级指令吞吐和 coherence 事务",
]

SOC_TOP_STEPS = [
    "1. 实现 8×8 mesh ClusterTop 阵列实例化",
    "2. 实现 east-west mesh 互连（相邻 cluster ew_flit 对接）",
    "3. 实现 north-south mesh 互连（相邻 cluster ns_flit 对接）",
    "4. 实现边界 cluster 端口 tie-off（边缘无连接的端口置 0）",
    "5. 实现全局时钟/复位分发",
    "6. 实现全局统计（total retired, L1 hit rates, coherence traffic）",
    "7. 验证：对比 behavioral model 的全 SoC 性能指标",
]


def register_soc_skeleton_steps(template_steps: dict):
    """Register SoC skeleton steps into arch_skel._TEMPLATE_STEPS.

    Usage:
        from rtlgen import arch_skel
        from skills.riscv64_soc.skeleton_templates import register_soc_skeleton_steps
        register_soc_skeleton_steps(arch_skel._TEMPLATE_STEPS)
    """
    template_steps["rv64_core"] = RV64_CORE_STEPS
    template_steps["l1_cache"] = L1_CACHE_STEPS
    template_steps["coherence_dir"] = COHERENCE_DIR_STEPS
    template_steps["l2_cache"] = L2_CACHE_STEPS
    template_steps["noc_router"] = NOC_ROUTER_STEPS
    template_steps["cluster"] = CLUSTER_STEPS
    template_steps["soc_top"] = SOC_TOP_STEPS
