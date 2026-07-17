// linear_solver_factory.hpp — 线性求解器工厂与自动选择
//
// Phase A1：提供统一的 makeLinearSolver() 入口，按 SolverMethod + SolverHints
// 构造 LinearSolver 子类。求解层（dc_op / shooting / time_stepper / hb_nonlinear）
// 通过基类指针持有，不再直接 new KluSolver——从而：
//   1. 支持多态（Auto 策略按规模/稀疏度选 KLU / DenseLu / 迭代）
//   2. 把对象构造提到 Newton 循环外，激活 KLU 符号分解复用 + refactor
//
// 选择策略（Auto）：
//   - dim < kDenseThreshold (默认 64) 且稠密度高 → DenseLu（无 analyze 开销，
//     稠密 LU 对小矩阵常数因子小）
//   - 否则 KLU（若编译启用 RFSIM_USE_KLU）——电路型稀疏不对称矩阵接近最优
//   - 无 KLU 编译时 → Auto 回退到 DenseLu（保可移植性）
//   - 显式 BiCgStab 走迭代求解器（BiCGSTAB + ILU(0) 预条件）
//
// SolverHints 在 Auto 选择时由调用方从 SparseMatrix 提取（dim + nnz）。
// 详见 plan（Phase A1 步骤 2/3）。
#ifndef RFSIM_ASSEMBLY_LINEAR_SOLVER_FACTORY_HPP
#define RFSIM_ASSEMBLY_LINEAR_SOLVER_FACTORY_HPP

#include "linear_solver.hpp"
#include "matrix.hpp"
#include <memory>
#include <string>

namespace rfsim {

// 求解方法枚举。从 .options method=<name> 解析或程序化设置。
enum class SolverMethod {
    Auto,     // 按规模/稀疏度自动选（默认）；大矩阵触发经验基准
    Klu,      // SuiteSparse KLU 稀疏直接（需 RFSIM_USE_KLU）
    Umfpack,  // SuiteSparse UMFPACK 多列前沿（需 RFSIM_USE_UMFPACK + BLAS）
    DenseLu,  // 稠密部分选主元 LU
    BiCgStab  // BiCGSTAB + ILU(0) 迭代
};

// 自动选择的输入提示（dim/nnz 从 SparseMatrix 提取）。
struct SolverHints {
    uint32_t dim = 0;
    uint32_t nnz = 0;          // 非零元数；稀疏度 = nnz / dim²
    bool symmetric = false;    // 矩阵是否对称（影响迭代求解器选择）
    // 上次 factorize 的 fill-in 估计（可选，供 Auto 调整；0 表示未知）
    double fillEstimate = 0.0;
};

// 从字符串解析 SolverMethod（".options method=klu" 等用）。
// 未知名返回 Auto 并（若 err != nullptr）写入提示。
SolverMethod parseSolverMethod(const std::string& name, std::string* err = nullptr);

// 反向：SolverMethod → 字符串名。
const char* solverMethodName(SolverMethod m);

// 从 SparseMatrix 提取 SolverHints（dim + nnz）。要求 A 已 finalize。
// 用于 Auto 选择；未 finalize 时 nnz=0（Auto 走规模兜底）。
SolverHints hintsFromMatrix(const SparseMatrix& A);

// 构造求解器。
//   method=Auto：按 hints 选择；m 显式指定时直接构造对应子类。
//   KLU 不可用时：method==Klu 与 method==Auto 都回退到 DenseLu。
// 失败返回 nullptr（如 KLU 不可用且 method==Klu 被显式请求——但此处选择回退
// 而非返回空，调用方据此能在 verbose 模式提示）。
std::unique_ptr<LinearSolver> makeLinearSolver(SolverMethod method,
                                               const SolverHints& hints);

// 便捷重载：直接从矩阵构造 Auto 求解器。
// 升级（用户需求）：大矩阵（dim > kEmpiricalThreshold，默认 10万）触发经验基准——
// 对候选求解器各跑 N 次 factorize+solve，选最快的（结果按指纹缓存）。
// 小矩阵用静态规则（默认 KLU）。
std::unique_ptr<LinearSolver> makeAutoSolver(const SparseMatrix& A);

} // namespace rfsim

#endif // RFSIM_ASSEMBLY_LINEAR_SOLVER_FACTORY_HPP
