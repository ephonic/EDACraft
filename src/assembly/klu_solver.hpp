// klu_solver.hpp — SuiteSparse KLU 稀疏直接求解器封装
//
// 用途：Shooting 内层 Newton 与外层 monodromy 雅可比的稀疏 Ax=b 求解。
//   KLU = 分块三角化 (BTF) + AMD 排序 + 部分选主元 LU。
//   对电路型不对称稀疏矩阵接近最优复杂度。
//
// 接口与 LuSolver 对齐（factorize / solve / dim）以便就地替换。
//
// 注意：rfsim 的 SparseMatrix 内部是 CSR；KLU 的 API 输入必须是 CSC。
// factorize() 内部完成 CSR→CSC 转置（对一般非对称矩阵 CSR 转 CSC = CSR(A^T)）。
// 因此我们调用 klu_solve 时使用 SOLVE 模式（A x = b），而非 TSOLVE。
//
// 详见 plan.md §4.x（DC/Shooting 直接求解器）与 cmake/SuiteSparseKLU.cmake。
#ifndef RFSIM_ASSEMBLY_KLU_SOLVER_HPP
#define RFSIM_ASSEMBLY_KLU_SOLVER_HPP

#include "matrix.hpp"
#include "../util/bench.hpp"
#include <cstdint>
#include <vector>

namespace rfsim {

class KluSolver {
public:
    KluSolver();
    ~KluSolver();

    // 不可拷贝（持有 KLU 资源）
    KluSolver(const KluSolver&) = delete;
    KluSolver& operator=(const KluSolver&) = delete;
    KluSolver(KluSolver&&) noexcept;
    KluSolver& operator=(KluSolver&&) noexcept;

    // 分解稀疏矩阵 A（n x n，CSR 输入）。返回 false 若奇异/分析失败。
    // 内部：CSR → CSC 转置 → klu_analyze（首次或模式变化时）→ klu_factor。
    bool factorize(const SparseMatrix& A);

    // 求解 A·x = b（需先 factorize）。
    void solve(const Vector& b, Vector& x) const;

    [[nodiscard]] uint32_t dim() const noexcept { return n_; }

    // V2-γ C3: bench 计时（仅 RFSIM_BENCH_JSON=1 时累加，否则保持 0）
    [[nodiscard]] double factorMs() const noexcept { return factorMs_; }
    [[nodiscard]] double solveMs()  const noexcept { return solveMs_; }

private:
    void freeFactors() noexcept;

    uint32_t n_ = 0;

    // CSC（int 索引：KLU 接受 int 或 SuiteSparse_long；这里用 int 简化）
    std::vector<int>    Ap_;   // size n+1
    std::vector<int>    Ai_;   // size nnz
    std::vector<double> Ax_;   // size nnz

    // KLU 不透明句柄。用 void* 是为了把 klu.h 完全挡在 .cpp 内：
    // klu.h 把 klu_symbolic / klu_numeric / klu_common 都用 typedef struct{...}
    // 形式定义，会与任何前向声明冲突。
    void* sym_    = nullptr;   // klu_symbolic*
    void* num_    = nullptr;   // klu_numeric*
    void* common_ = nullptr;   // klu_common*

    // V2-γ C3: 累计计时（solve 标 const，故 mutable）
    // L2: mutable 仅用于 bench 计时，非线程安全——勿跨线程共享 KluSolver
    double factorMs_ = 0.0;
    mutable double solveMs_  = 0.0;
};

} // namespace rfsim

#endif // RFSIM_ASSEMBLY_KLU_SOLVER_HPP
