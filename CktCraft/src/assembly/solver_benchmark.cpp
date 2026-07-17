// solver_benchmark.cpp — 经验性求解器选择实现
//
// 详见 solver_benchmark.hpp。用户需求：对大矩阵（dim>10万）跑 N 次基准选最快求解器。
#include "solver_benchmark.hpp"
#include "lu_solver.hpp"
#include "iterative_solver.hpp"

#ifdef RFSIM_USE_KLU
#include "klu_solver.hpp"
#endif
#ifdef RFSIM_USE_UMFPACK
#include "umfpack_solver.hpp"
#endif

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>

namespace rfsim {

namespace {

// 取一个 double 序列的中位数（输入会被排序）。
double median(std::vector<double>& v) {
    if (v.empty()) return 0.0;
    std::sort(v.begin(), v.end());
    size_t n = v.size();
    return (n % 2 == 1) ? v[n / 2] : 0.5 * (v[n / 2 - 1] + v[n / 2]);
}

} // namespace

EmpiricalSolverSelector::EmpiricalSolverSelector() {
    // 默认注册内置候选。
#ifdef RFSIM_USE_KLU
    candidates_.push_back({"klu", []() -> std::unique_ptr<LinearSolver> {
        return std::make_unique<KluSolver>();
    }, true});
#endif
#ifdef RFSIM_USE_UMFPACK
    candidates_.push_back({"umfpack", []() -> std::unique_ptr<LinearSolver> {
        return std::make_unique<UmfpackSolver>();
    }, true});
#endif
    candidates_.push_back({"dense-lu", []() -> std::unique_ptr<LinearSolver> {
        return std::make_unique<LuSolver>();
    }, true});
    candidates_.push_back({"bicgstab", []() -> std::unique_ptr<LinearSolver> {
        return std::make_unique<BiCgStabSolver>();
    }, true});
    // 其他外部求解器（PARDISO/MUMPS/SuperLU）由各自 wrapper 的初始化函数
    // 调 registerCandidate 注入。未注入则不在候选池。
}

EmpiricalSolverSelector& EmpiricalSolverSelector::instance() {
    static EmpiricalSolverSelector inst;
    return inst;
}

void EmpiricalSolverSelector::registerCandidate(const std::string& name, SolverFactory factory) {
    for (auto& c : candidates_) {
        if (c.name == name) { c.factory = std::move(factory); c.available = true; return; }
    }
    candidates_.push_back({name, std::move(factory), true});
}

void EmpiricalSolverSelector::setUnavailable(const std::string& name) {
    for (auto& c : candidates_) {
        if (c.name == name) c.available = false;
    }
}

std::vector<BenchResult> EmpiricalSolverSelector::benchmark(const SparseMatrix& A,
                                                              uint32_t runs) const {
    std::vector<BenchResult> results;
    if (!A.finalized()) return results;
    const uint32_t n = A.dim();
    // 构造一个确定性 RHS（全 1）和初始 x（全 0）
    Vector b(n, 1.0);
    Vector x(n, 0.0);
    for (const auto& cand : candidates_) {
        if (!cand.available) continue;
        BenchResult r;
        r.name = cand.name;
        std::vector<double> factTimes, solveTimes;
        factTimes.reserve(runs);
        solveTimes.reserve(runs);
        bool anyFail = false;
        for (uint32_t k = 0; k < runs; ++k) {
            auto solver = cand.factory();
            if (!solver) { anyFail = true; break; }
            SteadyTimer tf;
            bool ok = solver->factorize(A);
            double fm = tf.elapsedMs();
            if (!ok) { anyFail = true; break; }
            factTimes.push_back(fm);
            SteadyTimer ts;
            std::fill(x.begin(), x.end(), 0.0);
            solver->solve(b, x);
            solveTimes.push_back(ts.elapsedMs());
        }
        if (anyFail || factTimes.empty()) { r.ok = false; results.push_back(r); continue; }
        r.ok = true;
        r.factorMs = median(factTimes);
        r.solveMs = median(solveTimes);
        r.totalMs = r.factorMs + r.solveMs;
        results.push_back(r);
    }
    // 按 totalMs 升序（成功的在前，失败的在后）
    std::sort(results.begin(), results.end(), [](const BenchResult& a, const BenchResult& b) {
        if (a.ok != b.ok) return a.ok;            // 成功的优先
        return a.totalMs < b.totalMs;
    });
    return results;
}

bool EmpiricalSolverSelector::enabledForDim(uint32_t dim) {
    // RFSIM_EMPIRICAL_SOLVER=1 强制启用；否则按阈值。
    static int force = []() {
        const char* s = std::getenv("RFSIM_EMPIRICAL_SOLVER");
        return (s && (s[0] == '1' || s[0] == 't' || s[0] == 'T')) ? 1 : 0;
    }();
    if (force) return true;
    return dim > kEmpiricalThreshold;
}

uint64_t EmpiricalSolverSelector::matrixFingerprint(const SparseMatrix& A) {
    // FNV-1a 64-bit over dim + rowPtr + colIdx（不含值——同结构同指纹）。
    const auto& rp = A.rowPtr();
    const auto& ci = A.colIdx();
    uint64_t h = 1469598103934665603ULL;  // FNV offset basis
    auto mix = [&](uint64_t v) {
        h ^= v;
        h *= 1099511628211ULL;  // FNV prime
    };
    mix(static_cast<uint64_t>(A.dim()));
    mix(static_cast<uint64_t>(rp.size()));
    for (uint32_t v : rp) mix(v);
    for (uint32_t v : ci) mix(v);
    return h;
}

std::unique_ptr<LinearSolver> EmpiricalSolverSelector::select(const SparseMatrix& A,
                                                               const SolverHints& hints,
                                                               uint32_t threshold) {
    (void)hints;
    const uint32_t dim = A.dim();
    if (dim == 0) return nullptr;
    // 触发条件：threshold==0 禁用；否则 dim > threshold 或环境变量强制启用。
    // threshold 参数显式传入时优先用它（调用方可设小值强制触发，用于测试/调试）。
    bool shouldBench;
    if (threshold == 0) {
        shouldBench = false;
    } else if (threshold < kEmpiricalThreshold) {
        // 调用方主动设了小阈值（如测试用 threshold=1）→ 强制触发
        shouldBench = true;
    } else {
        shouldBench = (dim > threshold) || enabledForDim(dim);
    }
    if (!shouldBench) return nullptr;

    const uint64_t fp = matrixFingerprint(A);
    auto it = cache_.find(fp);
    if (it != cache_.end()) {
        // 缓存命中：用上次的最优候选构造新实例
        const std::string& winner = it->second;
        for (const auto& cand : candidates_) {
            if (cand.available && cand.name == winner) return cand.factory();
        }
        // 缓存的候选已不可用，落穿重新基准
    }

    // 跑基准
    auto results = benchmark(A, kBenchmarkRuns);
    if (results.empty() || !results.front().ok) return nullptr;
    const std::string& winner = results.front().name;
    cache_[fp] = winner;
    // 返回新构造的最优实例（调用方自行 factorize）
    for (const auto& cand : candidates_) {
        if (cand.available && cand.name == winner) return cand.factory();
    }
    return nullptr;
}

void EmpiricalSolverSelector::invalidate(const SparseMatrix& A) {
    cache_.erase(matrixFingerprint(A));
}

std::string EmpiricalSolverSelector::cachedWinner(uint64_t fingerprint) const {
    auto it = cache_.find(fingerprint);
    return it != cache_.end() ? it->second : std::string();
}

void EmpiricalSolverSelector::clearCache() {
    cache_.clear();
}

} // namespace rfsim
