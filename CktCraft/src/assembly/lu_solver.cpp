// lu_solver.cpp — 稠密 LU 求解器实现（部分选主元高斯消去）
#include "lu_solver.hpp"

#include <algorithm>
#include <cmath>

namespace rfsim {

namespace {
inline double& at(std::vector<double>& m, uint32_t n, uint32_t i, uint32_t j) {
    return m[size_t(i) * n + j];
}
inline double at(const std::vector<double>& m, uint32_t n, uint32_t i, uint32_t j) {
    return m[size_t(i) * n + j];
}
} // namespace

bool LuSolver::factorize(const SparseMatrix& A) {
    n_ = A.dim();
    const uint32_t n = n_;
    lu_.assign(size_t(n) * n, 0.0);
    piv_.resize(n);
    for (uint32_t i = 0; i < n; ++i) piv_[i] = i;

    // 从稀疏矩阵填充稠密
    for (uint32_t i = 0; i < n; ++i) {
        for (uint32_t j = 0; j < n; ++j) {
            at(lu_, n, i, j) = A.get(i, j);
        }
    }

    // 列循环高斯消去 + 部分选主元
    for (uint32_t k = 0; k < n; ++k) {
        // 选主元：找第 k 列中 |lu[i][k]| 最大的行 i>=k
        uint32_t pivRow = k;
        double maxVal = std::fabs(at(lu_, n, k, k));
        for (uint32_t i = k + 1; i < n; ++i) {
            double v = std::fabs(at(lu_, n, i, k));
            if (v > maxVal) { maxVal = v; pivRow = i; }
        }
        if (maxVal < 1e-300) {
            // 奇异
            return false;
        }
        // 交换行
        if (pivRow != k) {
            for (uint32_t j = 0; j < n; ++j) {
                std::swap(at(lu_, n, k, j), at(lu_, n, pivRow, j));
            }
            std::swap(piv_[k], piv_[pivRow]);
        }
        // 消去
        double pivot = at(lu_, n, k, k);
        for (uint32_t i = k + 1; i < n; ++i) {
            double factor = at(lu_, n, i, k) / pivot;
            at(lu_, n, i, k) = factor;  // 存 L 的下三角
            for (uint32_t j = k + 1; j < n; ++j) {
                at(lu_, n, i, j) -= factor * at(lu_, n, k, j);
            }
        }
    }
    return true;
}

void LuSolver::solve(const Vector& b, Vector& x) const {
    const uint32_t n = n_;
    x.assign(n, 0.0);
    // 应用行置换: y = P*b
    Vector y(n);
    for (uint32_t i = 0; i < n; ++i) y[i] = b[piv_[i]];

    // 前代 L·z = y（L 对角线为 1）
    for (uint32_t i = 0; i < n; ++i) {
        double s = y[i];
        for (uint32_t j = 0; j < i; ++j) s -= at(lu_, n, i, j) * x[j];
        x[i] = s;
    }
    // 回代 U·x = z
    for (int32_t ii = int32_t(n) - 1; ii >= 0; --ii) {
        uint32_t i = uint32_t(ii);
        double s = x[i];
        for (uint32_t j = i + 1; j < n; ++j) s -= at(lu_, n, i, j) * x[j];
        x[i] = s / at(lu_, n, i, i);
    }
}

} // namespace rfsim
