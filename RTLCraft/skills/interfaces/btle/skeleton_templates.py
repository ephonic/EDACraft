"""
skills.interfaces.btle.skeleton_templates — BTLE PE Type → Implementation Steps

PE type → implementation step mappings for BTLE PHY pipeline stages.
Used by ArchSkeletonGenerator when generating AgentPackage for BTLE PEs.
"""

CRC24_CORE_STEPS = [
    "1. 实现 CRC-24 LFSR 寄存器（24-bit, 复位加载 byte-swapped init 值）",
    "2. 实现 init 值 byte-swap：{init[7:0], init[15:8], init[23:16]}",
    "3. 实现 LFSR 反馈计算：new_bit = lfsr[23] ^ data_in",
    "4. 实现多项式 taps 更新：bit[0]=new_bit, bit[1]=lfsr[0]^new_bit, bit[2]=lfsr[1], "
    "bit[3]=lfsr[2]^new_bit, bit[4]=lfsr[3]^new_bit, bit[5]=lfsr[4], "
    "bit[6]=lfsr[5]^new_bit, bit[7]=lfsr[6], bit[8]=lfsr[7], "
    "bit[9]=lfsr[8]^new_bit, bit[10]=lfsr[9]^new_bit, bits[23:11]=lfsr[22:10]",
    "5. 实现 crc_state_init_bit_load 路径（重新加载 init 值）",
    "6. 实现 data_in_valid 门控 LFSR 更新",
    "7. 验证：对比 ble_crc24 golden reference 的 LFSR 序列",
]

SCRAMBLE_CORE_STEPS = [
    "1. 实现 7-bit LFSR 寄存器（多项式 x^7+x^4+1）",
    "2. 实现 channel_number 默认值处理（0 → 0x3F）",
    "3. 实现 LFSR 初始化：{1, channel_number[5:0]}",
    "4. 实现 channel_number_load 路径（重新初始化 LFSR）",
    "5. 实现 LFSR 移位：bit[0]←bit[6], bit[1]←bit[0], bit[2]←bit[1], "
    "bit[3]←bit[2], bit[4]←bit[3]^bit[6], bit[5]←bit[4], bit[6]←bit[5]",
    "6. 实现 data_out = lfsr[6] ^ data_in（在 data_in_valid 时更新）",
    "7. 实现 data_out_valid 延迟信号",
    "8. 验证：对比 ble_whiten golden reference 的加扰序列",
]

ACCESS_ADDRESS_DETECT_STEPS = [
    "1. 实现 32-bit 移位寄存器（bit_store, MSB 输入 phy_bit）",
    "2. 实现 bit_valid 延迟（bit_valid_d1）",
    "3. 实现默认 AA：0x123a5456（当 unique_bit_sequence 输入为 0）",
    "4. 实现 hit_flag：bit_store == unique_bit_sequence & bit_valid_d1",
    "5. 验证：输入标准 BLE AA (0x8E89BED6) 应正确检测",
]

GFSK_DEMOD_STEPS = [
    "1. 实现输入符号扩展（bit_width → 2*bit_width）",
    "2. 实现 I/Q 延迟链：i1←i_ext, i0←i1, q1←q_ext, q0←q1",
    "3. 实现 iq_valid 延迟链（3 级：iq_valid_d1/d2/d3）",
    "4. 实现判决指标计算：signal = i0*q1 - i1*q0",
    "5. 实现 phy_bit 决策：signal > 0",
    "6. 实现输出延迟对齐：signal_valid←iq_valid_d2, bit_valid←iq_valid_d3",
    "7. 验证：输入 I/Q 正弦波应产生正确的 bit 序列",
]

GAUSS_FILTER_STEPS = [
    "1. 实现 9 个可编程 tap 寄存器（tap0..tap8）",
    "2. 实现 tap_index 写入选择逻辑（switch-case 0..8）",
    "3. 实现 16-bit 移位寄存器（17-tap FIR 的输入历史）",
    "4. 实现 NRZ-to-bipolar 转换：bit ? +tap : -tap",
    "5. 实现 17-tap FIR 求和（tap9..tap16 镜像 tap7..tap0）",
    "6. 实现输出有效信号传递（bit_upsample_valid → gauss_valid）",
    "7. 验证：输入阶跃信号应产生高斯形状响应",
]

BIT_UPSAMPLER_STEPS = [
    "1. 实现 phy_bit 寄存器（bit_upsample_reg）",
    "2. 实现 bit_upsample_valid_internal 翻转逻辑（每周期翻转）",
    "3. 实现 bit_upsample_count 计数器（每两个周期递增）",
    "4. 实现 15 级 bit_valid 延迟链（valid/last 对齐）",
    "5. 实现 first_bit_valid 标记（初始化计数）",
    "6. 实现 bit_upsample_valid_last 输出（count==0 时触发）",
    "7. 验证：1M 输入应产生 8M 输出（每个 bit 重复 8 次）",
]

SDPRAM_STEPS = [
    "1. 实现存储器阵列（Memory data_width x (1<<addr_width)）",
    "2. 实现写端口：write_enable 时写入 write_address",
    "3. 实现读端口：读取 read_address → read_data_reg（1 周期延迟）",
    "4. 验证：读写同一地址应返回正确数据",
]

CRC_WRAPPER_STEPS = [
    "1. 实现 3 状态 FSM：IDLE → WORK_ON_INPUT → CRC_BIT_OUTPUT",
    "2. 实现 IDLE 状态：直接透传 info_bit，计数启动",
    "3. 实现 WORK_ON_INPUT 状态：透传数据，计数到位后切换到 CRC_OUTPUT",
    "4. 实现 CRC_BIT_OUTPUT 状态：每 16 周期输出 1 位 CRC（降频到 1M）",
    "5. 实现 CRC-24 LFSR 内联逻辑（跳过前 40 位）",
    "6. 实现 24 位 CRC 串行输出（MSB 先出）",
    "7. 验证：CRC 附加到 payload 后，接收端应校验通过",
]

SCRAMBLE_WRAPPER_STEPS = [
    "1. 实现 2 状态 FSM：IDLE → WORK_ON_INPUT",
    "2. 实现 data_in_count 计数器（跳过前 40 位 preamble+AA）",
    "3. 实现 data_in 1 周期延迟（对齐 scramble 输出）",
    "4. 实现 start_for_input（count>=40 时启用 scramble_core）",
    "5. 实现 start_for_output（count>=41 时 mux scramble 输出）",
    "6. 内联 scramble_core LFSR 逻辑",
    "7. 验证：加扰后数据应有接近 50% 的 0/1 比例",
]

VCO_STEPS = [
    "1. 实现相位累加器（integral_voltage_signal += voltage_signal）",
    "2. 实现两个 ROM 表（cos_table 和 sin_table，各 2^11 条目）",
    "3. 实现 ROM 读写接口（write_address/write_data 输入，read 输出）",
    "4. 实现 valid 延迟链（voltage_signal_valid → out_valid）",
    "5. 实现 sin_cos_out_valid_last 传递",
    "6. 验证：输入恒定电压应产生正弦波输出",
]

GFSK_MOD_STEPS = [
    "1. 实现三级流水线：bit_repeat_upsample → gauss_filter → vco",
    "2. 实现 bit_repeat_upsample 内联（1M→8M 采样）",
    "3. 实现 gauss_filter 内联（17-tap FIR, 可编程 tap 值）",
    "4. 实现 FIR 输出幅度缩放（右移 scale_shift 位）",
    "5. 实现 VCO 内联（相位累加器 + sin/cos ROM）",
    "6. 实现 ROM 读写接口（write 由外部更新 ROM 表）",
    "7. 验证：输入 bit 流应产生 GFSK 调制的 I/Q 信号",
]

BTLE_RX_CORE_STEPS = [
    "1. 实现 3 状态 FSM：IDLE → EXTRACT_LENGTH → CHECK_CRC",
    "2. 内联 GFSK demodulator（3-cycle 延迟，i0*q1-i1*q0）",
    "3. 内联 AA 检测器（32-bit 移位+匹配）",
    "4. 内联 descrambler（x^7+x^4+1 LFSR）",
    "5. 内联 CRC-24 计算器（跳过 AA 后的数据）",
    "6. 实现 octet 组装（LSB-first 串行→8-bit 并行）",
    "7. 实现 payload_length 提取（第 2 个 octet 的低 8 位）",
    "8. 实现 parity check 终止（CRC==0 时 crc_ok=1）",
    "9. 实现 decode_end 信号（所有 octet 接收完成）",
    "10. 验证：输入标准 BLE 帧应正确解码并校验 CRC",
]

BTLE_TX_STEPS = [
    "1. 实现 4 状态 FSM：IDLE → TX_PREAMBLE_ACCESS → TX_PDU → WAIT_LAST_SAMPLE",
    "2. 实现 preamble+AA 串行化（40-bit 移位寄存器，LSB 先出）",
    "3. 实现 PDU RAM 读取（dual-clock RAM: clkb 写, clk 读）",
    "4. 实现 PDU octet 串行化（每 octet 8 个周期，LSB 先出）",
    "5. 内联 CRC-24（跳过前 40 位，从 PDU 开始计算）",
    "6. 内联 scrambler（跳过前 40 位，从 PDU 开始加扰）",
    "7. 实现简化 GFSK 调制（bit → 直接 VCO，±100 偏移）",
    "8. 实现 VCO sin/cos ROM 查找和读写",
    "9. 实现 payload_length 动态提取（从 PDU 第 2 个 octet）",
    "10. 验证：TX 输出 I/Q 应与参考 RTL 的波形匹配",
]

BTLE_PHY_STEPS = [
    "1. 实现 TX 简化 FSM（IDLE → TX_PREAMBLE_ACCESS → TX_PDU → WAIT）",
    "2. 实现 RX 简化状态跟踪（hit_flag, decode_run, decode_end, crc_ok）",
    "3. 实现 TX/RX 信号接口映射",
    "4. 实现 TX I/Q 输出（preamble/AA 阶段：±50, PDU 阶段：简化映射）",
    "5. 实现 RX 状态输出（hit_flag, decode_end, crc_ok, payload_length）",
    "6. 实现 PDU 存储 RAM 接口（rx_pdu_octet_mem_data 输出）",
    "7. 验证：TX 输出帧可通过 RX 正确解码",
]


def register_btle_skeleton_steps(template_steps: dict):
    """Register BTLE skeleton steps into arch_skel._TEMPLATE_STEPS.

    Usage:
        from rtlgen import arch_skel
        from skills.interfaces.btle.skeleton_templates import register_btle_skeleton_steps
        register_btle_skeleton_steps(arch_skel._TEMPLATE_STEPS)
    """
    template_steps["crc24_core"] = CRC24_CORE_STEPS
    template_steps["scramble_core"] = SCRAMBLE_CORE_STEPS
    template_steps["access_address_detect"] = ACCESS_ADDRESS_DETECT_STEPS
    template_steps["gfsk_demod"] = GFSK_DEMOD_STEPS
    template_steps["gauss_filter"] = GAUSS_FILTER_STEPS
    template_steps["bit_upsampler"] = BIT_UPSAMPLER_STEPS
    template_steps["sdpram"] = SDPRAM_STEPS
    template_steps["crc_wrapper"] = CRC_WRAPPER_STEPS
    template_steps["scramble_wrapper"] = SCRAMBLE_WRAPPER_STEPS
    template_steps["vco"] = VCO_STEPS
    template_steps["gfsk_mod"] = GFSK_MOD_STEPS
    template_steps["btle_rx_core"] = BTLE_RX_CORE_STEPS
    template_steps["btle_tx"] = BTLE_TX_STEPS
    template_steps["btle_phy"] = BTLE_PHY_STEPS
