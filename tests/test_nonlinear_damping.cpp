// test_nonlinear_damping.cpp — Phase A2-4: 阻尼控制器单元测试
//
// 覆盖 DampingController 的 LM 自适应 λ、Backtracking Armijo、TR 步长限幅，
// 以及 applyLmRegularization 对稠密 Jacobian 对角的修改。
#include "../src/solver/nonlinear_damping.hpp"
#include <gtest/gtest.h>
#include <cmath>
#include <vector>

using rfsim::DampingController;
using rfsim::DampingStrategy;

// LM 正则化：对角线被加上 λ·scale（scale = 该行最大 |J|）
TEST(NonlinearDamping, LmRegularizationAddsToDiagonal) {
    const uint32_t dim = 3;
    DampingController d(dim, DampingStrategy::LevenbergMarquardt);
    d.setInitialLambda(0.1);
    // J = 单位阵（对角 1，off 0）→ scale=1，对角加 0.1*1=0.1 → 对角=1.1
    std::vector<double> J(dim * dim, 0.0);
    for (uint32_t i = 0; i < dim; ++i) J[i * dim + i] = 1.0;
    d.applyLmRegularization(J);
    for (uint32_t i = 0; i < dim; ++i) {
        EXPECT_NEAR(J[i * dim + i], 1.1, 1e-9);
        for (uint32_t k = 0; k < dim; ++k)
            if (k != i) EXPECT_NEAR(J[i * dim + k], 0.0, 1e-9);
    }
}

// LM 正则化：非对角行有更大元素时 scale 取该值
TEST(NonlinearDamping, LmRegularizationUsesRowMaxScale) {
    const uint32_t dim = 2;
    DampingController d(dim, DampingStrategy::LevenbergMarquardt);
    d.setInitialLambda(1.0);
    // J 行 0 = [10, 0]（scale=10）, 行 1 = [0, 1]（scale=1）
    std::vector<double> J = {10.0, 0.0, 0.0, 1.0};
    d.applyLmRegularization(J);
    EXPECT_NEAR(J[0], 10.0 + 1.0 * 10.0, 1e-9);  // 行0对角 += λ*10
    EXPECT_NEAR(J[3], 1.0 + 1.0 * 1.0, 1e-9);    // 行1对角 += λ*1
}

// Backtracking 策略不应修改 J（applyLmRegularization 是 no-op）
TEST(NonlinearDamping, BacktrackingSkipsRegularization) {
    const uint32_t dim = 2;
    DampingController d(dim, DampingStrategy::Backtracking);
    d.setInitialLambda(1.0);
    std::vector<double> J = {2.0, 0.0, 0.0, 3.0};
    d.applyLmRegularization(J);
    EXPECT_NEAR(J[0], 2.0, 1e-9);
    EXPECT_NEAR(J[3], 3.0, 1e-9);
}

// LM step：残差下降 → 接受 + λ 减小
TEST(NonlinearDamping, LmAcceptsDescentAndDecreasesLambda) {
    DampingController d(2, DampingStrategy::LevenbergMarquardt);
    d.setInitialLambda(1.0);
    double lamBefore = d.lambda();
    // fNorm=1.0, fTrial=0.5（下降）→ 接受
    auto r = d.step(1.0, 0.5, 1.0, 0.1, 1.0);
    EXPECT_TRUE(r.accepted);
    EXPECT_GT(d.lambda(), 0.0);
    EXPECT_LT(d.lambda(), lamBefore);  // λ 降了
}

// LM step：残差上升 → 拒绝 + λ 增大 + 标记重算
TEST(NonlinearDamping, LmRejectsAscentAndIncreasesLambda) {
    DampingController d(2, DampingStrategy::LevenbergMarquardt);
    d.setInitialLambda(1.0);
    double lamBefore = d.lambda();
    // fNorm=1.0, fTrial=2.0（上升）→ 拒绝
    auto r = d.step(1.0, 2.0, 1.0, 0.1, 1.0);
    EXPECT_FALSE(r.accepted);
    EXPECT_TRUE(r.recomputeStep);
    EXPECT_GT(d.lambda(), lamBefore);  // λ 升了
}

// LM step：连续失败 λ 单调升，有上限保护
TEST(NonlinearDamping, LmLambdaHasUpperBound) {
    DampingController d(2, DampingStrategy::LevenbergMarquardt);
    d.setInitialLambda(1.0);
    for (int i = 0; i < 50; ++i) d.step(1.0, 2.0, 1.0, 0.1, 1.0);  // 全失败
    EXPECT_LE(d.lambda(), 1e6);  // 上限
}

// Backtracking step：满足 Armijo → 接受
TEST(NonlinearDamping, BacktrackingAcceptsArmijo) {
    DampingController d(2, DampingStrategy::Backtracking);
    // fNorm=1.0, fTrial²=0.5²=0.25 ≤ 1·(1-2e-4·1)≈0.9998 → 接受
    auto r = d.step(1.0, 0.5, 1.0, 0.1, 1.0);
    EXPECT_TRUE(r.accepted);
}

// Backtracking step：不满足 Armijo → 拒绝
TEST(NonlinearDamping, BacktrackingRejectsNonArmijo) {
    DampingController d(2, DampingStrategy::Backtracking);
    // fNorm=1.0, fTrial=0.999（几乎不下降），alpha=1：0.999²=0.998 > 0.9998？不，0.998 < 0.9998 接受？
    // 实际 0.998 ≤ 0.9998 → 接受。改用更大的 fTrial 触发拒绝：fTrial=1.5（上升）
    auto r = d.step(1.0, 1.5, 1.0, 0.1, 1.0);
    EXPECT_FALSE(r.accepted);
}

// reset 恢复初始 λ
TEST(NonlinearDamping, ResetRestoresInitialLambda) {
    DampingController d(2, DampingStrategy::LevenbergMarquardt);
    d.setInitialLambda(0.5);
    d.step(1.0, 2.0, 1.0, 0.1, 1.0);  // 升 λ
    EXPECT_NE(d.lambda(), 0.5);
    d.reset();
    EXPECT_NEAR(d.lambda(), 0.5, 1e-9);
}

// TrustRegion：步长超出半径 → 缩放 alpha
TEST(NonlinearDamping, TrustRegionScalesOversizedStep) {
    DampingController d(2, DampingStrategy::TrustRegion);
    // dxNorm=10.0 > trustRadius_=1.0 → alpha 应被缩到 ~0.1
    auto r = d.step(1.0, 0.5, 1.0, 10.0, 1.0);
    EXPECT_LT(r.alpha, 1.0);
    EXPECT_GT(r.alpha, 0.0);
}
