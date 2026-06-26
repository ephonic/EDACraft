"""
skills.codec.video.skeleton_templates — Codec PE Type → Implementation Steps

PE type → implementation step mappings for xk265 H.265 encoder pipeline stages.
Used by ArchSkeletonGenerator when generating AgentPackage for codec PEs.

Covers 12 PE types: ENC_CTRL, PREI_TOP, POSI_TOP, IME_TOP, FME_TOP,
REC_TOP, DBSAO_TOP, CABAC_TOP, FETCH_TOP, TQ_TOP, INTRA_TOP, MC_TOP.
"""

ENC_CTRL_STEPS = [
    "1. 实现 CTU 光栅扫描计数器（ctu_x, ctu_y, sys_total_x_i, sys_total_y_i）",
    "2. 实现 10 状态 FSM：IDLE → PREI → POSI → IME → FME → REC → DB → CABAC → FETCH → DONE",
    "3. 实现 per-stage 启动信号生成（*_start_o = state == STAGE & ~*_done_i）",
    "4. 实现 CTU 推进逻辑：FETCH done → ctu_x++ 或 ctu_y++ 或 DONE",
    "5. 实现 RC QP 输出（初始 QP=22, 可配置）",
    "6. 实现 first_ctu 标记（用于 deblocking filter 边界跳过）",
    "7. 验证：对比 behavior model 的 CTU 序列和各阶段启动/完成时序",
]

PREI_TOP_STEPS = [
    "1. 实现 GxGy 梯度计算引擎（Sobel/Prewitt 算子，per-pixel 流水）",
    "2. 实现 counter 累积（64x64 区域梯度总和）",
    "3. 实现 mode decision 模块（基于梯度方向的最优 intra 模式预筛选）",
    "4. 实现 rate control：LCU 级 QP 调整（max_qp, min_qp, delta_qp）",
    "5. 实现 md_ram 读写接口（per-4x4 mode 写入）",
    "6. 实现 mode_write：将预筛选结果写入模式 RAM",
    "7. 验证：对比 behavior model 的梯度计算和 QP 调整序列",
]

POSI_TOP_STEPS = [
    "1. 实现 posi_ctrl FSM：TRA_PRE → TRA_POS → SIZE_4x4 → SIZE_8x8 → SIZE_16x16 → SIZE_32x32 → DECISION → DONE",
    "2. 实现 reference buffer：DC/Planar 参考像素加载",
    "3. 实现 prediction 引擎：35 种 intra 预测模式（DC, Planar, 角度模式）",
    "4. 实现 SATD cost 计算：Hadamard 变换 + 绝对值求和",
    "5. 实现 satd_cost_transpose：Hadamard 中间结果转置",
    "6. 实现 rate_estimation：lambda * bit_estimation 成本计算",
    "7. 实现 partition_decision：基于 SATD cost 的最优分区选择",
    "8. 实现 memory_wrapper：参考/模式数据的读写缓冲",
    "9. 验证：对比 behavior model 的 SATD cost 序列和分区决策",
]

IME_TOP_STEPS = [
    "1. 实现 ime_ctrl：ADR（寻址）→ DEC（分区决策）→ DMP（MV 导出）三阶段 FSM",
    "2. 实现 ime_addressing：搜索模式遍历（中心点 + 长度 + 斜率 + 降采样）",
    "3. 实现 ime_dat_array × 2：原始/参考像素 shift register 阵列（32x32 pixel buffer）",
    "4. 实现 ime_sad_array：多尺度 SAD 并行计算（64×4x4, 16×8x8, 4×16x16, 1×32x32）",
    "5. 实现 ime_cost_store：SAD + lambda*MVD 成本累加 + 最佳 MV 更新",
    "6. 实现 ime_partition_decision_engine：组合逻辑 1Nx1N vs 1Nx2N vs 2Nx1N vs 2Nx2N 比较",
    "7. 实现 ime_partition_decision：21 步迭代 CTU quad-tree 分区",
    "8. 实现 ime_mv_dump：串行输出最佳 MV 到输出 FIFO",
    "9. 验证：对比 behavior model 的 SAD 搜索和分区决策序列",
]

FME_TOP_STEPS = [
    "1. 实现 fme_ctrl：INTERP（插值）→ REFINE（精细搜索）→ DONE 三阶段 FSM",
    "2. 实现 1/4-pel 插值滤波器（6-tap HEVC 标准滤波器）",
    "3. 实现 fme_sad：插值位置的 SAD 计算",
    "4. 实现 fme_cost：SAD + lambda*MVD 成本",
    "5. 实现 fme_partition：基于精细 cost 的分区微调",
    "6. 实现 fme_mv_out：最终 MV 输出",
    "7. 验证：对比 behavior model 的插值和精化序列",
]

REC_TOP_STEPS = [
    "1. 实现 rec_ctrl：INTRA → MC → TQ → DONE 流水线 FSM",
    "2. 实现 intra_top：intra 预测像素生成（35 模式, DC/Planar/角度）",
    "3. 实现 mc_top：运动补偿（基于 FME MV 的像素插值）",
    "4. 实现 tq_top：正变换（DCT/DST）+ 量化 + 反变换 + 反量化",
    "5. 实现 rec_buf_wrapper：重建像素缓冲 + CBF 标志管理",
    "6. 实现 IinP 标志生成：intra/intra-prediction 模式标记",
    "7. 实现 cef/mvd 数据输出通道",
    "8. 验证：对比 behavior model 的重建像素和残差序列",
]

DBSAO_TOP_STEPS = [
    "1. 实现 dbsao_controller：LOAD → DBY → DBU → DBV → SAO → OUT FSM",
    "2. 实现 db_bs：边界强度（BS）计算，TU/PU 边缘检测，QP/CBF 标志提取",
    "3. 实现 db_filter：deblocking 滤波（强/弱滤波选择，HEVC 4x4 边缘滤波）",
    "4. 实现 sao_mode：SAO 模式决策（Edge Offset / Band Offset）",
    "5. 实现 sao_bo_predecision：Band Offset 预决策",
    "6. 实现 sao_data 输出（62-bit SAO 参数打包）",
    "7. 验证：对比 behavior model 的滤波和 SAO 序列",
]

CABAC_TOP_STEPS = [
    "1. 实现 cabac_ctrl：熵编码 FSM（binarization → context model → arithmetic encode）",
    "2. 实现 cabac_se_prepare：CU quad-tree 遍历，语法元素发射，LCU done 检测",
    "3. 实现 cabac_bina：语法元素二值化（TR, EGk, FL 等）",
    "4. 实现 cabac_bitpack：二进制打包成字节，emulation prevention 处理",
    "5. 实现 slice 结束检测（slice_done_o）",
    "6. 实现 IinP/MB 模式/Partition/CBF/MVD/coeff 等语法元素编码",
    "7. 验证：对比 behavior model 的 bitstream 输出",
]

FETCH_TOP_STEPS = [
    "1. 实现 fetch_ctrl：内存访问 FSM（当前帧/参考帧/重建帧）",
    "2. 实现 fetch_wrapper：顶层仲裁器和调度器",
    "3. 实现 fetch_cur_luma：当前帧 Y 分量像素读取（4-bank rotating buffer）",
    "4. 实现 fetch_ref_luma：参考帧 Y 分量像素读取（1024-entry buffer）",
    "5. 实现 fetch_db：deblocking 重建像素回写",
    "6. 实现 extif（外部接口）：AXI/DDR 请求打包",
    "7. 验证：对比 behavior model 的内存访问序列",
]

TQ_TOP_STEPS = [
    "1. 实现变换核心（DCT/DST, 4x4/8x8/16x16/32x32 尺寸）",
    "2. 实现量化（QP-dependent 量化矩阵）",
    "3. 实现反变换 + 反量化（重建残差生成）",
    "4. 实现 coefficient 数据输出（cef_wr）",
    "5. 验证：对比 behavior model 的变换/量化序列",
]

INTRA_TOP_STEPS = [
    "1. 实现 intra_ctrl：intra 预测状态机（256-cycle per-CTU 计数）",
    "2. 实现 mode RAM 读取（md_rd_ena/md_rd_adr）",
    "3. 实现 35 种 intra 预测模式像素生成（DC, Planar, 33 角度）",
    "4. 实现 reference pixel 管理和边界处理",
    "5. 验证：对比 behavior model 的 intra 预测像素序列",
]

MC_TOP_STEPS = [
    "1. 实现 mc_ctrl：运动补偿状态机（64-cycle per-CTU 计数）",
    "2. 实现 FME MV 读取接口（fmeif_mv_rden）",
    "3. 实现 reference 像素读取（fetchif_rden）",
    "4. 实现运动补偿插值像素写入 FME buffer（fme_wr_ena）",
    "5. 实现 MVD 写入（mvd_wen）和 prediction 使能（pre_en）",
    "6. 验证：对比 behavior model 的运动补偿像素序列",
]


def register_xk265_skeleton_steps(template_steps: dict):
    """Register xk265 skeleton steps into arch_skel._TEMPLATE_STEPS.

    Covers all 12 PE types used by the xk265 H.265 encoder.

    Usage:
        from rtlgen import arch_skel
        from skills.codec.video.skeleton_templates import register_xk265_skeleton_steps
        register_xk265_skeleton_steps(arch_skel._TEMPLATE_STEPS)
    """
    template_steps["fsm_controller"] = ENC_CTRL_STEPS
    template_steps["prei_processor"] = PREI_TOP_STEPS
    template_steps["posi_processor"] = POSI_TOP_STEPS
    template_steps["ime_processor"] = IME_TOP_STEPS
    template_steps["fme_processor"] = FME_TOP_STEPS
    template_steps["rec_processor"] = REC_TOP_STEPS
    template_steps["dbsao_processor"] = DBSAO_TOP_STEPS
    template_steps["cabac_processor"] = CABAC_TOP_STEPS
    template_steps["fetch_processor"] = FETCH_TOP_STEPS
    template_steps["tq_processor"] = TQ_TOP_STEPS
    template_steps["intra_processor"] = INTRA_TOP_STEPS
    template_steps["mc_processor"] = MC_TOP_STEPS


# Backward-compat alias (older code may use register_codec_skeleton_steps)
register_codec_skeleton_steps = register_xk265_skeleton_steps
