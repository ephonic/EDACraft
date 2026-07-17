// test_solver_benchmark.cpp — 经验性求解器选择（empirical solver selection）单元测试
//
// 用户需求升级：对候选求解器各跑 N 次 factorize+solve，选最快的。
// 覆盖：
//   - 候选池注册（默认 KLU/DenseLu/BiCGSTAB）
//   - benchmark 跑所有候选、按 totalMs 排序、返回结果
//   - 矩阵指纹（同结构同指纹）
//   - 小矩阵（dim<阈值）默认不触发经验选择；RFSIM_EMPIRICAL_SOLVER=1 强制启用
//   - 缓存命中（同指纹第二次 select 不重复基准）
#include "../src/assembly/solver_benchmark.hpp"
#include "../src/assembly/linear_solver_factory.hpp"
#include "../src/assembly/lu_solver.hpp"
#include <gtest/gtest.h>
#include <cstdlib>
#include <vector>

namespace {
// 三对角正定矩阵（与 test_solver_selection 同款构造）
rfsim::SparseMatrix makeTridiag(uint32_t n) {
    rfsim::SparseMatrix A(n);
    for (uint32_t i = 0; i < n; ++i) {
        A.addPattern(i, i); A.add(i, i, 4.0);
        if (i + 1 < n) { A.addPattern(i, i + 1); A.add(i, i + 1, -1.0); }
        if (i > 0)      { A.addPattern(i, i - 1); A.add(i, i - 1, -1.0); }
    }
    A.finalize();
    return A;
}
} // namespace

TEST(EmpiricalSolverSelect, DefaultCandidatesRegistered) {
    // 候选池应至少含 dense-lu（KLU 视编译，bicgstab 视编译）。
    auto& sel = rfsim::EmpiricalSolverSelector::instance();
    // benchmark 一个小矩阵，检查返回结果非空
    auto A = makeTridiag(10);
    auto results = sel.benchmark(A, 3);
    EXPECT_FALSE(results.empty());
    // 至少有 dense-lu 成功
    bool hasDense = false;
    for (const auto& r : results) if (r.name == "dense-lu" && r.ok) hasDense = true;
    EXPECT_TRUE(hasDense);
}

TEST(EmpiricalSolverSelect, BenchmarkReturnsSortedByTotalMs) {
    auto& sel = rfsim::EmpiricalSolverSelector::instance();
    auto A = makeTridiag(20);
    auto results = sel.benchmark(A, 3);
    ASSERT_FALSE(results.empty());
    // 成功的应在前，且按 totalMs 升序
    for (size_t k = 1; k < results.size(); ++k) {
        if (results[k - 1].ok && results[k].ok) {
            EXPECT_LE(results[k - 1].totalMs, results[k].totalMs + 1e-9);
        }
    }
    // 第一个（最优）应是 ok
    EXPECT_TRUE(results.front().ok);
}

TEST(EmpiricalSolverSelect, MatrixFingerprintSameStructure) {
    auto A1 = makeTridiag(15);
    auto A2 = makeTridiag(15);  // 同结构
    // 改 A2 的值（同结构不同值）
    A2.zeroValues();
    for (uint32_t i = 0; i < 15; ++i) A2.add(i, i, 5.0);
    auto A3 = makeTridiag(20);  // 不同结构（dim 不同）
    EXPECT_EQ(rfsim::EmpiricalSolverSelector::matrixFingerprint(A1),
              rfsim::EmpiricalSolverSelector::matrixFingerprint(A2));
    EXPECT_NE(rfsim::EmpiricalSolverSelector::matrixFingerprint(A1),
              rfsim::EmpiricalSolverSelector::matrixFingerprint(A3));
}

TEST(EmpiricalSolverSelect, SmallMatrixSkipsEmpiricalByDefault) {
    // dim=50 < 100000 阈值 → enabledForDim=false（除非 RFSIM_EMPIRICAL_SOLVER=1）
    // 注意：若 CI 设了 RFSIM_EMPIRICAL_SOLVER=1，此断言会翻转——用 unset 保护。
    // 这里测默认（未设环境变量）行为。
    bool forced = std::getenv("RFSIM_EMPIRICAL_SOLVER") != nullptr;
    if (forced) GTEST_SKIP() << "RFSIM_EMPIRICAL_SOLVER set, skip default-behavior test";
    EXPECT_FALSE(rfsim::EmpiricalSolverSelector::enabledForDim(50));
    EXPECT_FALSE(rfsim::EmpiricalSolverSelector::enabledForDim(99999));
    EXPECT_TRUE(rfsim::EmpiricalSolverSelector::enabledForDim(100001));  // > 10万
}

TEST(EmpiricalSolverSelect, SelectReturnsNullptrForSmallByDefault) {
    bool forced = std::getenv("RFSIM_EMPIRICAL_SOLVER") != nullptr;
    if (forced) GTEST_SKIP() << "RFSIM_EMPIRICAL_SOLVER set";
    auto& sel = rfsim::EmpiricalSolverSelector::instance();
    auto A = makeTridiag(30);
    auto solver = sel.select(A, rfsim::hintsFromMatrix(A));
    EXPECT_EQ(solver.get(), nullptr);  // 小矩阵不基准 → 返回空，调用方走静态规则
}

TEST(EmpiricalSolverSelect, ForcedEmpiricalSelectsAndCaches) {
    // 强制启用经验选择（设环境变量），验证 select 返回非空 + 缓存。
    // 注意：环境变量在程序启动时读（enabledForDim 内 static），测试进程内修改无效。
    // 故此用例仅在 RFSIM_EMPIRICAL_SOLVER=1 环境下有意义；否则 select 返回 nullptr。
    auto& sel = rfsim::EmpiricalSolverSelector::instance();
    auto A = makeTridiag(25);
    uint64_t fp = rfsim::EmpiricalSolverSelector::matrixFingerprint(A);
    sel.clearCache();  // 确保干净
    // 直接调 benchmark 验证机制（不依赖环境变量）
    auto results = sel.benchmark(A, 5);
    ASSERT_FALSE(results.empty());
    ASSERT_TRUE(results.front().ok);
    const std::string& winner = results.front().name;
    EXPECT_FALSE(winner.empty());
    // select 用阈值=1 强制触发（绕过 enabledForDim 的环境变量依赖）
    sel.clearCache();  // 再次清，确保 select 内部跑基准填缓存
    auto solver = sel.select(A, rfsim::hintsFromMatrix(A), /*threshold=*/1);
    ASSERT_TRUE(solver != nullptr) << "select(threshold=1) should force benchmark";
    // 缓存应有 winner
    std::string cached = sel.cachedWinner(fp);
    EXPECT_FALSE(cached.empty());
    // 第二次 select 同矩阵 → 缓存命中（不重复基准），仍返回实例
    auto solver2 = sel.select(A, rfsim::hintsFromMatrix(A), /*threshold=*/1);
    EXPECT_TRUE(solver2 != nullptr);
    sel.clearCache();  // 清理，避免影响后续测试
}

TEST(EmpiricalSolverSelect, InvalidateClearsCache) {
    auto& sel = rfsim::EmpiricalSolverSelector::instance();
    auto A = makeTridiag(12);
    sel.select(A, rfsim::hintsFromMatrix(A), /*threshold=*/1);
    uint64_t fp = rfsim::EmpiricalSolverSelector::matrixFingerprint(A);
    EXPECT_FALSE(sel.cachedWinner(fp).empty());
    sel.invalidate(A);
    EXPECT_TRUE(sel.cachedWinner(fp).empty());
}

TEST(EmpiricalSolverSelect, MakeAutoSolverUsesEmpiricalWhenForced) {
    // makeAutoSolver(A) 在 dim>阈值 或 RFSIM_EMPIRICAL_SOLVER=1 时走经验选择。
    // 用阈值=1 直接调 select 模拟大矩阵行为。
    auto& sel = rfsim::EmpiricalSolverSelector::instance();
    auto A = makeTridiag(15);
    sel.clearCache();
    auto solver = sel.select(A, rfsim::hintsFromMatrix(A), /*threshold=*/1);
    ASSERT_TRUE(solver != nullptr);
    // 求解器应能正常 factorize + solve
    ASSERT_TRUE(solver->factorize(A));
    rfsim::Vector b(15, 1.0), x;
    solver->solve(b, x);
    EXPECT_EQ(x.size(), 15u);
}

TEST(EmpiricalSolverSelect, RegisterCustomCandidate) {
    // 验证插件式注册：注册一个自定义候选，benchmark 应包含它。
    auto& sel = rfsim::EmpiricalSolverSelector::instance();
    sel.registerCandidate("custom-dense", []() -> std::unique_ptr<rfsim::LinearSolver> {
        auto p = std::make_unique<rfsim::LuSolver>();
        return p;
    });
    auto A = makeTridiag(8);
    auto results = sel.benchmark(A, 2);
    bool hasCustom = false;
    for (const auto& r : results) if (r.name == "custom-dense") hasCustom = true;
    EXPECT_TRUE(hasCustom);
    sel.setUnavailable("custom-dense");
    auto results2 = sel.benchmark(A, 2);
    for (const auto& r : results2) EXPECT_NE(r.name, "custom-dense");
}
