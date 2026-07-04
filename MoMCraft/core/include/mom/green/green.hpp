// =====================================================================
// mom/green/green.hpp —— 空域格林函数（阶段 1：自由空间 + 接地镜像）
//
// 阶段 1 用最简单的可解析格林函数验证 MoM 闭环：
//   - 标量势格林函数 G = 1/(4π) · [1/R1 - 1/R2]
//     其中 R1 = |r - r'|（直接），R2 = |r - r'_image|（关于接地平面镜像）。
//   - “-”号：PEC 接地平面对标量势（Dirichlet）的镜像反号。
//   - 矢量势镜像同号（Neumann）：G_A = 1/(4π)·[1/R1 + 1/R2]。
//
// 阶段 2 将替换为完整多层介质格林函数（极点/支线分离 + 多段 DCIM + FHT），
// 接口保持一致，便于平滑升级。
//
// 介质效应在阶段 1 暂以“有效介电常数”近似体现在波数 k 上；
// 严格的多层格林函数在阶段 2 完成。
// =====================================================================
#pragma once

#include "mom/common/types.hpp"
#include "mom/common/vec3.hpp"
#include "mom/green/medium.hpp"     // DielectricLayer, Stackup, groundz_is_real
#include "mom/green/spectral.hpp"   // 谱域（阶段 2 实装）
#include "mom/green/poles.hpp"      // 极点搜索（阶段 2 实装）
#include "mom/green/branch.hpp"     // 多段 DCIM（阶段 2 实装）
#include "mom/green/sommerfeld.hpp" // FHT（阶段 2 实装）
#include <vector>
#include <cmath>

namespace mom::green {

// DielectricLayer / Stackup / groundz_is_real 见 medium.hpp（公共头，避免循环包含）。

// ---------- 阶段 1：自由空间 + 接地镜像格林函数（含时谐相位） ----------

// 真空波数 k0 = ω√(μ0 ε0) = ω/c0。
inline Real k0(Real omega) { return omega / phys::c0; }

// 自由空间【直接】格林函数核（奇异于 r_obs=r_src）：g = e^{-jkR}/R。
inline Complex green_direct(const Vec3& r_obs, const Vec3& r_src, Real k) {
    const Real R = dist(r_obs, r_src);
    if (R < 1e-30) return Complex(0.0, 0.0);   // 自点由装配层用解析自项处理
    return std::exp(Complex(0.0, -k * R)) / R;
}

// 【镜像】核（永远平滑，因为镜像点与观测点不同平面，距离≥2·|h|）。
//   关于 z=ground_z 的镜像源：r_img.z = 2·ground_z − r_src.z。
inline Vec3 mirror(const Vec3& r_src, Real ground_z) {
    Vec3 r = r_src;
    r.z = 2.0 * ground_z - r_src.z;
    return r;
}

// 标量势【镜像】核 g_phi_img = −e^{-jkR2}/R2（Dirichlet 反号）。无接地→0。
inline Complex scalar_green_image(const Vec3& r_obs, const Vec3& r_src, Real k, Real ground_z) {
    if (!groundz_is_real(ground_z)) return Complex(0.0, 0.0);
    return -green_direct(r_obs, mirror(r_src, ground_z), k);
}
// 矢量势【镜像】核 g_A_img = +e^{-jkR2}/R2（Neumann 同号）。无接地→0。
inline Complex vector_green_image(const Vec3& r_obs, const Vec3& r_src, Real k, Real ground_z) {
    if (!groundz_is_real(ground_z)) return Complex(0.0, 0.0);
    return +green_direct(r_obs, mirror(r_src, ground_z), k);
}

// 标量势格林函数核（直接 + 镜像）：g(R1) − g(R2)。
inline Complex scalar_green(const Vec3& r_obs, const Vec3& r_src, Real k, Real ground_z) {
    return green_direct(r_obs, r_src, k) + scalar_green_image(r_obs, r_src, k, ground_z);
}
// 矢量势格林函数核（直接 + 镜像）：g(R1) + g(R2)。
inline Complex vector_green(const Vec3& r_obs, const Vec3& r_src, Real k, Real ground_z) {
    return green_direct(r_obs, r_src, k) + vector_green_image(r_obs, r_src, k, ground_z);
}

} // namespace mom::green
