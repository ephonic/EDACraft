// gmres.hpp - 右预条件 GMRES(m) 求解器
//
// 求解 A x = b，其中 A 是 LinearOperator，M 是右预条件器。
// 采用 restarted GMRES：每 m 步构造 Krylov 子空间并更新解。
#ifndef RFSIM_ASSEMBLY_GMRES_HPP
#define RFSIM_ASSEMBLY_GMRES_HPP

#include <cstdint>
#include <vector>

namespace rfsim {

// 抽象线性算子 y = A x
class LinearOperator {
public:
    virtual ~LinearOperator() = default;
    // 计算 y = A * x。x 与 y 长度均为 dim。
    virtual void apply(const std::vector<double>& x, std::vector<double>& y) const = 0;
    virtual uint32_t dim() const noexcept = 0;
};

// 抽象预条件器 z = M^{-1} r（右预条件）
class Preconditioner {
public:
    virtual ~Preconditioner() = default;
    // 计算 z = M^{-1} * r。r 与 z 长度均为 dim。
    virtual void apply(const std::vector<double>& r, std::vector<double>& z) const = 0;
    virtual uint32_t dim() const noexcept = 0;
};

struct GmresOptions {
    uint32_t restart = 30;      // 重启步数 m
    uint32_t maxIter = 1000;    // 最大总迭代次数
    double reltol = 1e-6;       // 相对收敛容差
    double abstol = 1e-12;      // 绝对收敛容差
};

struct GmresResult {
    bool converged = false;
    uint32_t iterations = 0;    // 总 Arnoldi 步数
    double residual = 0.0;      // 最终残差范数 ||b - A x||
};

// 右预条件 GMRES(m)
//   A: 线性算子
//   M: 右预条件器（可为 nullptr，表示单位预条件）
//   b: 右端项
//   x: 初始猜测（输入）/ 解（输出）
GmresResult solveGmres(const LinearOperator& A, const Preconditioner* M,
                       const std::vector<double>& b, std::vector<double>& x,
                       const GmresOptions& opts = {});

} // namespace rfsim

#endif // RFSIM_ASSEMBLY_GMRES_HPP
