"""
skills.fft.skeleton_templates — FFT PE Type → Implementation Steps

PE type → implementation step mappings for all 7 FFT pipeline stages.
Used by ArchSkeletonGenerator when generating AgentPackage for FFT PEs.
"""

FFT_BUTTERFLY_STEPS = [
    "1. 实现复数加法：x0_re + x1_re, x0_im + x1_im",
    "2. 实现复数减法：x0_re - x1_re, x0_im - x1_im",
    "3. 实现算术右移缩放：y = (sum + RH) >>> 1",
    "4. 实现输出寄存器：y0_re/y0_im (和路), y1_re/y1_im (差路)",
    "5. 验证：对比 golden reference 模型的 butterfly 输出",
]

FFT_DELAY_BUFFER_STEPS = [
    "1. 实现深度为 2^k 的移位寄存器链（buf_re, buf_im）",
    "2. 每个时钟周期：所有寄存器右移一位，新数据从 [0] 进入",
    "3. 输出取自最后一个寄存器 buf[depth-1]",
    "4. 验证：输入脉冲序列，输出应延迟 depth 个周期",
]

FFT_MULTIPLY_STEPS = [
    "1. 实现 4 个有符号实数乘法：a_re*b_re, a_re*b_im, a_im*b_re, a_im*b_im",
    "2. 实现缩放：每个乘积右移 (width-1) 位",
    "3. 实现复数组合：m_re = arbr - aibi, m_im = arbi + aibr",
    "4. 实现饱和保护：结果饱和到 width 位有符号范围",
    "5. 验证：对比 golden reference 模型的复数乘法输出",
]

FFT_TWIDDLE_STEPS = [
    "1. 实现 ROM 表初始化：W_N^k = cos(-2*pi*k/N) + j*sin(-2*pi*k/N)",
    "2. 量化：浮点值乘以 2^(width-1) 并饱和到 width 位",
    "3. 实现地址解码：addr % N 索引查找",
    "4. 验证：ROM 表值应与 numpy.fft 参考 twiddle 因子匹配",
]

FFT_SDF_UNIT_STEPS = [
    "1. 实现 BF1 控制逻辑：bf1_bf 由 di_count[log_m-1] 决定",
    "2. 实现 DB1 延迟缓冲器：深度 2^(log_m-1)，移位寄存器",
    "3. 实现 BF1 蝶形运算：BF2 用 RH=1，BF1 用 RH=0",
    "4. 实现 BF1 单路输出：bf1_bf 时输出 y0，否则输出 DB1 尾部",
    "5. 实现 BF2 控制逻辑：bf2_bf 由 bf1_count[log_m-2] 决定",
    "6. 实现 DB2 延迟缓冲器：深度 2^(log_m-2)",
    "7. 实现 BF2 蝶形运算 + 单路输出",
    "8. 实现旋转因子乘法：tw_addr = bf2_count << (log_n - log_m) * 控制位",
    "9. 实现乘法使能：tw_addr == 0 时旁路乘法器",
    "10. 实现输出使能链：mu_do_en 延迟 bf2_do_en 一个周期",
    "11. 验证：对比 SdfUnit.v 参考 RTL 的周期级输出序列",
]

FFT_SDF_UNIT2_STEPS = [
    "1. 实现单个蝶形运算（无旋转因子乘法，M=2）",
    "2. 实现深度为 1 的延迟缓冲器",
    "3. 实现 bf_en 切换逻辑：每个有效输入翻转一次",
    "4. 实现单路输出：bf_en 时输出蝶形和路，否则输出 DB 尾部",
    "5. 实现 do_en 延迟链：bf_sp_en 延迟一个周期",
    "6. 验证：对比 SdfUnit2.v 参考 RTL 的周期级输出序列",
]

FFT_CONTROLLER_STEPS = [
    "1. 根据 log2(N) 计算需要的 SDF 级数：num_su = log_n // 2",
    "2. 如果 log_n 为奇数，末尾添加一个 SdfUnit2 级",
    "3. 实现级联数据流：上一级的 (do_en, do_re, do_im) 驱动下一级",
    "4. 实现各级独立控制状态（di_count, bf1_count, bf2_count 等）",
    "5. 验证：输入 N 点复数序列，输出应为 FFT(X) 的正确频谱",
]


def register_fft_skeleton_steps(template_steps: dict):
    """Register FFT skeleton steps into arch_skel._TEMPLATE_STEPS.

    Usage:
        from rtlgen import arch_skel
        from skills.fft.skeleton_templates import register_fft_skeleton_steps
        register_fft_skeleton_steps(arch_skel._TEMPLATE_STEPS)
    """
    template_steps["fft_butterfly"] = FFT_BUTTERFLY_STEPS
    template_steps["fft_delay_buffer"] = FFT_DELAY_BUFFER_STEPS
    template_steps["fft_multiply"] = FFT_MULTIPLY_STEPS
    template_steps["fft_twiddle"] = FFT_TWIDDLE_STEPS
    template_steps["fft_sdf_unit"] = FFT_SDF_UNIT_STEPS
    template_steps["fft_sdf_unit2"] = FFT_SDF_UNIT2_STEPS
    template_steps["fft_controller"] = FFT_CONTROLLER_STEPS
