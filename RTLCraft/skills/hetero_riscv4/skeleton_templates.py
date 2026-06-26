"""
skills.hetero_riscv4.skeleton_templates — Heterogeneous SoC PE Type → Implementation Steps

PE type → implementation step mappings for heterogeneous 4-core RISC-V SoC.
Used by ArchSkeletonGenerator when generating AgentPackage for SoC PEs.

Two formats per PE type:
  - *_STEPS: human-readable strings for AgentPackage.implementation_steps
  - *_TASKS: structured dicts for skill-guided generation (behavior_tags, keywords)
"""

# ── Human-readable steps (for AgentPackage) ──

PERF_CORE_STEPS = [
    "1. 实现 5-stage pipeline 顶层（F/D/E/M/W 寄存器 + 控制逻辑）",
    "2. 实现 Fetch stage（PC 寄存器 + I-Cache 请求/响应接口）",
    "3. 实现 Decode stage（指令译码 + 寄存器读 + 立即数生成 + forwarding）",
    "4. 实现 Execute stage（ALU Mux chain: ADD/SUB/XOR/OR/AND/SLL/SRL/SRA/SLT/SLTU）",
    "5. 实现 Branch 逻辑（BEQ 比较 + PC 重定向）",
    "6. 实现 Memory stage（D-Cache 接口 + load/store 数据通路）",
    "7. 实现 Writeback stage（结果写回寄存器文件）",
    "8. 实现 Stall/Hazard 检测（ICache stall + DCache stall + branch redirect）",
    "9. 验证：对比 behavioral model 的指令吞吐率和 PC 序列",
]

PERF_CORE_TASKS = [
    {"name": "pc_reg", "goal": "Program counter with branch redirect and stall freeze",
     "behavior_tags": ["program_counter", "branch_redirect", "icache_addr"],
     "keywords": ["pc_reg", "branch_target", "advance_by_4", "stall_freeze", "control_flow", "redirect",
                  "64-bit PC register initialized to 0x1000 advances by 4 per cycle redirects to branch_target on taken branch generates icache_addr"]},
    {"name": "fetch", "goal": "I-Cache request/response interface, instruction latch",
     "behavior_tags": ["instruction_fetch", "icache", "pipeline"],
     "keywords": ["fetch", "icache_req", "icache_addr", "instruction_latch", "cache_stall", "pipeline_flush", "pc_capture",
                  "I-Cache request on fetch slot empty latches 32-bit instruction from 64-bit cache line lower half captures PC"]},
    {"name": "decode", "goal": "Instruction decode + early branch comparison + 3-stage forwarding",
     "behavior_tags": ["instruction_decode", "branch", "forwarding", "early_branch"],
     "keywords": ["decode", "opcode", "immediate", "branch_compare", "branch_target", "early_branch", "redirect", "forwarding_mux",
                  "Decodes instruction fields generates 5 immediate types with sign extension performs early branch comparison BEQ BNE JAL JALR"]},
    {"name": "execute", "goal": "Dedicated ALU Mux chain for R/I-type/LUI/AUIPC/JAL operations",
     "behavior_tags": ["alu", "execute", "mux_chain"],
     "keywords": ["alu", "execute", "rtype", "itype", "mux_chain", "add_sub_xor_shift", "lui_auipc", "jal_jalr", "wb_en", "cache_addr",
                  "Dedicated ALU stage with cascaded Mux chain computes R-type I-type LUI AUIPC JAL JALR results from pipeline-captured ra rb"]},
    {"name": "memory", "goal": "D-Cache load/store with sign/zero extension for all widths",
     "behavior_tags": ["load_store", "memory", "dcache", "sign_extend"],
     "keywords": ["memory", "load_store", "dcache", "sign_extend", "zero_extend", "lb_lh_lw_ld", "memory_stage",
                  "Memory stage captures ALU result on D-Cache response sign zero extend LB LBU LH LHU LW LWU LD data width extension"]},
    {"name": "writeback", "goal": "Register file writeback with retire signal and forwarding",
     "behavior_tags": ["writeback", "regfile", "retire", "forwarding"],
     "keywords": ["writeback", "regfile", "retire_valid", "forwarding", "register_write", "wb_en", "status",
                  "Writeback stage captures result from memory writes to 32-entry 64-bit register file generates retire_valid provides forwarding data"]},
    {"name": "hazard", "goal": "I-Cache and D-Cache stall detection + pipeline freeze + branch flush",
     "behavior_tags": ["stall", "hazard", "pipeline_control"],
     "keywords": ["hazard", "stall", "icache_stall", "dcache_stall", "pipeline_freeze", "branch_flush", "valid_propagation",
                  "Detects I-Cache stall and D-Cache stall combines into core_stall_w to freeze all pipeline stages generates branch_redirect flush"]},
]

EFF_CORE_STEPS = [
    "1. 实现 3-stage pipeline 顶层（F/E/W 寄存器 + 控制逻辑）",
    "2. 实现 Fetch stage（PC 寄存器 + I-Cache 请求/响应接口）",
    "3. 实现 Execute stage（合并译码+执行：ALU Mux chain + 寄存器读）",
    "4. 实现 Writeback stage（结果写回寄存器文件）",
    "5. 实现 Stall 检测（ICache stall + DCache stall）",
    "6. 验证：对比 behavioral model 的指令吞吐率",
]

EFF_CORE_TASKS = [
    {"name": "pc_reg", "goal": "Program counter with branch redirect and stall freeze",
     "behavior_tags": ["program_counter", "branch_redirect", "icache_addr"],
     "keywords": ["pc_reg", "branch_target", "advance", "stall", "control_flow",
                  "PC register initialized to 0x1000 advances by 4 each cycle when not stalled redirects to branch_target on taken branch"]},
    {"name": "fetch", "goal": "I-Cache request/response interface and instruction latch",
     "behavior_tags": ["instruction_fetch", "icache", "pipeline"],
     "keywords": ["fetch", "icache_req", "icache_addr", "instruction_latch", "cache_stall",
                  "I-Cache request when fetch pipeline slot empty latches 32-bit instruction from lower half of 64-bit cache line on cache valid"]},
    {"name": "decode_alu", "goal": "Combined decode+execute with ALU Mux chain and branch compare",
     "behavior_tags": ["instruction_decode", "alu", "branch", "forwarding"],
     "keywords": ["decode", "opcode", "immediate", "alu", "mux_chain", "rtype", "itype", "branch_compare", "forwarding", "sign_extend",
                  "Combined decode+execute extracts opcode funct3 funct7 generates I S B U J immediates reads register file with WB forwarding computes ALU"]},
    {"name": "writeback", "goal": "Register file writeback with retire and forwarding",
     "behavior_tags": ["writeback", "regfile", "retire", "forwarding"],
     "keywords": ["writeback", "regfile", "retire_valid", "forwarding", "register_write", "wb_en",
                  "Writeback captures ALU result writes to 32-entry register file generates retire_valid provides forwarding data to decode stage"]},
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

L1_CACHE_TASKS = [
    {"name": "tag_ram", "goal": "Tag RAM with tag comparison and valid bit check",
     "behavior_tags": ["l1_cache_small", "l1_cache_big", "cache"],
     "keywords": ["tag", "ram", "tag_compare", "valid_check", "parallel_lookup",
                  "Tag RAM stores 51-bit tag per set dual-port tag comparison on both ways in parallel generates hit signal when tag matches and valid bit set"]},
    {"name": "data_ram", "goal": "Data storage array with way-select read",
     "behavior_tags": ["l1_cache_small", "l1_cache_big", "cache"],
     "keywords": ["data", "ram", "way_select", "data_read", "data_write",
                  "Dual-port data RAM stores 512-bit line per set per way read from matching way on hit write during refill to LRU-selected way"]},
    {"name": "lru", "goal": "LRU replacement with per-set toggle bit",
     "behavior_tags": ["l1_cache_small", "l1_cache_big", "cache"],
     "keywords": ["lru", "replace", "toggle_bit", "pseudo_lru", "way_select",
                  "Per-set LRU bit toggles on each refill for pseudo-LRU replacement selects way 0 or way 1 based on current LRU bit value"]},
    {"name": "msi_fsm", "goal": "MSI coherence state tracking with FSM",
     "behavior_tags": ["l1_cache_small", "l1_cache_big", "cache", "mesi"],
     "keywords": ["msi", "coherence", "fsm", "state_track", "invalid_shared_modified",
                  "4-state FSM IDLE CHECK REFILL PROBE tracks MSI state per cache line on probe invalidation clears valid bit on refill sets state to Shared"]},
]

COHERENCE_DIR_STEPS = [
    "1. 实现 directory entry（tag + state + sharers bitmask + owner）",
    "2. 实现 4-bit sharers 跟踪（per-core bitmask）",
    "3. 实现 Shared 请求处理（添加 sharer, M→S downgrade）",
    "4. 实现 Modified 请求处理（invalidate 当前 owner, 授予新 owner）",
    "5. 实现 invalidation 消息生成",
    "6. 实现 directory 查找（tag match + state decode）",
    "7. 验证：对比 behavioral model 的 coherence state 转换序列",
]

COHERENCE_DIR_TASKS = [
    {"name": "directory", "goal": "Directory entry with tag state sharers bitmask owner core_id",
     "behavior_tags": ["coherence_directory", "mesi", "directory"],
     "keywords": ["directory", "entry", "tag_match", "state_decode", "sharers_bitmask", "owner_tracking",
                  "64-entry direct-mapped directory with tag MSI state 4-bit sharers bitmask owner core_id tag comparison generates hit signal"]},
    {"name": "sharers", "goal": "4-bit sharers bitmask tracking and owner management",
     "behavior_tags": ["coherence_directory", "mesi", "sharers"],
     "keywords": ["sharers", "bitmask", "owner", "add_sharer", "invalidate_sharers",
                  "4-bit sharers bitmask per directory entry tracks which cores hold shared copy on read adds requester to sharers on write invalidates current sharers"]},
    {"name": "invalidation", "goal": "Probe target generation and invalidation message handling",
     "behavior_tags": ["coherence_directory", "mesi", "invalidation"],
     "keywords": ["invalidate", "probe", "snoop", "target_bitmask", "writeback",
                  "Generates probe_targets bitmask for snoop invalidation on exclusive write invalidates current owner grants modified state generates writeback_to_core for M to S downgrade"]},
]

NOC_ROUTER_STEPS = [
    "1. 实现 5-port router 顶层互连（E/W/N/S/J buffers + crossbar + XY routing）",
    "2. 实现 per-port NoCBuffer 实例化（FIFO + push/pop + empty/full）",
    "3. 实现 XY routing function（坐标比较 → 输出端口选择）",
    "4. 实现 crossbar（5 路输入的 5 路输出复用器）",
    "5. 实现 credit-based flow control（ready/valid handshake）",
    "6. 验证：对比 behavioral model 的 flit 转发路径和延迟",
]

NOC_ROUTER_TASKS = [
    {"name": "noc_buffer", "goal": "Depth-4 FIFO buffer with push/pop and full/empty detection",
     "behavior_tags": ["noc_buffer", "fifo", "noc_router"],
     "keywords": ["fifo", "buffer", "push_pop", "read_write_pointer", "count", "full_empty", "depth_4",
                  "Depth-4 FIFO with data array count read write pointers push when valid and not full pop when not empty generates full empty flags"]},
    {"name": "xy_routing", "goal": "Dimension-order XY routing from flit header coordinate comparison",
     "behavior_tags": ["xy_routing", "dimension_order", "routing", "noc_router"],
     "keywords": ["xy_routing", "dimension_order", "coordinate_compare", "port_selection", "east_west_north_south", "flit_header",
                  "Extracts dest_x and dest_y from flit header bits compares with current x_pos y_pos coordinates selects output port X-first then Y"]},
    {"name": "crossbar_arb", "goal": "Per-output fixed-priority arbiter with crossbar Mux",
     "behavior_tags": ["noc_router", "mesh", "crossbar", "arbitration"],
     "keywords": ["crossbar", "arbitration", "fixed_priority", "grant", "mux_select", "per_output", "independent",
                  "Per-output fixed-priority arbiter E greater than W greater than N greater than S greater than J each output independently grants to highest-priority requesting input"]},
    {"name": "flow_control", "goal": "Credit-based flow control with backpressure",
     "behavior_tags": ["noc_router", "mesh", "flow_control", "credit"],
     "keywords": ["credit", "flow_control", "ready_valid", "push_pop", "backpressure", "downstream_ready",
                  "Credit-based flow control input ready equals not full push when upstream valid and ready pop when input wins grant AND downstream ready_i"]},
]

MESH_TOP_STEPS = [
    "1. 实现 2×2 mesh NoCRouter 阵列实例化",
    "2. 实现 east-west 互连（相邻 router 对接）",
    "3. 实现 north-south 互连（相邻 router 对接）",
    "4. 实现边界 router 端口 tie-off",
    "5. 实现全局时钟/复位分发",
    "6. 验证：对比 behavioral model 的全 SoC 性能指标",
]

MESH_TOP_TASKS = [
    {"name": "mesh", "goal": "2x2 mesh NoC router array",
     "behavior_tags": ["mesh_noc"], "keywords": ["mesh", "top"]},
]


def register_hetero_skeleton_steps(template_steps: dict):
    """Register heterogeneous SoC skeleton steps into arch_skel._TEMPLATE_STEPS."""
    # Use TASKS (dict format) for skill-guided generation,
    # keep STEPS for human-readable AgentPackage implementation_steps
    template_steps["perf_core"] = PERF_CORE_TASKS
    template_steps["eff_core"] = EFF_CORE_TASKS
    template_steps["l1_cache"] = L1_CACHE_TASKS
    template_steps["coherence_dir"] = COHERENCE_DIR_TASKS
    template_steps["noc_router"] = NOC_ROUTER_TASKS
    template_steps["mesh_top"] = MESH_TOP_TASKS
