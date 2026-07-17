// =====================================================================
// mom/green/medium.hpp —— 平面分层介质描述（无循环依赖的公共头）
//
// DielectricLayer / Stackup 被 green.hpp 与 spectral.hpp 共用，单独提取避免循环包含。
// =====================================================================
#pragma once

#include "mom/common/types.hpp"
#include <vector>
#include <limits>

namespace mom::green {

// 平面分层介质中的一层。
struct DielectricLayer {
    Real thickness = 0.0;   // m；外半空间用 is_half_space=true（厚度忽略）
    Real eps_r     = 1.0;   // 相对介电常数（实部）
    Real tand      = 0.0;   // 损耗角正切
    Real mu_r      = 1.0;   // 相对磁导率
    bool  is_half_space = false; // 顶/底半空间
};

// 多层介质叠层描述（自底向上）。
struct Stackup {
    std::vector<DielectricLayer> layers;
    Real ground_z = 0.0;   // 底部接地平面 z（镜像参考）；无接地则置 NaN
    Real cover_z  = std::numeric_limits<Real>::quiet_NaN();  // 顶部 PEC 封闭 z；NaN=开放（上侧半空间）
};

// 判断 ground_z / cover_z 是否为有效 PEC 平面（NaN 表示无）。
inline bool groundz_is_real(Real z) { return z == z; /* NaN!=NaN */ }

} // namespace mom::green
