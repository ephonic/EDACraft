// test_stability.cpp — S 参数稳定性分析单元测试
//
// 优化项5：验证 K-factor / μ / MAG / MSG 计算。
#include "../src/sparam/stability.hpp"
#include <gtest/gtest.h>
#include <cmath>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

using namespace rfsim;

namespace {
// 构造一个 2 端口 Touchstone 数据（单频点）
TouchstoneData make2port(double freq, Complex S11, Complex S21, Complex S12, Complex S22) {
    TouchstoneData td;
    td.numPorts = 2;
    td.freqs = {freq};
    td.S = {{S11, S21, S12, S22}};  // S[i*2+j]: S11,S21,S12,S22
    return td;
}
} // namespace

TEST(Stability, UnconditionallyStableAmplifier) {
    // 典型稳定放大器：K>1, |Δ|<1
    // S11=0.3∠-120, S21=5.0∠60, S12=0.02∠20, S22=0.4∠-25
    auto td = make2port(1e9,
        0.3 * std::polar(1.0, -120.0 * M_PI / 180.0),
        5.0 * std::polar(1.0,  60.0 * M_PI / 180.0),
        0.02 * std::polar(1.0, 20.0 * M_PI / 180.0),
        0.4 * std::polar(1.0, -25.0 * M_PI / 180.0));
    auto r = computeStability(td);
    ASSERT_TRUE(r.ok);
    ASSERT_EQ(r.points.size(), 1u);
    const auto& p = r.points[0];
    // K 应 > 1（稳定）
    EXPECT_GT(p.K, 1.0) << "K=" << p.K;
    EXPECT_LT(p.deltaMag, 1.0) << "|Δ|=" << p.deltaMag;
    EXPECT_TRUE(p.unconditionallyStable);
    // μ 也应 > 1
    EXPECT_GT(p.mu, 1.0);
    // MAG 应为正（有增益）
    EXPECT_GT(p.maxStableGain_dB, 0.0);
}

TEST(Stability, PotentiallyUnstableHighGain) {
    // 潜在不稳定：K<1。选 S11/S22 较大、S12·S21 使 K<1 的参数。
    // S11=0.7, S22=0.7, S21=3, S12=0.05（全实数）
    // Δ = 0.49 - 0.15 = 0.34, |Δ|=0.34
    // denom = 2·0.05·3 = 0.3
    // K = (1 - 0.49 - 0.49 + 0.34²)/0.3 = (0.02 + 0.1156)/0.3 = 0.452 → K<1
    auto td = make2port(1e9,
        Complex(0.7, 0), Complex(3.0, 0), Complex(0.05, 0), Complex(0.7, 0));
    auto r = computeStability(td);
    ASSERT_TRUE(r.ok);
    const auto& p = r.points[0];
    EXPECT_LT(p.K, 1.0) << "K=" << p.K << " (should be <1, potentially unstable)";
    EXPECT_FALSE(p.unconditionallyStable);
    // MSG = |S21/S12| = 60 → 10·log10(60) = 17.78 dB
    EXPECT_NEAR(p.maxStableGain_dB, 17.78, 0.1);
}

TEST(Stability, DeltaComputation) {
    // 验证 |Δ| = |S11·S22 - S12·S21|
    auto td = make2port(1e9, Complex(0.5, 0), Complex(2.0, 0), Complex(0.1, 0), Complex(0.4, 0));
    auto r = computeStability(td);
    ASSERT_TRUE(r.ok);
    const auto& p = r.points[0];
    // Δ = 0.5·0.4 - 0.1·2.0 = 0.2 - 0.2 = 0
    EXPECT_NEAR(p.deltaMag, 0.0, 1e-9);
}

TEST(Stability, RequiresTwoPort) {
    TouchstoneData td;
    td.numPorts = 3;  // 非 2 端口
    auto r = computeStability(td);
    EXPECT_FALSE(r.ok);
    EXPECT_FALSE(r.message.empty());
}

TEST(Stability, MultipleFreqPoints) {
    TouchstoneData td;
    td.numPorts = 2;
    td.freqs = {1e9, 2e9, 3e9};
    td.S = {
        {Complex(0.3,0), Complex(5,0), Complex(0.02,0), Complex(0.4,0)},
        {Complex(0.25,0), Complex(4,0), Complex(0.03,0), Complex(0.35,0)},
        {Complex(0.2,0), Complex(3,0), Complex(0.04,0), Complex(0.3,0)},
    };
    auto r = computeStability(td);
    ASSERT_TRUE(r.ok);
    EXPECT_EQ(r.points.size(), 3u);
    EXPECT_NEAR(r.points[0].freq, 1e9, 1.0);
    EXPECT_NEAR(r.points[2].freq, 3e9, 1.0);
}
