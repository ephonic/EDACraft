// test_solver_selection.cpp — Phase A1-8: 线性求解器抽象 + 工厂 + 自动选择 单元测试
//
// 覆盖：
//   1. LinearSolver 接口：KluSolver / LuSolver / BiCgStabSolver 都能 factorize + solve 一个
//      小规模正定系统，且解与解析解吻合（容差内）。
//   2. 工厂 makeLinearSolver：4 种 SolverMethod 各返回正确的具体类型（name() 字符串）。
//   3. Auto 选择策略：小稠密矩阵 → DenseLu；稀疏矩阵 → Klu。
//   4. parseSolverMethod / solverMethodName 往返一致。
//   5. KLU refactor 复用：连续 factorize 同结构矩阵不重新 analyze（supportsRefactor=true），
//      且结果正确；结构变化时安全重新分析（A1-4 堆腐败修复的回归保护）。
#include "../src/assembly/linear_solver_factory.hpp"
#include "../src/assembly/lu_solver.hpp"
#include "../src/assembly/klu_solver.hpp"
#include "../src/assembly/iterative_solver.hpp"
#ifdef RFSIM_USE_UMFPACK
#include "../src/assembly/umfpack_solver.hpp"
#endif
#include <gtest/gtest.h>
#include <cmath>
#include <vector>

namespace {

// 构建一个 n×n 对角占优三对角矩阵（稀疏，对称，正定），装配到 SparseMatrix（CSR）。
// 对角=4，上下次对角=-1。b = A·x_true，x_true = [1,2,...,n]。
rfsim::SparseMatrix makeTridiag(uint32_t n, std::vector<double>& b) {
    rfsim::SparseMatrix A(n);
    b.assign(n, 0.0);
    std::vector<double> xtrue(n);
    for (uint32_t i = 0; i < n; ++i) xtrue[i] = static_cast<double>(i + 1);
    for (uint32_t i = 0; i < n; ++i) {
        A.addPattern(i, i); A.add(i, i, 4.0);
        if (i + 1 < n) { A.addPattern(i, i + 1); A.add(i, i + 1, -1.0); }
        if (i > 0)      { A.addPattern(i, i - 1); A.add(i, i - 1, -1.0); }
    }
    A.finalize();
    // b = A·xtrue
    for (uint32_t i = 0; i < n; ++i) {
        double s = 4.0 * xtrue[i];
        if (i + 1 < n) s -= 1.0 * xtrue[i + 1];
        if (i > 0)     s -= 1.0 * xtrue[i - 1];
        b[i] = s;
    }
    return A;
}

// 检查解 x 与 xtrue=[1..n] 的最大相对误差 < tol
double maxRelErr(const std::vector<double>& x, uint32_t n, double scale = 1.0) {
    double m = 0.0;
    for (uint32_t i = 0; i < n; ++i) {
        double truth = static_cast<double>(i + 1) * scale;
        double rel = std::fabs(x[i] - truth) / std::max(1.0, std::fabs(truth));
        m = std::max(m, rel);
    }
    return m;
}

} // namespace

// ===== 1. 各具体求解器求解三对角系统 =====

TEST(LinearSolverSelect, KluSolvesTridiag) {
    const uint32_t n = 20;
    std::vector<double> b;
    auto A = makeTridiag(n, b);
    rfsim::KluSolver solver;
    ASSERT_TRUE(solver.factorize(A));
    std::vector<double> x;
    solver.solve(b, x);
    EXPECT_EQ(x.size(), n);
    EXPECT_LT(maxRelErr(x, n), 1e-9);
    EXPECT_STREQ(solver.name(), "klu");
    EXPECT_TRUE(solver.supportsRefactor());
}

TEST(LinearSolverSelect, DenseLuSolvesTridiag) {
    const uint32_t n = 20;
    std::vector<double> b;
    auto A = makeTridiag(n, b);
    rfsim::LuSolver solver;
    ASSERT_TRUE(solver.factorize(A));
    std::vector<double> x;
    solver.solve(b, x);
    EXPECT_EQ(x.size(), n);
    EXPECT_LT(maxRelErr(x, n), 1e-9);
    EXPECT_STREQ(solver.name(), "dense-lu");
    EXPECT_FALSE(solver.supportsRefactor());
}

TEST(LinearSolverSelect, BiCgStabSolvesTridiag) {
    const uint32_t n = 20;
    std::vector<double> b;
    auto A = makeTridiag(n, b);
    rfsim::BiCgStabSolver solver;
    solver.setMaxIter(200);
    solver.setReltol(1e-10);
    ASSERT_TRUE(solver.factorize(A));
    std::vector<double> x(n, 0.0);
    solver.solve(b, x);
    EXPECT_TRUE(solver.lastConverged());
    EXPECT_LT(maxRelErr(x, n), 1e-6);
    EXPECT_STREQ(solver.name(), "bicgstab");
}

// ===== 2. 工厂按 SolverMethod 返回正确类型 =====

TEST(LinearSolverSelect, FactoryReturnsCorrectType) {
    using rfsim::SolverMethod;
    rfsim::SolverHints h{20, 60, false, 0.0};  // 小稀疏
    auto klu = rfsim::makeLinearSolver(SolverMethod::Klu, h);
    ASSERT_TRUE(klu);
    EXPECT_STREQ(klu->name(), "klu");

    auto dense = rfsim::makeLinearSolver(SolverMethod::DenseLu, h);
    ASSERT_TRUE(dense);
    EXPECT_STREQ(dense->name(), "dense-lu");

    auto iter = rfsim::makeLinearSolver(SolverMethod::BiCgStab, h);
    ASSERT_TRUE(iter);
    EXPECT_STREQ(iter->name(), "bicgstab");
}

// ===== 3. Auto 选择策略 =====

TEST(LinearSolverSelect, AutoPicksKluForSparse) {
    // 稀疏矩阵：dim=50, nnz≈150 → density≈0.06 → 选 KLU
    std::vector<double> b;
    auto A = makeTridiag(50, b);
    auto solver = rfsim::makeLinearSolver(rfsim::SolverMethod::Auto,
                                          rfsim::hintsFromMatrix(A));
    ASSERT_TRUE(solver);
#ifdef RFSIM_USE_KLU
    EXPECT_STREQ(solver->name(), "klu");
#else
    EXPECT_STREQ(solver->name(), "dense-lu");  // 无 KLU 时 Auto 回退
#endif
}

TEST(LinearSolverSelect, AutoPicksDenseForSmallDense) {
    // 小稠密矩阵：dim=10, 每对都有连接 → nnz=100 → density=1.0 → 选 DenseLu
    rfsim::SparseMatrix A(10);
    for (uint32_t i = 0; i < 10; ++i)
        for (uint32_t j = 0; j < 10; ++j) { A.addPattern(i, j); A.add(i, j, (i == j) ? 10.0 : 0.1); }
    A.finalize();
    auto solver = rfsim::makeLinearSolver(rfsim::SolverMethod::Auto,
                                          rfsim::hintsFromMatrix(A));
    ASSERT_TRUE(solver);
    EXPECT_STREQ(solver->name(), "dense-lu");
}

// ===== 4. parseSolverMethod / solverMethodName 往返 =====

TEST(LinearSolverSelect, MethodParseRoundTrip) {
    using rfsim::SolverMethod;
    struct Case { const char* in; SolverMethod expect; };
    Case cases[] = {
        {"auto", SolverMethod::Auto}, {"AUTO", SolverMethod::Auto}, {"", SolverMethod::Auto},
        {"klu", SolverMethod::Klu}, {"KLU", SolverMethod::Klu},
        {"dense", SolverMethod::DenseLu}, {"dense-lu", SolverMethod::DenseLu}, {"lu", SolverMethod::DenseLu},
        {"bicgstab", SolverMethod::BiCgStab}, {"iter", SolverMethod::BiCgStab},
    };
    for (const auto& c : cases) {
        std::string err;
        EXPECT_EQ(rfsim::parseSolverMethod(c.in, &err), c.expect)
            << "input='" << c.in << "'";
        EXPECT_TRUE(err.empty()) << "input='" << c.in << "' err=" << err;
    }
    // 未知名 → Auto + 错误信息
    std::string err;
    EXPECT_EQ(rfsim::parseSolverMethod("bogus", &err), SolverMethod::Auto);
    EXPECT_FALSE(err.empty());

    // name() 往返
    EXPECT_STREQ(rfsim::solverMethodName(SolverMethod::Auto), "auto");
    EXPECT_STREQ(rfsim::solverMethodName(SolverMethod::Klu), "klu");
    EXPECT_STREQ(rfsim::solverMethodName(SolverMethod::DenseLu), "dense-lu");
    EXPECT_STREQ(rfsim::solverMethodName(SolverMethod::BiCgStab), "bicgstab");
}

// ===== 5. KLU refactor 复用 + 结构变化安全重建（A1-4 堆腐败回归） =====

TEST(LinearSolverSelect, KluRefactorReuseSameStructure) {
    // 连续 factorize 同结构（不同值）矩阵：复用 sym_，结果正确。
    const uint32_t n = 15;
    std::vector<double> b1, b2;
    auto A1 = makeTridiag(n, b1);
    // 第二个矩阵：同结构，对角改为 5.0
    rfsim::SparseMatrix A2(n);
    std::vector<double> xtrue2(n);
    std::vector<double> b2gen(n, 0.0);
    for (uint32_t i = 0; i < n; ++i) xtrue2[i] = static_cast<double>(i + 1) * 2.0;
    for (uint32_t i = 0; i < n; ++i) {
        A2.addPattern(i, i); A2.add(i, i, 5.0);
        if (i + 1 < n) { A2.addPattern(i, i + 1); A2.add(i, i + 1, -1.0); }
        if (i > 0)      { A2.addPattern(i, i - 1); A2.add(i, i - 1, -1.0); }
    }
    A2.finalize();
    for (uint32_t i = 0; i < n; ++i) {
        double s = 5.0 * xtrue2[i];
        if (i + 1 < n) s -= 1.0 * xtrue2[i + 1];
        if (i > 0)     s -= 1.0 * xtrue2[i - 1];
        b2gen[i] = s;
    }

    rfsim::KluSolver solver;
    ASSERT_TRUE(solver.factorize(A1));
    std::vector<double> x1; solver.solve(b1, x1);
    EXPECT_LT(maxRelErr(x1, n), 1e-9);

    // 第二次：同结构、不同值 → 走 refactor，不重新 analyze
    ASSERT_TRUE(solver.factorize(A2));
    std::vector<double> x2; solver.solve(b2gen, x2);
    // xtrue2 = 2*[1..n]
    double m = 0.0;
    for (uint32_t i = 0; i < n; ++i)
        m = std::max(m, std::fabs(x2[i] - xtrue2[i]) / std::max(1.0, std::fabs(xtrue2[i])));
    EXPECT_LT(m, 1e-9);
}

TEST(LinearSolverSelect, KluReanalyzesOnStructureChange) {
    // 结构变化（n 变）时安全重新 analyze，不堆崩溃。这是 A1-4 修复的核心回归保护。
    std::vector<double> b1;
    auto A1 = makeTridiag(10, b1);
    std::vector<double> b2;
    auto A2 = makeTridiag(20, b2);  // 不同维度

    rfsim::KluSolver solver;
    ASSERT_TRUE(solver.factorize(A1));
    std::vector<double> x1; solver.solve(b1, x1);
    EXPECT_LT(maxRelErr(x1, 10), 1e-9);

    // 结构变化：n 10 → 20，必须重新 analyze 且不崩溃
    ASSERT_TRUE(solver.factorize(A2)) << "structure change must re-analyze cleanly";
    std::vector<double> x2; solver.solve(b2, x2);
    EXPECT_LT(maxRelErr(x2, 20), 1e-9);
}

// ===== 6. Auto 求解端到端（含 DenseLu 路径，原死代码现激活） =====

TEST(LinearSolverSelect, AutoSolveEndToEnd) {
    const uint32_t n = 30;
    std::vector<double> b;
    auto A = makeTridiag(n, b);
    auto solver = rfsim::makeAutoSolver(A);
    ASSERT_TRUE(solver);
    ASSERT_TRUE(solver->factorize(A));
    std::vector<double> x;
    solver->solve(b, x);
    EXPECT_LT(maxRelErr(x, n), 1e-9);
}

// ===== UMFPACK 求解器（RFSIM_USE_UMFPACK 编译时启用）=====
#ifdef RFSIM_USE_UMFPACK
TEST(LinearSolverSelect, UmfpackSolvesTridiag) {
    const uint32_t n = 20;
    std::vector<double> b;
    auto A = makeTridiag(n, b);
    rfsim::UmfpackSolver solver;
    ASSERT_TRUE(solver.factorize(A));
    std::vector<double> x;
    solver.solve(b, x);
    EXPECT_EQ(x.size(), n);
    EXPECT_LT(maxRelErr(x, n), 1e-9);
    EXPECT_STREQ(solver.name(), "umfpack");
    EXPECT_TRUE(solver.supportsRefactor());
}

TEST(LinearSolverSelect, UmfpackSymbolicReuseSameStructure) {
    // 连续 factorize 同结构矩阵：复用 Symbolic，结果正确。
    const uint32_t n = 15;
    std::vector<double> b1;
    auto A1 = makeTridiag(n, b1);
    rfsim::UmfpackSolver solver;
    ASSERT_TRUE(solver.factorize(A1));
    std::vector<double> x1; solver.solve(b1, x1);
    EXPECT_LT(maxRelErr(x1, n), 1e-9);

    // 第二次同结构不同值
    rfsim::SparseMatrix A2(n);
    std::vector<double> b2(n, 0.0);
    std::vector<double> xtrue2(n);
    for (uint32_t i = 0; i < n; ++i) xtrue2[i] = static_cast<double>(i + 1) * 2.0;
    for (uint32_t i = 0; i < n; ++i) {
        A2.addPattern(i, i); A2.add(i, i, 5.0);
        if (i + 1 < n) { A2.addPattern(i, i + 1); A2.add(i, i + 1, -1.0); }
        if (i > 0)      { A2.addPattern(i, i - 1); A2.add(i, i - 1, -1.0); }
    }
    A2.finalize();
    for (uint32_t i = 0; i < n; ++i) {
        double s = 5.0 * xtrue2[i];
        if (i + 1 < n) s -= 1.0 * xtrue2[i + 1];
        if (i > 0)     s -= 1.0 * xtrue2[i - 1];
        b2[i] = s;
    }
    ASSERT_TRUE(solver.factorize(A2)) << "same-structure refactor must succeed";
    std::vector<double> x2; solver.solve(b2, x2);
    double m = 0.0;
    for (uint32_t i = 0; i < n; ++i)
        m = std::max(m, std::fabs(x2[i] - xtrue2[i]) / std::max(1.0, std::fabs(xtrue2[i])));
    EXPECT_LT(m, 1e-9);
}
#endif  // RFSIM_USE_UMFPACK
