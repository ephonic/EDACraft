// iterative_solver.hpp — BiCGSTAB + ILU(0) 迭代线性求解器
//
// Phase A1-6：为 LinearSolver 接口提供迭代求解器实现，作为 KLU 之外的备选。
// 用于大规模稀疏 MNA：当矩阵极度稀疏、内存敏感或 KLU 不可用时，
// BiCGSTAB(2) + ILU(0) 预条件能在很多电路问题上提供合理的常数因子。
//
// 算法：
//   - 预条件：ILU(0)（保留原矩阵稀疏模式的 incomplete LU，dropping=0）
//     —— 对电路 MNA（强对角占优 + 局部耦合）预条件效果好。
//   - 主迭代：Bi-Conjugate Gradient Stabilized（van der Vorst 1992），
//     相比 GMRES(m) 内存恒定（O(n)），适合长周期 transient/shooting。
//   - 失败（达到 maxIter 未收敛或 breakdown）时：factorize 返回 false，
//     调用方（factory）会回退到 DenseLu/KLU 保正确性。
//
// 注意：BiCGSTAB 对病态矩阵可能 breakdown（rho=0 或 omega=0）；
// 这种情况下返回未收敛，由上层回退。不要把迭代求解器设为 Auto 的默认——
// Auto 仍首选 KLU，BiCgStab 仅在显式 .options method=bicgstab 时启用。
#ifndef RFSIM_ASSEMBLY_ITERATIVE_SOLVER_HPP
#define RFSIM_ASSEMBLY_ITERATIVE_SOLVER_HPP

#include "linear_solver.hpp"
#include "matrix.hpp"
#include <cstdint>
#include <vector>

namespace rfsim {

class BiCgStabSolver : public LinearSolver {
public:
    BiCgStabSolver();

    // 保留矩阵 A 的 CSR（用于 BiCGSTAB 的 SpMV）+ 计算 ILU(0) 预条件。
    // A 需已 finalize。返回 false 若 ILU(0) 分解出现零主元（无法预条件）。
    bool factorize(const SparseMatrix& A) override;

    // BiCGSTAB 求解 A·x = b。x 初始可为任意（建议 0），输出解。
    // 收敛到 reltol·‖b‖ + abstol；否则 x 为当前最佳近似。
    void solve(const Vector& b, Vector& x) const override;

    [[nodiscard]] uint32_t dim() const noexcept override { return n_; }
    [[nodiscard]] bool supportsRefactor() const override { return false; }
    [[nodiscard]] const char* name() const override { return "bicgstab"; }

    // 迭代参数（可在 factorize 前由调用方调整）。
    void setMaxIter(uint32_t m) { maxIter_ = m; }
    void setReltol(double t) { reltol_ = t; }
    void setAbstol(double t) { abstol_ = t; }

    // 最后一次 solve 的诊断（供 verbose 输出）。
    [[nodiscard]] uint32_t lastIterations() const noexcept { return lastIter_; }
    [[nodiscard]] double lastResidual() const noexcept { return lastRes_; }
    [[nodiscard]] bool lastConverged() const noexcept { return lastConv_; }

private:
    uint32_t n_ = 0;
    uint32_t maxIter_ = 1000;
    double reltol_ = 1e-8;
    double abstol_ = 1e-12;

    // 矩阵 CSR（BiCGSTAB 的 SpMV 用）
    std::vector<uint32_t> rowPtr_;  // size n+1
    std::vector<uint32_t> colIdx_;  // size nnz
    std::vector<double>   vals_;    // size nnz

    // ILU(0) 预条件因子（同稀疏模式）：L+U 合并存于 ilu_，对角线为 U（单位 L）
    std::vector<double> ilu_;
    // 每行对角元素在 ilu_ 中的下标（applyIlu 前代/回代用）
    std::vector<int32_t> diagPos_;
    // ILU 每行非对角列索引（与 colIdx_ 同序），便于 triangular solve
    // —— 为简化实现，ILU(0) 的 apply 直接按 CSR 行扫描做就地前/回代。

    mutable uint32_t lastIter_ = 0;
    mutable double lastRes_ = 0.0;
    mutable bool lastConv_ = false;

    // ILU(0) 预条件 apply：z = (LU)^{-1} r（就地前代 + 回代，按 CSR 行序）
    void applyIlu(const Vector& r, Vector& z) const;
};

} // namespace rfsim

#endif // RFSIM_ASSEMBLY_ITERATIVE_SOLVER_HPP
