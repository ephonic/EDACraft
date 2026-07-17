// =====================================================================
// mom/solver/pfft.hpp —— 预校正 FFT（pFFT）加速 + 迭代求解器
//
// 完整 pFFT 实现：
//   1. 基函数投影到规则均匀网格
//   2. 远场相互作用用 FFT 全局卷积（O(N log N)）
//   3. 近场预校正：小距离单元对直接精确计算补偿
//   4. GMRES 迭代求解器使用 pFFT 矩阵向量乘法
//   5. 内存 O(N)，适合 N=10k~数百万级
// =====================================================================
#pragma once

#include "mom/common/types.hpp"
#include "mom/common/vec3.hpp"
#include "mom/mesh/trimesh.hpp"
#include "mom/green/dyadic.hpp"
#include <vector>
#include <functional>
#include <cmath>
#include <algorithm>
#include <complex>

namespace mom::solver {

// 格林函数查找表（简化版，供快速装配用）
class GreenLookupTable {
public:
    GreenLookupTable(std::function<Complex(Real)> eval, Real rho_min, Real rho_max,
                      Size n_grid = 2000)
        : rho_min_(rho_min), rho_max_(rho_max), n_grid_(n_grid) {
        if (rho_max <= rho_min) rho_max = rho_min + 1.0;
        drho_ = (rho_max - rho_min) / Real(n_grid - 1);
        table_.resize(n_grid);
        for (Size i = 0; i < n_grid; ++i) {
            Real rho = rho_min + Real(i) * drho_;
            table_[i] = eval(rho);
        }
    }

    Complex operator()(Real rho) const {
        if (rho <= rho_min_) return table_.front();
        if (rho >= rho_max_) return Complex(0, 0);
        Real t = (rho - rho_min_) / drho_;
        Index i = Index(t);
        if (i < 0) i = 0;
        if (i >= Index(n_grid_) - 1) i = Index(n_grid_) - 2;
        Real frac = t - Real(i);
        return table_[i] * (1.0 - frac) + table_[i + 1] * frac;
    }

    Size grid_size() const { return n_grid_; }

private:
    Real rho_min_, rho_max_, drho_;
    Size n_grid_;
    std::vector<Complex> table_;
};

// pFFT 配置
struct PFFTConfig {
    Real near_threshold = 0.0;  // 近场校正距离阈值（米）
    Size grid_resolution = 0;   // 网格分辨率（0=自动）
    bool use_double_precision_far = false;
};

// pFFT 矩阵向量乘法器
class PFFTMatrixVector {
public:
    // 从三角网格 + 格林函数构建 pFFT
    PFFTMatrixVector(
        const mesh::TriMesh& mesh,
        const green::dyadic::SpatialDyadic& green,
        const PFFTConfig& config = PFFTConfig()
    );

    // 析构函数（在 cpp 中实现，避免不完整类型问题）
    ~PFFTMatrixVector();

    // 矩阵向量乘法：y = Z·x（x, y 为基函数系数向量）
    std::vector<Complex> multiply(const std::vector<Complex>& x) const;

    Index size() const { return nb_; }

private:
    Index nb_;
    // 内部实现细节（网格、投影权重、FFT 数据等）
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

// GMRES 迭代求解器（使用 pFFT 矩阵向量乘法）
std::vector<Complex> solve_gmres(
    const PFFTMatrixVector& A,
    const std::vector<Complex>& b,
    Real tol = 1e-6,
    Index max_iter = 1000,
    Index restart = 50
);

} // namespace mom::solver
