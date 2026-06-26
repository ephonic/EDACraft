// test_hb.cpp - Harmonic Balance solver tests
#include "solver/hb_solver.hpp"
#include "solver/ac_analysis.hpp"
#include "model/builtin_devices.hpp"
#include <gtest/gtest.h>
#include <cmath>
using namespace rfsim;

TEST(Hb, ResistorDividerDC) {
    std::vector<std::unique_ptr<DeviceModel>> devs;
    auto v = std::make_unique<VoltageSource>("v1", 1, 0, 5.0);
    devs.push_back(std::move(v));
    devs.push_back(std::make_unique<Resistor>("r1", 1, 2, 1000.0));
    devs.push_back(std::make_unique<Resistor>("r2", 2, 0, 1000.0));
    HbConfig cfg; cfg.fundamental = 1e6; cfg.numHarmonics = 3;
    auto r = solveHbLinear(2, devs, cfg);
    ASSERT_TRUE(r.ok);
    EXPECT_NEAR(r.nodeVoltages[1].v[0].real(), 5.0, 1e-6);
    EXPECT_NEAR(r.nodeVoltages[2].v[0].real(), 2.5, 1e-6);
    for (uint32_t k = 1; k <= 3; ++k) EXPECT_NEAR(std::abs(r.nodeVoltages[2].v[k]), 0.0, 1e-9);
}

TEST(Hb, RcLowpassMatchesAC) {
    std::vector<std::unique_ptr<DeviceModel>> devs;
    auto v = std::make_unique<VoltageSource>("v1", 1, 0, 0.0);
    v->setAcMag(Complex(1.0, 0.0));
    devs.push_back(std::move(v));
    devs.push_back(std::make_unique<Resistor>("r1", 1, 2, 1000.0));
    devs.push_back(std::make_unique<Capacitor>("c1", 2, 0, 1e-9));
    double f0 = 159154.9;
    HbConfig cfg; cfg.fundamental = f0; cfg.numHarmonics = 3;
    auto hb = solveHbLinear(2, devs, cfg);
    ASSERT_TRUE(hb.ok);
    double hbMag = std::abs(hb.nodeVoltages[2].v[1]);
    EXPECT_NEAR(hbMag, 1.0 / std::sqrt(2.0), 1e-3);
    AcSpec aspec;
    auto ac = solveAc(2, devs, aspec, {f0});
    ASSERT_TRUE(ac.ok);
    EXPECT_NEAR(hbMag, std::abs(ac.points[0].nodeVoltages[2]), 1e-6);
}

TEST(Hb, WaveformIFFT) {
    std::vector<std::unique_ptr<DeviceModel>> devs;
    auto v = std::make_unique<VoltageSource>("v1", 1, 0, 0.0);
    v->setAcMag(Complex(1.0, 0.0));
    devs.push_back(std::move(v));
    devs.push_back(std::make_unique<Resistor>("r1", 1, 2, 1000.0));
    devs.push_back(std::make_unique<Resistor>("r2", 2, 0, 1000.0));
    HbConfig cfg; cfg.fundamental = 1e6; cfg.numHarmonics = 3;
    auto hb = solveHbLinear(2, devs, cfg);
    ASSERT_TRUE(hb.ok);
    auto wave = nodeHarmonicsToWaveform(hb.nodeVoltages[2], 3);
    ASSERT_EQ(wave.size(), 8u);
    double maxAbs = 0;
    for (double w : wave) maxAbs = std::max(maxAbs, std::fabs(w));
    EXPECT_NEAR(maxAbs, 0.5, 0.1);
}

TEST(Hb, DcPlusSine) {
    std::vector<std::unique_ptr<DeviceModel>> devs;
    auto v = std::make_unique<VoltageSource>("v1", 1, 0, 2.0);
    v->setAcMag(Complex(1.0, 0.0));
    devs.push_back(std::move(v));
    devs.push_back(std::make_unique<Resistor>("r1", 1, 2, 1000.0));
    devs.push_back(std::make_unique<Resistor>("r2", 2, 0, 1000.0));
    HbConfig cfg; cfg.fundamental = 1e6; cfg.numHarmonics = 2;
    auto hb = solveHbLinear(2, devs, cfg);
    ASSERT_TRUE(hb.ok);
    EXPECT_NEAR(hb.nodeVoltages[2].v[0].real(), 1.0, 1e-6);
    EXPECT_NEAR(std::abs(hb.nodeVoltages[2].v[1]), 0.5, 1e-6);
}
