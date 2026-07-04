// =====================================================================
// mom/mesh/mesh.hpp —— 矩形网格 + 屋顶（rooftop）基函数
//
// 阶段 1 范围：平面（z=const）矩形带状导体上的 1D 屋顶基函数。
// 这是 PCB/IC 互连线中最常见的情形（沿 x 走向的微带/带状线）。
//
// 屋顶基函数定义在相邻两段上：第 i 个基函数在第 i 段上升、第 i+1 段下降，
// 中心节点为 i。电流沿 x 流动，幅值连续、端点为零（电荷守恒）。
//
// 几何：带子在 z=z0 平面，宽 W（y 方向）、长 L（x 方向）。
// 沿 x 分成 Nx 段，每段长 dx；沿 y 分成 Ny 段用于面积分。
// =====================================================================
#pragma once

#include "mom/common/types.hpp"
#include "mom/common/vec3.hpp"
#include <vector>
#include <array>

namespace mom::mesh {

// 一个矩形面元（在 z=z0 平面）
struct RectCell {
    Real x0, y0, z0;   // 中心坐标
    Real dx, dy;        // x、y 边长
};

// 屋顶基函数：覆盖两个相邻 x 段（左段 index，右段 index+1）。
struct RooftopBasis {
    Index left_seg;     // 左段索引（沿 x 的段号）
    Index right_seg;    // 右段索引 = left_seg + 1
    Real  x_center;     // 屋顶中心 x（节点坐标）
};

// 矩形带状网格
struct RectMesh {
    Real  x_min = 0.0, x_max = 0.0;   // 带子 x 范围
    Real  y_min = 0.0, y_max = 0.0;   // 带子 y 范围（宽度）
    Real  z0    = 0.0;                // 导体所在 z
    Index nx = 0;                     // x 方向分段数
    Index ny = 1;                     // y 方向分段数（宽度积分用）
    Real  dx() const { return (x_max - x_min) / Real(nx); }
    Real  dy() const { return (x_max == x_min ? 0.0 : (y_max - y_min) / Real(ny)); }

    // 生成 x 方向的段（每段一个 RectCell，宽度取全宽 W）。
    // 这里“段”仅指 x 方向；y 方向的细化在面积分内做（保持 1D 基函数）。
    std::vector<RectCell> x_segments() const;

    // 生成屋顶基函数（nx 段 → nx-1 个基函数）。
    std::vector<RooftopBasis> bases() const;
};

// 屋顶基函数在某点 (x,y) 的 x 方向电流密度形状值 f(x)（不含归一化幅值）。
// 左段线性上升、右段线性下降，节点处为 1，两端为 0。
Real rooftop_shape(const RooftopBasis& b, Real x, Real seg_dx);

// 屋顶基函数的散度（电荷连续性）：d(f)/dx。
// 左段 +1/dx，右段 -1/dx，常数。返回各段上的散度值。
std::array<Real, 2> rooftop_div(const RooftopBasis& b, Real seg_dx);

} // namespace mom::mesh
