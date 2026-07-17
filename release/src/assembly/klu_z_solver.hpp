// klu_z_solver.hpp — 复数版 KLU 稀疏求解器（klu_z_*）
//
// 用于 AC 分析：复数矩阵 Ax=b 直接求解。
// 复数存储格式：KLU 用实虚对拆分（Ax[2*k]=Re, Ax[2*k+1]=Im）。
//
// 工作流：
//   1) 首次：klu_analyze (symbolic) + klu_z_factor (numeric)
//   2) pattern 不变时：klu_z_refactor (仅数值更新，省 symbolic)
//   3) solve: klu_z_solve (原位)
#ifndef RFSIM_ASSEMBLY_KLU_Z_SOLVER_HPP
#define RFSIM_ASSEMBLY_KLU_Z_SOLVER_HPP

#include "../util/bench.hpp"
#include <cstdint>
#include <vector>

namespace rfsim {

class KluZSolver {
public:
    KluZSolver();
    ~KluZSolver();

    KluZSolver(const KluZSolver&) = delete;
    KluZSolver& operator=(const KluZSolver&) = delete;
    KluZSolver(KluZSolver&&) noexcept;
    KluZSolver& operator=(KluZSolver&&) noexcept;

    // 从 CSC 格式分解。Ap/Ai 是 int，Ax 是 double[2*nz]（实虚对）。
    // 首次调 analyze+factor；后续 pattern 相同调 refactor。
    bool factorize(int n, const int* Ap, const int* Ai, const double* Ax);

    // 求解 Ax=b。B 是 double[2*n]（实虚对），原位覆写为解。
    void solve(double* B) const;

    [[nodiscard]] int dim() const noexcept { return n_; }

    // bench 计时
    [[nodiscard]] double factorMs() const noexcept { return factorMs_; }
    [[nodiscard]] double solveMs() const noexcept { return solveMs_; }

private:
    void freeFactors() noexcept;

    int n_ = 0;
    void* sym_    = nullptr;
    void* num_    = nullptr;
    void* common_ = nullptr;
    bool analyzed_ = false;
    // CSR→CSC 转置缓存
    std::vector<int> cscAp_, cscAi_;
    std::vector<double> cscAx_;

    double factorMs_ = 0.0;
    mutable double solveMs_ = 0.0;
};

} // namespace rfsim

#endif // RFSIM_ASSEMBLY_KLU_Z_SOLVER_HPP
