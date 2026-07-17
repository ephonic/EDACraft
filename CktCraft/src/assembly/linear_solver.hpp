// linear_solver.hpp — 线性求解器抽象接口
//
// Phase A1：统一 KluSolver / LuSolver / 迭代求解器到一个抽象基类，
// 使求解层（dc_op / shooting / time_stepper / hb_nonlinear）可以：
//   1. 通过基类指针多态分发（自动选择 KLU vs DenseLu vs 迭代）
//   2. 把求解器对象的构造提到 Newton 循环外，激活符号分解复用 + refactor
//      （KluSolver 内已有的 analyzed_/klu_refactor 路径，原本因每轮循环
//       重新构造对象而完全失效——死代码）。
//
// 设计说明：
//   - 接口与现有 KluSolver / LuSolver 的方法签名字节级对齐
//     （factorize(SparseMatrix) + solve(Vector,Vector) + dim()），
//     两者只需加 override 即可适配，无 API churn。
//   - KluZSolver（复数 + in-place solve + raw CSC 指针）API 不兼容，
//     暂不纳入本接口——AC 分析仍直接用 KluZSolver；未来可引入
//     ComplexLinearSolver 接口。
//   - factorize() 语义：对支持 refactor 的求解器（KLU），连续调用同结构
//     矩阵时复用符号分解、只做数值 refactor；结构变化时自动重新 analyze。
//
// 详见 plan（Phase A1）。
#ifndef RFSIM_ASSEMBLY_LINEAR_SOLVER_HPP
#define RFSIM_ASSEMBLY_LINEAR_SOLVER_HPP

#include "matrix.hpp"
#include <cstdint>

namespace rfsim {

// 线性求解器抽象基类：求解 A·x = b（A 为 SparseMatrix）。
class LinearSolver {
public:
    virtual ~LinearSolver() = default;

    // 分解矩阵 A。对支持 refactor 的求解器（KLU），连续调用同结构矩阵时
    // 复用符号分解，仅做数值 refactor；返回 false 若矩阵奇异或分析失败。
    virtual bool factorize(const SparseMatrix& A) = 0;

    // 求解 A·x = b（需先 factorize 成功）。x 为输出。
    virtual void solve(const Vector& b, Vector& x) const = 0;

    // 矩阵维度（factorize 后有效）。
    [[nodiscard]] virtual uint32_t dim() const = 0;

    // bench 计时（仅 RFSIM_BENCH_JSON=1 时累加；默认 0）。
    [[nodiscard]] virtual double factorMs() const { return 0.0; }
    [[nodiscard]] virtual double solveMs()  const { return 0.0; }

    // 是否支持符号分解复用 + 数值 refactor（连续 factorize 同结构矩阵时省 analyze）。
    // KLU=true；DenseLu=false（每次都全分解，但稠密无 analyze 开销）。
    [[nodiscard]] virtual bool supportsRefactor() const { return false; }

    // 求解器名（用于诊断输出："klu" / "dense-lu" / "bicgstab"）。
    [[nodiscard]] virtual const char* name() const = 0;
};

} // namespace rfsim

#endif // RFSIM_ASSEMBLY_LINEAR_SOLVER_HPP
