// =====================================================================
// mom/microstrip.hpp —— 微带线 MoM 求解器（阶段 1 顶层）
//
// 把“网格 + MPIE 装配 + 直接解 + 端口 + S 参数”串成一个易用 API。
// 阶段 1：自由空间 + 接地镜像格林函数，介质以有效介电常数近似。
// 阶段 2：格林函数替换为完整多层介质版本，此 API 不变。
// =====================================================================
#pragma once

#include "mom/common/types.hpp"
#include "mom/common/vec3.hpp"
#include "mom/green/green.hpp"
#include "mom/mesh/mesh.hpp"
#include <vector>

namespace mom {

// 微带线几何与求解配置。
struct MicrostripConfig {
    Real length   = 20.0e-3;   // 走线长度 L (m)
    Real width    = 3.0e-3;    // 走线宽度 W (m)
    Real height   = 1.6e-3;    // 介质厚度 h（导体到接地平面，m）
    Real eps_eff  = 1.0;       // 有效介电常数（阶段 1 近似；阶段 2 由格林函数吸收）
    Index nx      = 40;        // x 方向分段数
    int  gauss    = 4;         // 每段高斯积分点数
    Real z0_ref   = 50.0;      // 端口参考阻抗（欧姆）
    bool has_ground = true;    // 是否有接地平面（镜像）
};

// 在单个频点求解，返回 (nport=2) 端口的 S 参数行主序 2×2。
//   freq  : 频率 (Hz)
//   cfg   : 配置
// 返回 {S11, S12, S21, S22}。
std::vector<Complex> solve_microstrip_sparam(Real freq,
                                             const MicrostripConfig& cfg);

} // namespace mom
