"""
skills.image.isp.skeleton_templates — DSL Skeleton Steps for ISP Pipeline

Maps PE types to implementation step lists for the ArchSkeletonGenerator.
Registered at import time via register_isp_skeleton_steps().
"""
from __future__ import annotations

from typing import Dict, List

from rtlgen.arch_skel import _TEMPLATE_STEPS


_ISP_SKELETON_STEPS: Dict[str, List[str]] = {
    "isp_axi_in": [
        "1. 实现 AXI-Stream slave 接口：s_axis_tvalid/s_axis_tready 握手协议",
        "2. 实现 2 级流水线 FIFO（valid0/valid1）：tvalid & tready 时加载 tdata，延迟两拍输出",
        "3. 实现 pix_sof/pix_eol 映射：tuser → sof0，tlast → eol0，随流水线传递",
        "4. 实现 tready 反压：valid1 为高时拉低 tready，阻止上游输入",
        "5. 验证：AXI-Stream 输入 → pix_valid/pix_data/pix_sof/pix_eol 延迟两拍正确输出",
    ],
    "isp_crop": [
        "1. 实现 x/y 计数器：pix_valid 递增，pix_eol 时 x 归零 y 递增，pix_sof 时 y 归零",
        "2. 实现区域门控：x_cnt ∈ [start_x, start_x+width) 且 y_cnt ∈ [start_y, start_y+height) 时输出",
        "3. 实现 enable 控制：cfg_enable=0 时直通，=1 时执行裁剪",
        "4. 实现 pix_sof/pix_eol 透传：仅在区域内有效时传递",
        "5. 验证：配置裁剪区域后输出像素数 = width × height，区域外像素被丢弃",
    ],
    "isp_dpc": [
        "1. 实现 5×5 窗口缓存：4 级 line buffer + center_buf，构建 8 方向 footprint",
        "2. 实现死像素检测：center < min(footprint) 或 center > max(footprint) 且 8 方向差值均超 threshold",
        "3. 实现 4 方向梯度计算：V/H/LD/RD 梯度 = |2*center - 对向两像素和|",
        "4. 实现最小梯度方向均值校正：取 min(gv,gh,gld,grd) 对应方向的均值作为修正值",
        "5. 实现 pipeline 延迟匹配：out_valid 比 pix_valid 延迟一拍",
        "6. 验证：注入死像素（全黑/全白），输出被正确修正为邻域均值",
    ],
    "isp_blc": [
        "1. 实现 row/col 奇偶计数器：pix_eol 翻转 row，pix_valid 翻转 col",
        "2. 实现 Bayer 通道识别：根据 cfg_bayer (RGGB/BGGR/GRBG/GBRG) + row/col 选择 R/Gr/Gb/B 通道",
        "3. 实现 per-channel offset 减法：pix_data - offset，裁剪到 [0, pixel_max]",
        "4. 实现 enable 控制：关闭时直通输入",
        "5. 验证：不同 Bayer 模式下各通道 offset 正确应用，无溢出",
    ],
    "isp_oecf": [
        "1. 实现 256-entry LUT：以 pix_data 高 8 位为索引查表",
        "2. 实现 LUT 可编程：通过 APB 寄存器加载 oecf_lut_0 ~ oecf_lut_255",
        "3. 实现 enable 控制：关闭时直通输入",
        "4. 验证：LUT 加载 gamma 曲线后输出符合 opto-electronic 映射",
    ],
    "isp_dg": [
        "1. 实现 Q4.8 定点乘法：pix_data * cfg_gain，右移 8 位",
        "2. 实现饱和裁剪：结果限制在 [0, pixel_max]",
        "3. 实现 AE 反馈增益自动调整：根据 AE 统计动态更新 cfg_gain",
        "4. 验证：gain=256 (1.0x) 直通，gain=512 (2.0x) 正确放大并饱和",
    ],
    "isp_lsc": [
        "1. 实现 row/col 奇偶计数器跟踪 Bayer 位置",
        "2. 实现 per-channel Q4.4 增益选择：根据 Bayer 模式 + row/col 选择 R/Gr/Gb/B 增益",
        "3. 实现径向增益乘法：pix_data * gain_sel >> 4，裁剪到 [0, pixel_max]",
        "4. 实现 enable 控制：关闭时直通",
        "5. 验证：边缘像素增益 > 1.0 时正确增亮，中心增益 = 1.0 时不变",
    ],
    "isp_bnr": [
        "1. 实现 5×5 Joint Bilateral Filter 窗口：4 级 line buffer + center_buf",
        "2. 实现空间高斯权重：[1,4,7,4,1; 4,16,26,16,7; ...] 中心权重 41",
        "3. 实现 range kernel：diff = |center - neighbor|，range_w = max(0, 16 - (diff >> 4))",
        "4. 实现 Green Guiding：仅同色像素参与加权平均",
        "5. 实现加权归一化：result = weighted_sum / weight_total，裁剪到 [0, pixel_max]",
        "6. 验证：高噪声输入经 BNR 后噪声降低，边缘保留",
    ],
    "isp_wb": [
        "1. 实现 row/col 奇偶计数器 + Bayer 模式识别 R/G/B 通道",
        "2. 实现 per-channel Q4.8 增益：R/G/B 三路独立增益乘法",
        "3. 实现饱和裁剪：结果限制在 [0, pixel_max]",
        "4. 实现 AWB 增益反馈：从 AWBStats 模块接收计算的 R/G/B 增益",
        "5. 验证：R_gain=512 (2.0x) 时红色通道正确增亮，G/B 不变",
    ],
    "isp_awb_stats": [
        "1. 实现 RGB 三通道累加器：r_acc/g_acc/b_acc 逐像素累加",
        "2. 实现 SOF 复位：pix_sof 时清零所有累加器和计数器",
        "3. 实现像素计数器：统计有效像素总数 cnt",
        "4. 实现输出接口：stat_r_sum/stat_g_sum/stat_b_sum/stat_pix_count/stat_done",
        "5. 验证：输入均匀灰度图后 R/G/B sum 相等，cnt = width × height",
    ],
    "isp_demosaic": [
        "1. 实现 5×5 Bayer 窗口缓存：4 级 line buffer + center_buf",
        "2. 实现 G 插值（R/B 位置）：(4*center + 2*(N+S+E+W) - (NN+SS+EE+WW)) >> 3",
        "3. 实现 R 插值（Gb 位置）：水平强调 5×5 kernel",
        "4. 实现 B 插值（Gr 位置）：垂直强调 5×5 kernel（R 插值的转置）",
        "5. 实现 R/B 互插（B/R 位置）：对角 kernel",
        "6. 实现 Bayer 位置跟踪：row/col 奇偶 + cfg_bayer 确定当前像素类型",
        "7. 验证：RGGB 输入经 demosaic 后输出完整 RGB，单色场景无色伪影",
    ],
    "isp_ccm": [
        "1. 实现 3×3 Q4.8 有符号乘法器：smul(pix, coeff) 处理符号位",
        "2. 实现 R/G/B 三路 MAC 累加：r_acc = Σ smul(pix_ch, coeff_row_ch)",
        "3. 实现结果归一化：acc >> 8，裁剪到 [0, pixel_max]",
        "4. 实现 9 个 CCM 系数可配置：c00~c22 通过 APB 设置",
        "5. 验证：单位矩阵 CCM 直通，标准 sRGB 矩阵色彩校正正确",
    ],
    "isp_gamma": [
        "1. 实现 4096-entry per-channel LUT：gamma_r/gamma_g/gamma_b 各 4096 项",
        "2. 实现三路并行查表：pix_r/g/b 各自索引对应 LUT",
        "3. 实现 LUT 可编程：APB 分块加载 gamma 曲线数据",
        "4. 验证：gamma 2.2 曲线加载后输出符合 sRGB 非线性映射",
    ],
    "isp_ae_stats": [
        "1. 实现 Y 累加器：y_acc 逐像素累加 pix_y",
        "2. 实现 Y² 累加器：y_sq_acc = Σ(pix_y - center_illum)²",
        "3. 实现 Y³ 带符号累加器：y_cu_acc = Σ sign(pix_y - center_illum) × |pix_y - center_illum|³",
        "4. 实现 SOF 复位：pix_sof 时清零 y_acc/y_sq_acc/y_cu_acc/cnt",
        "5. 实现中心照度加权：cfg_center_illum 用于 ROI 曝光评估",
        "6. 验证：均匀亮度输入 y_sq_acc 和 y_cu_acc 接近 0（无偏斜）",
    ],
    "isp_csc": [
        "1. 实现 BT.601 矩阵：Y=(77R+150G+29B)>>8, Cb=(-43R-85G+128B)>>8+128, Cr=(128R-107G-21B)>>8+128",
        "2. 实现 BT.709 矩阵：Y=(47R+157G+16B)>>8, Cb=(-26R-86G+112B)>>8+128, Cr=(112R-102G-10B)>>8+128",
        "3. 实现 cfg_std 标准切换：0=BT.709, 1=BT.601",
        "4. 实现输出裁剪：Y/Cb/Cr 均限制在 [0, 255]",
        "5. 验证：纯红(255,0,0) 经 BT.601 转换后 Y=77, Cb=85, Cr=255",
    ],
    "isp_ldci": [
        "1. 实现 8×8 tile 网格划分：根据 (x_cnt, y_cnt) 确定当前 tile 位置",
        "2. 实现 per-tile 直方图累加：每个 tile 256 bin histogram",
        "3. 实现 clip limit 裁剪：histogram[i] = min(hist[i], cfg_clip_limit)",
        "4. 实现 CDF 计算：cumulative[i] = Σ hist[0..i]，归一化到 [0, 255]",
        "5. 实现 ping-pong LUT 缓冲：当前帧使用 LUT_A，下一帧使用 LUT_B，交替切换",
        "6. 实现 3 状态 FSM：IDLE → HIST → CDF → APPLY",
        "7. 验证：低对比度图像经 CLAHE 后局部对比度增强",
    ],
    "isp_sharpen": [
        "1. 实现 3×3 高斯平滑窗口：[1,2,1; 2,4,2; 1,2,1]，总和 16",
        "2. 实现 detail 提取：detail = center - smoothed",
        "3. 实现 Q4.4 强度控制：sharpened = center + (detail * strength) >> 4",
        "4. 实现 Y 通道处理，Cb/Cr 直通",
        "5. 实现 saturation 裁剪：结果限制在 [0, 255]",
        "6. 验证：strength=16 (1.0x) 时边缘增强明显，strength=0 时直通",
    ],
    "isp_nr2d": [
        "1. 实现 3×3 box 滤波器：smooth = (center + Σ neighbors[:8]) >> 3",
        "2. 实现 Q4.4 混合强度：blend = (original * (16-strength) + smooth * strength) >> 4",
        "3. 实现 Y 通道降噪，Cb/Cr 直通",
        "4. 实现 saturation 裁剪：结果限制在 [0, 255]",
        "5. 验证：strength=4 时轻微降噪，strength=16 时完全平滑",
    ],
    "isp_scale": [
        "1. 实现 x/y 像素计数器：pix_eol 时 x 归零 y 递增，pix_sof 时 y 归零",
        "2. 实现 scale_x 分频：0=1x (全部输出), 1=1/2x (偶数像素), 2=1/4x (4 的倍数)",
        "3. 实现 scale_y 分频：同 scale_x 逻辑",
        "4. 实现 emit 逻辑：仅 out_x && out_y 时输出有效像素",
        "5. 实现 pix_eol 修正：仅当 out_x 时输出 eol",
        "6. 验证：scale_x=1, scale_y=1 时输出分辨率为输入的 1/4",
    ],
    "isp_yuv": [
        "1. 实现 444 模式直通：Y/Cb/Cr 全部输出",
        "2. 实现 422 模式 Cb/Cr 水平平均：偶数像素保存 Cb/Cr，奇数像素累加后 >> 1",
        "3. 实现 420 模式垂直平均：隔行输出 Cb/Cr（y_cnt == 0 时输出平均值）",
        "4. 实现 cfg_format 模式切换：0=444, 1=422, 2=420",
        "5. 验证：422 模式下 Cb/Cr 数据率为 Y 的一半，颜色无失真",
    ],
    "isp_axi_out": [
        "1. 实现 AXI-Stream master 输出：m_axis_tvalid/tready/tdata/tlast/tuser",
        "2. 实现 YCbCr 444 打包：tdata = {cr[7:0], cb[7:0], y[7:0]} (24-bit)",
        "3. 实现 2 级握手缓冲：pix_valid & m_ready 时加载输出寄存器",
        "4. 实现 out_valid 延迟：m_ready 但无新像素时输出保持",
        "5. 验证：连续 pix_valid 输入产生连续 AXI-Stream 输出，反压时不丢数据",
    ],
    "isp_apb_regs": [
        "1. 实现 APB 2-cycle 访问协议：setup phase (psel) + access phase (penable)",
        "2. 实现 32×32-bit 寄存器阵列：reg_0 ~ reg_31，写操作在 psel & penable & pwrite 时执行",
        "3. 实现读操作：prdata = reg[addr>>2 & 0x1F]，在 access phase 输出",
        "4. 实现 enable 字段解码：从 reg_0~reg_5 提取各模块 enable 信号输出",
        "5. 实现 pready/pslverr 输出：pready = psel & penable, pslverr = 0",
        "6. 验证：APB 写 reg_0 后读取值一致，enable 字段正确映射到 cfg_*_enable",
    ],
}


def register_isp_skeleton_steps():
    """Register ISP PE type implementation steps into the skeleton template registry."""
    _TEMPLATE_STEPS.update(_ISP_SKELETON_STEPS)


# Auto-register on import
register_isp_skeleton_steps()

__all__ = ["register_isp_skeleton_steps", "_ISP_SKELETON_STEPS"]
