// lu_solver.hpp — 稠密 LU 直接求解器（部分选主元）
//
// 求解 A·x = b。DC 工作点阶段电路规模小，用稠密 LU 简单可靠。
// 大规模/HB 阶段(§4.6)将换为预条件 GMRES。
//
// 实现：Doolittle 分解 + 部分选主元 PA = LU，前代/回代求解。
//
// Phase A1：继承 LinearSolver，使 dc_op/shooting/time_stepper 可通过
// 基类指针多态选用，且 Auto 策略在小规模/稠密场景回退到此。
#ifndef RFSIM_ASSEMBLY_LU_SOLVER_HPP
#define RFSIM_ASSEMBLY_LU_SOLVER_HPP

#include "linear_solver.hpp"
#include "matrix.hpp"
#include <vector>

namespace rfsim {

class LuSolver : public LinearSolver {
public:
    LuSolver() = default;

    // 分解矩阵（n x n 稠密，从 SparseMatrix 读取）。
    // 返回 false 若矩阵奇异。
    bool factorize(const SparseMatrix& A) override;

    // 求解 A·x = b（需先 factorize）。x 输出。
    void solve(const Vector& b, Vector& x) const override;

    [[nodiscard]] uint32_t dim() const noexcept override { return n_; }

    // 稠密 LU 无符号分解概念，每次 factorize 都全分解。
    [[nodiscard]] bool supportsRefactor() const override { return false; }
    [[nodiscard]] const char* name() const override { return "dense-lu"; }

private:
    uint32_t n_ = 0;
    std::vector<double>   lu_;      // n*n，行主序，存 LU 合并
    std::vector<uint32_t> piv_;     // 行置换（主元行索引）
};

} // namespace rfsim

#endif // RFSIM_ASSEMBLY_LU_SOLVER_HPP
