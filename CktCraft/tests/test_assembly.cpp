// test_assembly.cpp - assembly and solver tests
#include "assembly/matrix.hpp"
#include "assembly/lu_solver.hpp"
#include "assembly/mna.hpp"
#include "solver/dc_op.hpp"
#include "model/builtin_devices.hpp"
#include <gtest/gtest.h>
using namespace rfsim;

TEST(Assembly, SparseMatrixAddGet) {
    SparseMatrix A(3);
    A.add(0,0,2.0); A.add(1,1,3.0); A.add(0,1,-1.0);
    EXPECT_DOUBLE_EQ(A.get(0,0), 2.0);
    A.finalize();
    EXPECT_DOUBLE_EQ(A.get(0,0), 2.0);
}
TEST(Assembly, LuSolve2x2) {
    SparseMatrix A(2);
    A.add(0,0,2); A.add(0,1,1); A.add(1,0,1); A.add(1,1,3);
    A.finalize();
    LuSolver s; ASSERT_TRUE(s.factorize(A));
    Vector x; s.solve({5,10}, x);
    EXPECT_NEAR(x[0], 1.0, 1e-12); EXPECT_NEAR(x[1], 3.0, 1e-12);
}
TEST(Assembly, LuSolveSingular) {
    SparseMatrix A(2);
    A.add(0,0,1); A.add(0,1,1); A.add(1,0,1); A.add(1,1,1);
    A.finalize();
    LuSolver s; EXPECT_FALSE(s.factorize(A));
}
TEST(DcOp, VoltageDivider) {
    std::vector<std::unique_ptr<DeviceModel>> devs;
    devs.push_back(std::make_unique<VoltageSource>("v1", 1, 0, 10.0));
    devs.push_back(std::make_unique<Resistor>("r1", 1, 2, 2000.0));
    devs.push_back(std::make_unique<Resistor>("r2", 2, 0, 3000.0));
    auto r = solveDcOp(2, devs);
    ASSERT_TRUE(r.converged);
    EXPECT_NEAR(r.nodeVoltages[1], 10.0, 1e-6);
    EXPECT_NEAR(r.nodeVoltages[2], 6.0, 1e-6);
    EXPECT_NEAR(r.branchCurrents[0], 2e-3, 1e-6);
}
TEST(DcOp, CurrentSourceResistor) {
    std::vector<std::unique_ptr<DeviceModel>> devs;
    devs.push_back(std::make_unique<CurrentSource>("i1", 1, 0, 1e-3));
    devs.push_back(std::make_unique<Resistor>("r1", 1, 0, 1000.0));
    auto r = solveDcOp(1, devs);
    ASSERT_TRUE(r.converged);
    EXPECT_NEAR(r.nodeVoltages[1], 1.0, 1e-6);
}
TEST(DcOp, TwoSourcesResistor) {
    std::vector<std::unique_ptr<DeviceModel>> devs;
    devs.push_back(std::make_unique<VoltageSource>("v1", 1, 0, 5.0));
    devs.push_back(std::make_unique<VoltageSource>("v2", 2, 0, 3.0));
    devs.push_back(std::make_unique<Resistor>("r1", 1, 2, 1000.0));
    auto r = solveDcOp(2, devs);
    ASSERT_TRUE(r.converged);
    EXPECT_NEAR(r.nodeVoltages[1], 5.0, 1e-6);
    EXPECT_NEAR(r.nodeVoltages[2], 3.0, 1e-6);
}

// L8: V3 fast path 单元测试——commitPattern + zeroCommitted + addCommitted + ptrFor
TEST(Assembly, SparseMatrixCommitPattern) {
    SparseMatrix G;
    G.resize(3);
    // 建 pattern
    G.addPattern(0, 0); G.addPattern(0, 1);
    G.addPattern(1, 0); G.addPattern(1, 1); G.addPattern(1, 2);
    G.addPattern(2, 1); G.addPattern(2, 2);
    G.add(0, 0, 1.0); G.add(0, 1, 2.0);
    G.add(1, 0, 3.0); G.add(1, 1, 4.0); G.add(1, 2, 5.0);
    G.add(2, 1, 6.0); G.add(2, 2, 7.0);
    G.finalize();
    ASSERT_TRUE(G.finalized());

    // 快照原始值
    auto orig = G.values();

    // commit
    G.commitPattern();
    ASSERT_TRUE(G.patternCommitted());

    // zeroCommitted 清零
    G.zeroCommitted();
    for (double v : G.values()) EXPECT_NEAR(v, 0.0, 1e-15);

    // addCommitted 写入
    G.addCommitted(0, 0, 1.0); G.addCommitted(0, 1, 2.0);
    G.addCommitted(1, 0, 3.0); G.addCommitted(1, 1, 4.0); G.addCommitted(1, 2, 5.0);
    G.addCommitted(2, 1, 6.0); G.addCommitted(2, 2, 7.0);

    // 验证值与原始一致
    ASSERT_EQ(G.values().size(), orig.size());
    for (size_t i = 0; i < orig.size(); ++i)
        EXPECT_NEAR(G.values()[i], orig[i], 1e-15);

    // ptrFor 返回正确指针
    double* p = G.ptrFor(1, 2);
    ASSERT_NE(p, nullptr);
    EXPECT_NEAR(*p, 5.0, 1e-15);
    *p += 10.0;
    EXPECT_NEAR(G.get(1, 2), 15.0, 1e-15);

    // 越界返回 nullptr
    EXPECT_EQ(G.ptrFor(5, 0), nullptr);
    EXPECT_EQ(G.ptrFor(0, 5), nullptr);

    // addCommitted 越界静默丢弃（不崩溃）
    G.addCommitted(10, 10, 1.0);  // 不应崩溃
}

// L8: add() 自动转 addCommitted
TEST(Assembly, SparseMatrixAddAutoCommitted) {
    SparseMatrix G;
    G.resize(2);
    G.addPattern(0, 0); G.addPattern(0, 1);
    G.addPattern(1, 0); G.addPattern(1, 1);
    G.finalize();
    G.commitPattern();

    // committed 后用 add() 应自动走 addCommitted
    G.zeroCommitted();
    G.add(0, 0, 1.0); G.add(1, 1, 2.0);
    EXPECT_NEAR(G.get(0, 0), 1.0, 1e-15);
    EXPECT_NEAR(G.get(1, 1), 2.0, 1e-15);

    // addPattern 在 committed 后应被忽略
    G.addPattern(5, 5);  // 不应崩溃或改变 pattern
    EXPECT_EQ(G.values().size(), 4);  // pattern 未变
}
