// umfpack_solver.hpp — SuiteSparse UMFPACK 稀疏直接求解器封装
//
// UMFPACK = 多列前沿（multifrontal）+ AMD/COLAMD 排序 + 部分选主元 LU。
// 对中等规模稠密填充重的稀疏矩阵常优于 KLU（KLU 的 BTF 对电路最优，UMFPACK
// 的 multifrontal 对一般非对称矩阵 + BLAS-3 密集块更新更强）。
//
// 经验性求解器选择（solver_benchmark）会把 UMFPACK 作为候选之一，对大矩阵
// 实测选优。UMFPACK 需 BLAS（与 KLU 不同），故编译需 RFSIM_USE_UMFPACK +
// BLAS 库链接。
//
// 接口与 KluSolver/LuSolver 对齐（继承 LinearSolver）。CSR→CSC 转置在 factorize
// 内部做（UMFPACK 输入 CSC，与 KLU 同）。符号分解复用：连续 factorize 同结构
// 矩阵时复用 Symbolic，只重算 Numeric（UMFPACK 支持独立 symbolic/numeric 分离）。
#ifndef RFSIM_ASSEMBLY_UMFPACK_SOLVER_HPP
#define RFSIM_ASSEMBLY_UMFPACK_SOLVER_HPP

#include "linear_solver.hpp"
#include "matrix.hpp"
#include <cstdint>
#include <vector>

namespace rfsim {

class UmfpackSolver : public LinearSolver {
public:
    UmfpackSolver();
    ~UmfpackSolver();

    UmfpackSolver(const UmfpackSolver&) = delete;
    UmfpackSolver& operator=(const UmfpackSolver&) = delete;
    UmfpackSolver(UmfpackSolver&&) noexcept;
    UmfpackSolver& operator=(UmfpackSolver&&) noexcept;

    bool factorize(const SparseMatrix& A) override;
    void solve(const Vector& b, Vector& x) const override;

    [[nodiscard]] uint32_t dim() const noexcept override { return n_; }
    // UMFPACK 支持 symbolic/numeric 分离——连续同结构矩阵复用 Symbolic。
    [[nodiscard]] bool supportsRefactor() const override { return true; }
    [[nodiscard]] const char* name() const override { return "umfpack"; }

private:
    void freeFactors() noexcept;

    uint32_t n_ = 0;
    // CSC（int 索引；UMFPACK di 接口用 int32_t）
    std::vector<int32_t> Ap_;   // size n+1
    std::vector<int32_t> Ai_;   // size nnz
    std::vector<double>  Ax_;   // size nnz
    // 结构指纹（同 KluSolver：连续同结构复用 Symbolic）
    std::vector<int32_t> prevAp_;
    std::vector<int32_t> prevAi_;

    void* symbolic_ = nullptr;  // umfpack Symbolic 句柄
    void* numeric_  = nullptr;  // umfpack Numeric 句柄
    double control_[20];        // UMFPACK_CONTROL
    bool analyzed_ = false;
};

} // namespace rfsim

#endif // RFSIM_ASSEMBLY_UMFPACK_SOLVER_HPP
