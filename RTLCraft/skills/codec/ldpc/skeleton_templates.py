"""
skills.codec.ldpc.skeleton_templates — LDPC PE Type → Implementation Steps

PE type → implementation step mappings for LDPC Min-Sum decoder.
Used by ArchSkeletonGenerator when generating AgentPackage for LDPC PEs.
"""

QUANTIZED_ADDER_STEPS = [
    "1. 实现 (prec+1)-bit 内部加法器（sum_wire = in1 + in2）",
    "2. 实现溢出检测：sum_wire[prec] == sum_wire[prec-1] 表示无溢出",
    "3. 实现无溢出路径：直接截取 sum_wire[prec-1:0]",
    "4. 实现溢出饱和路径：符号位扩展（Cat(sum_wire[prec], Rep(sum_wire[prec-1], prec-1))）",
    "5. 验证：边界值测试（pmax+pmax, pmin+pmin, pmax+1）",
]

QUANTIZED_SUBBER_STEPS = [
    "1. 实现 (prec+1)-bit 内部减法器（sum_wire = in1 - in2）",
    "2. 实现溢出检测：与加法器相同的逻辑",
    "3. 实现无溢出路径：直接截取 sum_wire[prec-1:0]",
    "4. 实现溢出饱和路径：符号位扩展",
    "5. 验证：边界值测试（pmax-pmin, pmin-pmax）",
]

COMPARATOR_STEPS = [
    "1. 实现 min 选择：if (min2 > min1) min=min1, else min=min2",
    "2. 实现 not_min 中间信号（较大的那个 min 输入）",
    "3. 实现 not_max 选择：min(sec_min1, sec_min2)",
    "4. 实现 sec_min 选择：min(not_min, not_max)",
    "5. 验证：4 个输入的不同排列组合下 min/sec_min 正确性",
]

CHECK_NODE_STEPS = [
    "1. 实现 Q 值提取和符号/绝对值分离（per-edge: Qsign, abs_Q）",
    "2. 实现 sign_product XOR 树（所有 Qsign 的异或）",
    "3. 实现 comparator tree 叶子节点初始化（abs_Q 和全 1 填充）",
    "4. 实例化 Comparator 模块树（num_connections-1 个比较器）",
    "5. 实现 R 符号计算：Rsign = sign_product XOR Qsign",
    "6. 实现 R 绝对值选择：if (abs_Q == min) second_min else min",
    "7. 实现 R 符号恢复：if Rsign then -abs_R else abs_R",
    "8. 实现 Rreg 寄存器组（posedge clk, posedge rst 异步复位）",
    "9. 实现 Rwires 输出打包（从 Rreg 拼接）",
    "10. 验证：对比 golden reference 的 Min-Sum 更新",
]

VAR_NODE_STEPS = [
    "1. 实现 R 值提取（从 Rwires 按 prec 位切片）",
    "2. 实现 saturating adder tree（QuantizedAdder 实例化，求 sum_R）",
    "3. 实现 P_v 计算：QuantizedAdder(sum_R, llr)",
    "4. 实现硬判决输出：x = P_v[prec-1]",
    "5. 实例化 QuantizedSubber 阵列（per-edge: Q_i = P_v - R_i）",
    "6. 实现 Qwires 输出打包（从 sub_wires 拼接）",
    "7. 实现 Qreg 寄存器（捕获 Qwires，1-cycle 延迟）",
    "8. 验证：对比 golden reference 的 P_v 和 Q 值",
]

LDPC_DECODER_STEPS = [
    "1. 实现 LLR 输入解包（per-VN: llr[prec-1:0] 切片）",
    "2. 实现 VN↔CN 互连（per-edge: Qwires/Rwires 交叉连接）",
    "3. 实例化 VarNode 阵列（per-VN，degree 参数化）",
    "4. 实例化 CheckNode 阵列（per-CN，degree 参数化）",
    "5. 实现 parity check 逻辑（per-CN: XOR of connected x bits）",
    "6. 实现迭代计数器（count, 5-bit, 上限 25）",
    "7. 实现 done 逻辑：(count == 25) || (out_check == 0)",
    "8. 实现 done_reg 寄存器（异步复位，保持 done 状态）",
    "9. 实现 P_v/x 输出打包",
    "10. 验证：对比 minsum_decode golden reference 的收敛行为",
]


def register_ldpc_skeleton_steps(template_steps: dict):
    """Register LDPC skeleton steps into arch_skel._TEMPLATE_STEPS.

    Usage:
        from rtlgen import arch_skel
        from skills.codec.ldpc.skeleton_templates import register_ldpc_skeleton_steps
        register_ldpc_skeleton_steps(arch_skel._TEMPLATE_STEPS)
    """
    template_steps["quantized_adder"] = QUANTIZED_ADDER_STEPS
    template_steps["quantized_subber"] = QUANTIZED_SUBBER_STEPS
    template_steps["comparator"] = COMPARATOR_STEPS
    template_steps["check_node"] = CHECK_NODE_STEPS
    template_steps["var_node"] = VAR_NODE_STEPS
    template_steps["ldpc_decoder"] = LDPC_DECODER_STEPS
