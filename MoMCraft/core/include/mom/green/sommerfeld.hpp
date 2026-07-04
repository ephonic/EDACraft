// =====================================================================
// mom/green/sommerfeld/sommerfeld.hpp —— 索末菲尔德积分快速计算
//
// 阶段 2 实现：剩余需数值求解的索末菲尔德积分
//     G(rho) = (1/2pi) ∫_0^∞ G_tilde(k_rho) J0(k_rho rho) k_rho dk_rho
// 该积分核【高振荡、收敛慢】，传统数值积分无法快速收敛。采用：
//   1. 数值路径变换（Sommerfeld 积分路径变形，沿最速下降路径）消除振荡；
//   2. 快速汉克尔变换（FHT）批量高效计算 J0 型积分，适合扫频与扫 rho。
// =====================================================================
#pragma once

#include "mom/common/types.hpp"

namespace mom::green::sommerfeld {

// 占位：数值路径变换 + FHT 计算（阶段 2 填充）。
inline Real fast_hankel_transform_demo() {
    // TODO 阶段2
    return {};
}

} // namespace mom::green::sommerfeld
