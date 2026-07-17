// lu_solver.hpp — 稠密 LU 直接求解器（部分选主元）
//
// 求解 A·x = b。DC 工作点阶段电路规模小，用稠密 LU 简单可靠。
// 大规模/HB 阶段(§4.6)将换为预条件 GMRES。
//
// 实现：Doolittle 分解 + 部分选主元 PA = LU，前代/回代求解。
#ifndef RFSIM_ASSEMBLY_LU_SOLVER_HPP
#define RFSIM_ASSEMBLY_LU_SOLVER_HPP

#include "matrix.hpp"
#include <vector>

namespace rfsim {

class LuSolver {
public:
    LuSolver() = default;

    // 分解矩阵（n x n 稠密，从 SparseMatrix 读取）。
    // 返回 false 若矩阵奇异。
    bool factorize(const SparseMatrix& A);

    // 求解 A·x = b（需先 factorize）。x 输出。
    void solve(const Vector& b, Vector& x) const;

    [[nodiscard]] uint32_t dim() const noexcept { return n_; }

private:
    uint32_t n_ = 0;
    std::vector<double>   lu_;      // n*n，行主序，存 LU 合并
    std::vector<uint32_t> piv_;     // 行置换（主元行索引）
};

} // namespace rfsim

#endif // RFSIM_ASSEMBLY_LU_SOLVER_HPP
