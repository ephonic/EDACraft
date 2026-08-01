// test_hb_nl.cpp - nonlinear Harmonic Balance tests
#include "solver/hb_nonlinear.hpp"
#include "solver/hb_solver.hpp"
#include "model/builtin_devices.hpp"
#include "model/generated/generated_registry.hpp"
#include <gtest/gtest.h>
#include <cmath>
using namespace rfsim;

namespace {
ParamList bsim4ModelParams() {
    ParamList p;
    auto add = [&](const char* n, double v) {
        p.push_back({n, ParamValue{ParamValue::Kind::Number, v, "", SourceLoc{}}});
    };
    add("toxe", 3e-9); add("toxp", 3e-9); add("vth0", 0.5);
    add("k1", 0.5); add("k2", 0.0); add("k3", 0.0);
    add("dvt0", 1.0); add("dvt1", 2.0); add("dvt2", -0.032);
    add("u0", 0.045); add("ua", -1e-10); add("ub", 0.0);
    add("vsat", 1.5e5); add("rdsw", 160); add("nfactor", 1.2);
    add("cgso", 0.1e-9); add("cgdo", 0.1e-9); add("cgbo", 0.0);
    add("cjs", 1e-3); add("cjd", 1e-3);
    add("cjsws", 1e-10); add("cjswd", 1e-10);
    add("mjs", 0.5); add("mjd", 0.5);
    add("mjsws", 0.33); add("mjswd", 0.33);
    add("pbs", 0.88); add("pbd", 0.88);
    add("pbsws", 0.88); add("pbswd", 0.88);
    return p;
}

} // namespace

// Diode rectifier: sine drives diode, expect DC + harmonics
TEST(HbNonlinear, DiodeRectifierRuns) {
    std::vector<std::unique_ptr<DeviceModel>> devs;
    auto v = std::make_unique<VoltageSource>("v1", 1, 0, 0.0);
    v->setAcMag(Complex(1.0, 0.0));
    devs.push_back(std::move(v));
    devs.push_back(std::make_unique<Resistor>("r1", 1, 2, 1000.0));
    auto diode = createGeneratedModel("simple_diode", "d1", std::vector<NodeId>{2, 0}, ParamList{}, ParamList{});
    devs.push_back(std::move(diode));

    HbConfig cfg; cfg.fundamental = 1e6; cfg.numHarmonics = 3;
    auto r = solveHbNonlinear(2, devs, cfg);
    ASSERT_GT(r.nodeVoltages.size(), 2u);
    // fundamental component should exist
    EXPECT_GT(std::abs(r.nodeVoltages[2].v[1]), 1e-6);
}

// Diode rectifier with source continuation (higher drive, fixed gmin)
TEST(HbNonlinear, DiodeRectifierContinuation) {
    std::vector<std::unique_ptr<DeviceModel>> devs;
    auto v = std::make_unique<VoltageSource>("v1", 1, 0, 0.0);
    v->setAcMag(Complex(2.0, 0.0));
    devs.push_back(std::move(v));
    devs.push_back(std::make_unique<Resistor>("r1", 1, 2, 1000.0));
    auto diode = createGeneratedModel("simple_diode", "d1", std::vector<NodeId>{2, 0}, ParamList{}, ParamList{});
    devs.push_back(std::move(diode));

    HbConfig cfg; cfg.fundamental = 1e6; cfg.numHarmonics = 3;
    HbNlOptions opts;
    opts.sourceSteps = 10;
    opts.gmin.gminSteps = 0;
    opts.gmin.gmin = 1e-2;
    auto r = solveHbNonlinear(2, devs, cfg, nullptr, opts);
    EXPECT_TRUE(r.converged);
    EXPECT_EQ(r.continuationSteps, 10u + 1);
    ASSERT_GT(r.nodeVoltages.size(), 2u);
    EXPECT_GT(std::abs(r.nodeVoltages[2].v[1]), 1e-6);
}

// Linear circuit: nonlinear HB should match linear HB
TEST(HbNonlinear, LinearMatchesHbLinear) {
    std::vector<std::unique_ptr<DeviceModel>> devs;
    auto v = std::make_unique<VoltageSource>("v1", 1, 0, 2.0);
    v->setAcMag(Complex(1.0, 0.0));
    devs.push_back(std::move(v));
    devs.push_back(std::make_unique<Resistor>("r1", 1, 2, 1000.0));
    devs.push_back(std::make_unique<Resistor>("r2", 2, 0, 1000.0));

    HbConfig cfg; cfg.fundamental = 1e6; cfg.numHarmonics = 2;
    auto hbNl = solveHbNonlinear(2, devs, cfg);
    ASSERT_GT(hbNl.nodeVoltages.size(), 2u);
    EXPECT_NEAR(hbNl.nodeVoltages[2].v[0].real(), 1.0, 0.2);
    EXPECT_NEAR(std::abs(hbNl.nodeVoltages[2].v[1]), 0.5, 0.2);
}

// BSIM4 common-source amplifier: verify nonlinear HB converges with a MOSFET
TEST(HbNonlinear, Bsim4EvalDcDoesNotCrash) {
    ParamList instParams;
    instParams.push_back({"w", ParamValue{ParamValue::Kind::Number, 1e-6, "", SourceLoc{}}});
    instParams.push_back({"l", ParamValue{ParamValue::Kind::Number, 130e-9, "", SourceLoc{}}});
    ParamList allParams = instParams;
    for (auto& p : bsim4ModelParams()) allParams.push_back(std::move(p));
    auto mos = createGeneratedModel("bsim4va", "m1", std::vector<NodeId>{2, 3, 0, 0}, allParams, ParamList{});

    std::vector<double> v(20, 0.0);
    v[1] = 1.0; v[2] = 0.8; v[3] = 0.5;
    OperatingPoint op{v};
    DeviceContribution dc;
    mos->eval(op, dc);

    // stress evalDC to check for state-dependent crash
    for (int i = 0; i < 200; ++i) {
        v[2] = 0.5 + 0.01 * (i % 10);
        OperatingPoint op2{v};
        mos->eval(op2, dc);
    }
}

TEST(HbNonlinear, Bsim4CommonSourceConverges) {
    std::vector<std::unique_ptr<DeviceModel>> devs;

    // VDD = 1V
    devs.push_back(std::make_unique<VoltageSource>("vdd", 1, 0, 1.0));
    // Load resistor
    devs.push_back(std::make_unique<Resistor>("rd", 1, 2, 1000.0));
    // Gate bias + small信号：偏置接近阈值，保持弱非线性以确保 Newton 收敛。
    // 强非线性（深导通、大信号）仍需要更精确的瞬态残差与更鲁棒的 continuation。
    auto vg = std::make_unique<VoltageSource>("vg", 3, 0, 0.55);
    vg->setAcMag(Complex(0.1, 0.0));
    devs.push_back(std::move(vg));

    ParamList instParams;
    instParams.push_back({"w", ParamValue{ParamValue::Kind::Number, 1e-6, "", SourceLoc{}}});
    instParams.push_back({"l", ParamValue{ParamValue::Kind::Number, 130e-9, "", SourceLoc{}}});
    ParamList allParams = instParams;
    for (auto& p : bsim4ModelParams()) allParams.push_back(std::move(p));
    auto mos = createGeneratedModel("bsim4va", "m1", std::vector<NodeId>{2, 3, 0, 0}, allParams, ParamList{});
    devs.push_back(std::move(mos));

    HbConfig cfg; cfg.fundamental = 1e6; cfg.numHarmonics = 1;
    HbNlOptions opts;
    opts.sourceSteps = 0;
    opts.gmin.gmin = 1e-12;
    opts.dvmax = 0.5;
    opts.maxIter = 50;
    auto r = solveHbNonlinear(3, devs, cfg, nullptr, opts);
    EXPECT_TRUE(r.converged);
    ASSERT_GT(r.nodeVoltages.size(), 2u);
    EXPECT_TRUE(std::isfinite(r.nodeVoltages[2].v[1].real()))
        << "node 2 fundamental real part is not finite";
    EXPECT_TRUE(std::isfinite(r.nodeVoltages[2].v[1].imag()))
        << "node 2 fundamental imag part is not finite";
}
