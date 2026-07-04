// =====================================================================
// core/tests/test_frequency_sweep.cpp —— FreqSweep 单元测试
// =====================================================================
#include <gtest/gtest.h>
#include "mom/sweep/frequency_sweep.hpp"

using mom::FrequencySweep;
using mom::Real;
using mom::Size;
using mom::SweepScale;

TEST(FrequencySweep, LinearEndpointsAndSpacing) {
    FrequencySweep sw(1.0e6, 10.0e9, 11, SweepScale::Linear);
    auto f = sw.frequencies();
    ASSERT_EQ(f.size(), 11u);
    EXPECT_DOUBLE_EQ(f.front(), 1.0e6);
    EXPECT_DOUBLE_EQ(f.back(),  10.0e9);
    // 等间距
    const Real step = (10.0e9 - 1.0e6) / 10.0;
    for (Size i = 0; i < f.size(); ++i)
        EXPECT_NEAR(f[i], 1.0e6 + Real(i) * step, 1.0e-3);
}

TEST(FrequencySweep, LogEndpointsAndGeometric) {
    FrequencySweep sw(1.0e6, 1.0e9, 4, SweepScale::Log);
    auto f = sw.frequencies();
    ASSERT_EQ(f.size(), 4u);
    EXPECT_NEAR(f.front(), 1.0e6, 1.0);
    EXPECT_NEAR(f.back(),  1.0e9, 1.0);
    // 相邻比值为常数（几何级数）
    const Real r0 = f[1] / f[0];
    EXPECT_NEAR(f[2] / f[1], r0, 1.0e-9);
    EXPECT_NEAR(f[3] / f[2], r0, 1.0e-9);
}

TEST(FrequencySweep, SinglePoint) {
    FrequencySweep sw(1.0e9, 1.0e9, 1, SweepScale::Linear);
    auto f = sw.frequencies();
    ASSERT_EQ(f.size(), 1u);
    EXPECT_DOUBLE_EQ(f[0], 1.0e9);
}

TEST(FrequencySweep, RejectsInvalid) {
    EXPECT_THROW(FrequencySweep(1.0e9, 1.0e6, 10, SweepScale::Linear),
                 std::invalid_argument);                  // stop<start
    EXPECT_THROW(FrequencySweep(0.0, 1.0e9, 10, SweepScale::Log),
                 std::invalid_argument);                  // log start<=0
    EXPECT_THROW(FrequencySweep(1.0e6, 1.0e9, 0, SweepScale::Linear),
                 std::invalid_argument);                  // count==0
}

TEST(FrequencySweep, ParseScale) {
    EXPECT_EQ(mom::parse_scale("lin"),  SweepScale::Linear);
    EXPECT_EQ(mom::parse_scale("LOG"),  SweepScale::Log);
    EXPECT_EQ(mom::parse_scale(""),     SweepScale::Linear);
    EXPECT_THROW(mom::parse_scale("xyz"), std::invalid_argument);
}
