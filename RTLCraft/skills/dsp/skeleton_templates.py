"""
skills.dsp.skeleton_templates — DSP PE Type → Implementation Steps

PE type → implementation step mappings for all 12 DSP pipeline stages.
Used by ArchSkeletonGenerator when generating AgentPackage for DSP PEs.
"""

DSP_MULT_STEPS = [
    "1. 实现 4 级流水线寄存器：input_a_reg_0/1, input_b_reg_0/1, output_reg_0/1",
    "2. 实现 AXI-Stream 握手：input_a_tready = input_b_tvalid & output_tready",
    "3. 实现 AXI-Stream 握手：input_b_tready = input_a_tvalid & output_tready",
    "4. 实现 transfer 条件：input_a_tvalid & input_b_tvalid & output_tready",
    "5. 实现流水线推进：stage0←input, stage1←stage0, mul←stage1, stage0_out←mul, stage1_out←stage0_out",
    "6. 实现有符号乘法：$signed(input_a_reg_1) * $signed(input_b_reg_1)",
    "7. 验证：对比 golden reference 模型的 4 级流水线输出序列",
]

IQ_JOIN_STEPS = [
    "1. 实现 I/Q 独立数据缓冲寄存器（i_data_reg, q_data_reg）",
    "2. 实现 I/Q 独立有效标志（i_valid_reg, q_valid_reg）",
    "3. 实现 input_i_tready：~i_valid_reg | (output_tready & output_tvalid)",
    "4. 实现 input_q_tready：~q_valid_reg | (output_tready & output_tvalid)",
    "5. 实现 output_tvalid = i_valid_reg & q_valid_reg（两路均有效时才输出）",
    "6. 实现 I/Q 独立写入和清除逻辑",
    "7. 验证：I/Q 异步输入时，输出仅在两者均到达时有效",
]

IQ_SPLIT_STEPS = [
    "1. 实现 I/Q 独立输出缓冲寄存器（i_data_reg, q_data_reg）",
    "2. 实现 I/Q 独立有效标志（i_valid_reg, q_valid_reg）",
    "3. 实现 input_tready：(～i_valid_reg | 消费I) & (～q_valid_reg | 消费Q)",
    "4. 实现独立输出通道：output_i_tvalid = i_valid_reg, output_q_tvalid = q_valid_reg",
    "5. 实现 I 通道消费：output_i_tready & output_i_tvalid → i_valid_reg←0",
    "6. 实现 Q 通道消费：output_q_tready & output_q_tvalid → q_valid_reg←0",
    "7. 验证：输出可独立被下游消费，不互相阻塞",
]

I2S_CTRL_STEPS = [
    "1. 实现 prescale_cnt 递减计数器（分频器）",
    "2. 实现 prescale_cnt 重载：计数到 0 时加载 prescale 值",
    "3. 实现 sck_reg 翻转：每次 prescale_cnt 到 0 时切换 0↔1",
    "4. 实现 ws_cnt 字选择计数器（每 WIDTH 个 sck 周期递减）",
    "5. 实现 ws_reg 翻转：ws_cnt 到 0 且 sck 变低时切换",
    "6. 验证：prescale=N 时 sck 频率 = sys_clk/(2*(N+1))",
]

PHASE_ACCUMULATOR_STEPS = [
    "1. 实现相位累加寄存器 phase_reg（WIDTH 位，初始化 INITIAL_PHASE）",
    "2. 实现相位步长寄存器 phase_step_reg（初始化 INITIAL_PHASE_STEP）",
    "3. 实现 AXI 握手：input_phase_tready = output_phase_tready",
    "4. 实现 input_phase_step_tready 固定为 1",
    "5. 实现 output_phase_tvalid 固定为 1",
    "6. 实现相位更新：握手时加载新值，否则自增 phase_step_reg",
    "7. 实现相位步长更新：input_phase_step_tvalid 时更新",
    "8. 验证：恒定步长应产生线性相位斜坡（自由运行 NCO）",
]

DSP_IQ_MULT_STEPS = [
    "1. 实现 4 级流水线寄存器：A_I/Q reg_0/1, B_I/Q reg_0/1, out_I/Q reg_0/1",
    "2. 实现 AXI-Stream 握手（同 dsp_mult，双输入 + output_tready）",
    "3. 实现 transfer 条件：input_a_tvalid & input_b_tvalid & output_tready",
    "4. 实现 I 通道乘法：$signed(input_a_i_reg_1) * $signed(input_b_i_reg_1)",
    "5. 实现 Q 通道乘法：$signed(input_a_q_reg_1) * $signed(input_b_q_reg_1)",
    "6. 流水线映射到 Xilinx DSP slice（reg→pipe→mul→pipe）",
    "7. 验证：对比 golden reference 模型的 4 级流水线 I/Q 输出",
]

I2S_RX_STEPS = [
    "1. 实现 sck 边沿检测：last_sck 延迟，检测 ~last_sck & sck（上升沿）",
    "2. 实现 ws 延迟链：last_ws ← ws, last_ws2 ← last_ws",
    "3. 实现 ws 跳变检测：last_ws2 != last_ws → 重置 bit_cnt = WIDTH-1",
    "4. 实现 MSB-first 移位寄存器：sreg ← {sreg[WIDTH-2:0], sd}",
    "5. 实现 bit_cnt 递减，最后 1 位时加载到 l_data_reg 或 r_data_reg",
    "6. 实现左右声道区分：last_ws2==1 → 右声道，last_ws2==0 → 左声道",
    "7. 实现 output_tvalid = l_data_valid_reg & r_data_valid_reg",
    "8. 验证：输入标准 I2S 串行流应正确恢复左右声道并行数据",
]

I2S_TX_STEPS = [
    "1. 实现 input_tready = ~l_data_valid_reg & ~r_data_valid_reg",
    "2. 实现 sck 上升沿检测：加载新字到 sreg，清除对应 valid 标志",
    "3. 实现 sck 下降沿检测：MSB-first 移位输出到 sd_reg",
    "4. 实现 ws 跳变检测：根据 ws 值选择左声道或右声道数据",
    "5. 实现 bit_cnt 计数器（WIDTH 位递减）",
    "6. 实现 {sd_reg, sreg} ≤ {sreg[WIDTH-1:0], 1'b0} 移位操作",
    "7. 验证：输入左右声道并行数据应产生正确 I2S 串行输出",
]

SINE_DDS_LUT_STEPS = [
    "1. 实现相位字段提取：SIGN=phase[INPUT_WIDTH-1], A=phase[INPUT_WIDTH-2:W], B=phase[W-1:0]",
    "2. 实现三个 ROM 表：coarse_c_lut(2^(W+1) 项), coarse_s_lut(2^(W+1) 项), fine_s_lut(2^W 项)",
    "3. 实现 5 级流水线：LUT读→管道→乘法→加减→符号修正",
    "4. 实现角度加法恒等式：sin(A+B)=sin(A)+cos(A)*sin(B), cos(A+B)=cos(A)-sin(A)*sin(B)",
    "5. 实现乘积右移归一化：cp_reg >> (OUTPUT_WIDTH-1)",
    "6. 实现符号修正：SIGN=1 时取反输出",
    "7. 验证：输出正弦波应与 math.sin/cos 参考值匹配（误差 ≤ 1 LSB）",
]

SINE_DDS_STEPS = [
    "1. 实现相位累加器（同 phase_accumulator：phase_reg + phase_step_reg）",
    "2. 实现相位到 LUT 的位提取：phase[PHASE_WIDTH-1:PHASE_WIDTH-OUTPUT_WIDTH-2]",
    "3. 内联 sine_dds_lut 的 5 级流水线逻辑",
    "4. 实现三个 ROM 表初始化（与 sine_dds_lut 相同）",
    "5. 实现角度加法恒等式计算（同 sine_dds_lut）",
    "6. 验证：恒定相位步长应产生连续正弦波",
]

CIC_DECIMATOR_STEPS = [
    "1. 实现 N 个积分器级联：int_reg[k] ← int_reg[k] + (k==0 ? input : int_reg[k-1])",
    "2. 实现可编程分频器：cycle_reg 计数器（0 到 min(RMAX-1, rate-1)）",
    "3. 实现 N 个梳状器级联：comb_reg[k] ← src - delay_reg[k][M-1]",
    "4. 实现 M 级延迟线（per comb stage）：delay_reg 移位链",
    "5. 实现积分器更新条件：input_tready & input_tvalid",
    "6. 实现梳状器更新条件：output_tready & output_tvalid",
    "7. 实现 input_tready = output_tready | (cycle_reg != 0)",
    "8. 实现 output_tvalid = input_tvalid & (cycle_reg == 0)",
    "9. 验证：输入阶跃信号，输出应每 R 个周期产生一次有效值",
]

CIC_INTERPOLATOR_STEPS = [
    "1. 实现 N 个梳状器级联：comb_reg[k] ← src - delay_reg[k][M-1]（输入采样率）",
    "2. 实现可编程上转换器：cycle_reg 计数器（0 到 min(RMAX-1, rate-1)）",
    "3. 实现 N 个积分器级联：int_reg[k] ← int_reg[k] + (k==0 ? comb_reg[N-1] : int_reg[k-1])",
    "4. 实现 M 级延迟线（per comb stage）：delay_reg 移位链",
    "5. 实现梳状器更新条件：input_tready & input_tvalid（仅在 cycle_reg==0 时）",
    "6. 实现积分器更新条件：output_tready & output_tvalid（每个周期）",
    "7. 实现 input_tready = output_tready & (cycle_reg == 0)",
    "8. 实现 output_tvalid = input_tvalid | (cycle_reg != 0)",
    "9. 验证：输入单一样本，输出应产生 R 个插值样本",
]


def register_dsp_skeleton_steps(template_steps: dict):
    """Register DSP skeleton steps into arch_skel._TEMPLATE_STEPS.

    Usage:
        from rtlgen import arch_skel
        from skills.dsp.skeleton_templates import register_dsp_skeleton_steps
        register_dsp_skeleton_steps(arch_skel._TEMPLATE_STEPS)
    """
    template_steps["dsp_mult"] = DSP_MULT_STEPS
    template_steps["iq_join"] = IQ_JOIN_STEPS
    template_steps["iq_split"] = IQ_SPLIT_STEPS
    template_steps["i2s_ctrl"] = I2S_CTRL_STEPS
    template_steps["phase_accumulator"] = PHASE_ACCUMULATOR_STEPS
    template_steps["dsp_iq_mult"] = DSP_IQ_MULT_STEPS
    template_steps["i2s_rx"] = I2S_RX_STEPS
    template_steps["i2s_tx"] = I2S_TX_STEPS
    template_steps["sine_dds_lut"] = SINE_DDS_LUT_STEPS
    template_steps["sine_dds"] = SINE_DDS_STEPS
    template_steps["cic_decimator"] = CIC_DECIMATOR_STEPS
    template_steps["cic_interpolator"] = CIC_INTERPOLATOR_STEPS
