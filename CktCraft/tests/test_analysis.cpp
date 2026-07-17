// test_analysis.cpp - DC sweep and AC analysis tests
#include "solver/dc_sweep.hpp"
#include "solver/ac_analysis.hpp"
#include "model/builtin_devices.hpp"
#include <gtest/gtest.h>
#include <cmath>
using namespace rfsim;

TEST(DcSweep, VoltageDivider) {
    std::vector<std::unique_ptr<DeviceModel>> devs;
    devs.push_back(std::make_unique<VoltageSource>("v1", 1, 0, 0.0));
    devs.push_back(std::make_unique<Resistor>("r1", 1, 2, 1000.0));
    devs.push_back(std::make_unique<Resistor>("r2", 2, 0, 1000.0));
    DcSweepSpec spec{"v1", 0.0, 5.0, 1.0};
    auto r = solveDcSweep(2, devs, spec);
    ASSERT_TRUE(r.ok);
    ASSERT_EQ(r.points.size(), 6u);
    for (size_t k = 0; k < r.points.size(); ++k) {
        EXPECT_NEAR(r.points[k].nodeVoltages[2], r.points[k].sweepValue / 2.0, 1e-6);
    }
}
TEST(Ac, RcLowpass) {
    std::vector<std::unique_ptr<DeviceModel>> devs;
    auto v = std::make_unique<VoltageSource>("v1", 1, 0, 0.0);
    v->setAcMag(Complex(1.0, 0.0));
    devs.push_back(std::move(v));
    devs.push_back(std::make_unique<Resistor>("r1", 1, 2, 1000.0));
    devs.push_back(std::make_unique<Capacitor>("c1", 2, 0, 1e-6));
    AcSpec spec;
    auto r = solveAc(2, devs, spec, {1.0, 159.1549, 15915.49});
    ASSERT_TRUE(r.ok);
    ASSERT_EQ(r.points.size(), 3u);
    EXPECT_NEAR(std::abs(r.points[0].nodeVoltages[2]), 1.0, 1e-3);
    EXPECT_NEAR(std::abs(r.points[1].nodeVoltages[2]), 1.0/std::sqrt(2.0), 1e-3);
    EXPECT_NEAR(std::abs(r.points[2].nodeVoltages[2]), 0.01, 1e-3);
}
TEST(Ac, ResistorOnly) {
    std::vector<std::unique_ptr<DeviceModel>> devs;
    auto v = std::make_unique<VoltageSource>("v1", 1, 0, 0.0);
    v->setAcMag(Complex(1.0, 0.0));
    devs.push_back(std::move(v));
    devs.push_back(std::make_unique<Resistor>("r1", 1, 2, 1000.0));
    devs.push_back(std::make_unique<Resistor>("r2", 2, 0, 1000.0));
    AcSpec spec;
    auto r = solveAc(2, devs, spec, {1.0, 1e6});
    ASSERT_TRUE(r.ok);
    EXPECT_NEAR(std::abs(r.points[0].nodeVoltages[2]), 0.5, 1e-9);
}
