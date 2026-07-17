// solver_benchmark.hpp — 经验性求解器选择（empirical solver selection）
//
// 用户需求升级：不再仅靠静态规则（dim/稀疏度阈值）选求解器，而是对候选求解器
// 实际跑 N 次（默认 10）factorize+solve 基准，选最快的用于后续求解。
//
// 触发策略（用户决策）：
//   - dim > kEmpiricalThreshold（默认 100000）的大矩阵 → 触发经验基准
//   - 小稀疏矩阵 → 默认 KLU（不基准，开销不值得）
//   - Auto 路径：先静态规则选默认，大矩阵再覆盖为经验选择结果
//
// 持久化：按矩阵指纹（dim + nnz + 结构哈希）缓存最优求解器类型，本会话内同结构
// 矩阵直接复用最优选择，不重复基准。开销摊到首步。
//
// 插件式架构：候选池通过 registerSolverFactory 动态注册（KLU/DenseLu/BiCGSTAB
// 默认注册；UMFPACK/PARDISO/MUMPS/SuperLU 等外部求解器按编译/运行时可用性注册）。
#ifndef RFSIM_ASSEMBLY_SOLVER_BENCHMARK_HPP
#define RFSIM_ASSEMBLY_SOLVER_BENCHMARK_HPP

#include "linear_solver.hpp"
#include "linear_solver_factory.hpp"
#include "../util/bench.hpp"
#include <cstdint>
#include <functional>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

namespace rfsim {

// 经验基准触发阈值（dim > 此值才基准）。用户指定 10万。
constexpr uint32_t kEmpiricalThreshold = 100000;

// 基准跑的次数（factorize+solve 重复 N 次，取中位数/最小值）。
// 默认 10（用户举例）。对小矩阵这开销可忽略；对大矩阵是必要投资。
constexpr uint32_t kBenchmarkRuns = 10;

// 候选求解器工厂：返回一个新构造的求解器实例。
using SolverFactory = std::function<std::unique_ptr<LinearSolver>()>;

// 候选注册：name + factory + 是否当前编译可用。
// 默认 KLU/DenseLu/BiCGSTAB 始终注册（KLU 视 RFSIM_USE_KLU）。
// UMFPACK/PARDISO/MUMPS/SuperLU 等外部求解器在各自 wrapper 初始化时注册。
struct SolverCandidate {
    std::string name;
    SolverFactory factory;
    bool available = true;
};

// 单次基准结果
struct BenchResult {
    std::string name;
    double factorMs = 0.0;   // factorize 中位数耗时（ms）
    double solveMs = 0.0;    // solve 中位数耗时（ms）
    double totalMs = 0.0;    // factor+solve 中位数（选优依据）
    bool ok = false;         // 是否成功（factorize 未奇异）
};

// 候选池管理 + 经验基准 + 缓存。
class EmpiricalSolverSelector {
public:
    static EmpiricalSolverSelector& instance();

    // 注册候选求解器。重复 name 覆盖。默认构造时已注册内置候选。
    void registerCandidate(const std::string& name, SolverFactory factory);
    // 标记某候选不可用（如 UMFPACK 编译但运行时加载失败）。
    void setUnavailable(const std::string& name);

    // 对给定矩阵跑所有可用候选的基准，返回各候选结果（按 totalMs 升序）。
    // 每个 candidate 做 runs 次 factorize+solve，取中位数。
    // 注意：会消耗 candidates 的求解器实例（factorize 有副作用）；每次新构造实例。
    std::vector<BenchResult> benchmark(const SparseMatrix& A,
                                       uint32_t runs = kBenchmarkRuns) const;

    // 经验选择：若 dim > threshold 则基准并返回最优求解器；否则返回 nullptr
    // （调用方回退静态规则）。结果按指纹缓存。
    // 返回的 unique_ptr 是新构造的最优求解器实例（已 factorize 过的会被丢弃——
    // 调用方拿到的是干净实例，需自行 factorize）。
    std::unique_ptr<LinearSolver> select(const SparseMatrix& A,
                                         const SolverHints& hints,
                                         uint32_t threshold = kEmpiricalThreshold);

    // 强制对某矩阵重新基准（清缓存）。下次 select 会重跑。
    void invalidate(const SparseMatrix& A);

    // 是否启用经验基准（可通过 RFSIM_EMPIRICAL_SOLVER=1 强制开，或 dim>阈值自动）。
    static bool enabledForDim(uint32_t dim);

    // 设置阈值（默认 kEmpiricalThreshold）。0 表示禁用经验选择。
    void setThreshold(uint32_t t) { threshold_ = t; }
    [[nodiscard]] uint32_t threshold() const { return threshold_; }

    // 缓存查询：返回指纹对应的最优候选名（空表示未缓存/未基准）。
    [[nodiscard]] std::string cachedWinner(uint64_t fingerprint) const;
    // 清所有缓存。
    void clearCache();

    // 矩阵指纹：dim + nnz + 结构 hash（rowPtr/colIdx 的 FNV-1a）。
    // 同结构矩阵指纹相同（值不同不影响），用于缓存复用。
    static uint64_t matrixFingerprint(const SparseMatrix& A);

private:
    EmpiricalSolverSelector();
    std::vector<SolverCandidate> candidates_;
    uint32_t threshold_ = kEmpiricalThreshold;
    // 指纹 → 最优候选名
    std::unordered_map<uint64_t, std::string> cache_;
};

// 便捷：对矩阵做一次经验选择，返回新构造的最优求解器。
// dim ≤ threshold 或经验选择禁用时返回 nullptr（调用方用静态规则）。
inline std::unique_ptr<LinearSolver> selectEmpirically(const SparseMatrix& A,
                                                       const SolverHints& hints) {
    return EmpiricalSolverSelector::instance().select(A, hints);
}

} // namespace rfsim

#endif // RFSIM_ASSEMBLY_SOLVER_BENCHMARK_HPP
