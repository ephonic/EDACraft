// =====================================================================
// mom/common/types.hpp —— 全局基础数值类型与物理常数
// =====================================================================
#pragma once

#include <complex>
#include <cstddef>
#include <limits>

namespace mom {

// ---- 标量类型：全工程默认双精度复数 ----
using Real   = double;
using Complex = std::complex<Real>;

// double-complex 的虚数单位
constexpr Complex Iunit{0.0, 1.0};

// ---- 索引 / 维度 ----
using Index  = std::ptrdiff_t;   // 有符号，便于做差值运算
using Size   = std::size_t;

// ---- 物理常数（SI） ----
namespace phys {
    constexpr Real c0   = 2.99792458e8;     // 真空光速 (m/s)
    constexpr Real mu0  = 1.2566370614e-6;  // 真空磁导率 (H/m)
    constexpr Real eps0 = 8.8541878128e-12; // 真空介电常数 (F/m)
    constexpr Real eta0 = 376.730313668;    // 真空波阻抗 (ohm)
    constexpr Real pi   = 3.14159265358979323846;
    constexpr Real inv_4pi = 1.0 / (4.0 * pi);
} // namespace phys

// ---- 常用数值阈值 ----
constexpr Real kDefaultTol = 1e-3;          // 相对容差（格林函数拟合等）
constexpr Real kInf = std::numeric_limits<Real>::infinity();

} // namespace mom
