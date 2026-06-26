"""
skills.noc.skeleton_templates — NoC PE Type → Implementation Steps

PE type → implementation step mappings for mesh NoC router pipeline stages.
Used by ArchSkeletonGenerator when generating AgentPackage for NoC PEs.
"""

ROUTER_STEPS = [
    "1. 实现 5-port router 顶层互连（InputUnit × 5, OutputUnit × 5, CrossBar, VC_Alloc）",
    "2. 实现 per-port InputUnit 实例化（Buffer + Route_Func + 7-state FSM）",
    "3. 实现 per-port OutputUnit 实例化（write_req 生成逻辑）",
    "4. 实现 5×5 CrossBar 数据通路（5 路输入的 5 路输出复用器）",
    "5. 实现 VC_Alloc 模块（5 路 round-robin 仲裁器）",
    "6. 实现 Select_gen + set_Alloc + ST_Controler + ST 控制链",
    "7. 实现 out_en_gen（crossbar select → output enable 映射）",
    "8. 实现 credit-based flow control（em_pl 空位跟踪）",
    "9. 验证：对比 behavioral model 的 per-port FSM 状态序列和 flit 转发路径",
]

INPUT_UNIT_STEPS = [
    "1. 实现 Buffer 实例（4-depth FIFO, push/pop/empty_slots 控制）",
    "2. 实现 Route_Func（XY routing: 坐标比较 → 5-bit valid_out + status）",
    "3. 实现 7-state FSM（IDLE → ST_wait → ST[0-3] → CLEANUP → IDLE）",
    "4. 实现 per-state 控制信号生成（vc_f, push_o, pop）",
    "5. 实现 push_ack 逻辑（SINGLE/BODY/TAIL flit 类型的不同 push 策略）",
    "6. 实现 enable 信号生成（flit header 解析，dest_X/dest_Y 提取）",
    "7. 实现 out_num + PW 优先级输出端口选择（多目标端口仲裁）",
    "8. 验证：对比 behavioral model 的 FSM 状态转换和输出端口选择序列",
]

OUTPUT_UNIT_STEPS = [
    "1. 实现输出 buffer 状态跟踪",
    "2. 实现 write_req 生成（基于下一跳 buffer 占用状态）",
    "3. 实现 credit 回传（em_pl 更新）",
    "4. 验证：对比 behavioral model 的 write_req 时序",
]

VC_ALLOC_STEPS = [
    "1. 实现 5 个 round-robin counter（c_e/c_w/c_n/c_s/c_j, mod-5 计数）",
    "2. 实现 per-output-port 请求收集（5 路输入请求）",
    "3. 实现 round-robin 仲裁逻辑（counter 起始遍历，选择首个请求者）",
    "4. 实现 grant 信号输出（grant_e/grant_w/grant_n/grant_s/grant_j）",
    "5. 实现 counter 更新（grant 后 counter = winner + 1）",
    "6. 验证：对比 behavioral model 的 round-robin 仲裁序列",
]

CROSSBAR_STEPS = [
    "1. 实现 5 路输入寄存（IE/IW/IN/IS/Inject, 64-bit）",
    "2. 实现 5 个 5:1 多路复用器（S_E/S_W/S_N/S_S/S_ejec 选择信号）",
    "3. 实现输出寄存器（OE/OW/ON/OS/Eject）",
    "4. 实现默认值输出（select == 7 → 0）",
    "5. 验证：对比 behavioral model 的 crossbar 数据通路",
]

ROUTE_FUNC_STEPS = [
    "1. 实现坐标比较逻辑（X_cur vs X_dest, Y_cur vs Y_dest）",
    "2. 实现 5-bit valid_out 生成（E/W/N/S/Eject 单热码）",
    "3. 实现 status 信号（多目标端口标记）",
    "4. 实现 XY routing 方向优先级（X 方向优先于 Y 方向）",
    "5. 验证：对比 behavioral model 的路由决策序列",
]

BUFFER_STEPS = [
    "1. 实现 4-depth 寄存器堆（64-bit × 4）",
    "2. 实现 head/tail 指针（3-bit, mod-4 循环）",
    "3. 实现 push/pop 控制（条件更新指针和计数）",
    "4. 实现 empty_slots 输出（3-bit: depth - count）",
    "5. 验证：对比 behavioral model 的 buffer 填充/排空序列",
]

PACKET_GEN_STEPS = [
    "1. 实现 8-state FSM（INIT → GAP → WAIT → HEAD → BODY → TAIL → CLEANUP → DONE）",
    "2. 实现 inter-packet gap counter（9 周期间隔）",
    "3. 实现 HEAD flit 生成（dest != src 随机选择, flit header 组装）",
    "4. 实现 BODY/TAIL flit 生成（payload + flit type 编码）",
    "5. 实现 Flit_ID 跟踪（{packet_count, node_id}）",
    "6. 实现 write_req + write_req_ack handshake",
    "7. 验证：对比 behavioral model 的 flit 序列和 dest 分布",
]

PACKET_REC_STEPS = [
    "1. 实现 eject 端口 flit 接收",
    "2. 实现 flit type 解析（HEAD/BODY/TAIL/SINGLE）",
    "3. 实现 packet 计数器（TAIL/SINGLE → packet++）",
    "4. 实现 flit 计数器（per-flit 递增）",
    "5. 验证：对比 behavioral model 的 packet 接收统计",
]

ST_CONTROLER_STEPS = [
    "1. 实现 VC grant → ST request 映射（per-port grant → 对应 output ST_req）",
    "2. 实现 5 路 ST request 输出（e/w/n/s/eject_st_req）",
    "3. 实现 output enable + select match → ack 生成",
    "4. 实现 5 路 ack 输出（e/w/n/s/inject_ack）",
    "5. 验证：对比 behavioral model 的 ST handshake 序列",
]

SELECT_GEN_STEPS = [
    "1. 实现 5 路 grant 检测（e_g/w_g/n_g/s_g/inject_g）",
    "2. 实现 grant → select 映射（per-port req → 对应 crossbar select）",
    "3. 实现 5 路 3-bit select 输出（s_e/s_w/s_n/s_s/s_eject）",
    "4. 实现默认值（reset → select = 7）",
    "5. 验证：对比 behavioral model 的 crossbar select 序列",
]

SET_ALLOC_STEPS = [
    "1. 实现 5 路 VC grant 检测（e_vc_grant/w_vc_grant/...）",
    "2. 实现 grant + req → output port alloc 映射",
    "3. 实现 5 路 alloc 输出（alloc_e/alloc_w/alloc_n/alloc_s/alloc_j）",
    "4. 验证：对比 behavioral model 的 alloc 信号序列",
]

OUT_EN_GEN_STEPS = [
    "1. 实现 5 路 push_o 检测（e_push_o/w_push_o/...）",
    "2. 实现 push + select match → output enable 映射",
    "3. 实现 5 路 enable 输出（e_en/w_en/n_en/s_en/eject_en）",
    "4. 验证：对比 behavioral model 的 output enable 序列",
]

NETWORK_STEPS = [
    "1. 实现 MESH_SIZE × MESH_SIZE Process_Node 阵列实例化",
    "2. 实现 east/west/north/south link 互连（相邻 router 端口对接）",
    "3. 实现 per-node packet generator 和 receiver",
    "4. 实现网络级统计（total_injected, total_received, avg_latency）",
    "5. 实现边界节点处理（边缘 router 无对应方向连接）",
    "6. 验证：对比 behavioral model 的网络流量统计和延迟分布",
]


def register_noc_skeleton_steps(template_steps: dict):
    """Register NoC skeleton steps into arch_skel._TEMPLATE_STEPS.

    Usage:
        from rtlgen import arch_skel
        from skills.noc.skeleton_templates import register_noc_skeleton_steps
        register_noc_skeleton_steps(arch_skel._TEMPLATE_STEPS)
    """
    template_steps["router"] = ROUTER_STEPS
    template_steps["input_unit"] = INPUT_UNIT_STEPS
    template_steps["output_unit"] = OUTPUT_UNIT_STEPS
    template_steps["vc_alloc"] = VC_ALLOC_STEPS
    template_steps["crossbar"] = CROSSBAR_STEPS
    template_steps["route_func"] = ROUTE_FUNC_STEPS
    template_steps["buffer"] = BUFFER_STEPS
    template_steps["packet_gen"] = PACKET_GEN_STEPS
    template_steps["packet_rec"] = PACKET_REC_STEPS
    template_steps["st_controler"] = ST_CONTROLER_STEPS
    template_steps["select_gen"] = SELECT_GEN_STEPS
    template_steps["set_alloc"] = SET_ALLOC_STEPS
    template_steps["out_en_gen"] = OUT_EN_GEN_STEPS
    template_steps["network"] = NETWORK_STEPS
