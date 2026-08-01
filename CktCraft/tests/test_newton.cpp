// test_newton.cpp - nonlinear DC Newton convergence tests
#include "solver/dc_op.hpp"
#include "model/builtin_devices.hpp"
#include "model/generated/generated_registry.hpp"
#include <gtest/gtest.h>
#include <cmath>
#include <cstdlib>
#include <iostream>
using namespace rfsim;

// Voltage-driven diode: V=5V, R=1k, D forward biased -> V_anode ~0.7V
TEST(NewtonDiag, DiodeVoltageDriven) {
    std::vector<std::unique_ptr<DeviceModel>> devs;
    devs.push_back(std::make_unique<VoltageSource>("v1", 2, 0, 5.0));
    devs.push_back(std::make_unique<Resistor>("r1", 2, 1, 1000.0));
    auto diode = createGeneratedModel("simple_diode", "d1", std::vector<NodeId>{1, 0}, ParamList{}, ParamList{});
    devs.push_back(std::move(diode));

    DcOpOptions opts;
    opts.maxIterations = 2000;
    opts.dvmax = 0.1;
    auto r = solveDcOp(2, devs, opts);
    std::cout << "[NewtonDiag] converged=" << r.converged << " iters=" << r.iterations;
    if (r.nodeVoltages.size() > 2)
        std::cout << " v(anode)=" << r.nodeVoltages[1];
    std::cout << "\n";
    EXPECT_TRUE(r.converged);
    ASSERT_GT(r.nodeVoltages.size(), 2u);
    EXPECT_NEAR(r.nodeVoltages[2], 5.0, 1e-3);
    EXPECT_NEAR(r.nodeVoltages[1], 0.7, 0.15);
}
