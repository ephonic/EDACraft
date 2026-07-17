// test_newton.cpp - nonlinear DC Newton convergence tests
#include "solver/dc_op.hpp"
#include "model/builtin_devices.hpp"
#include "model/osdi_model.hpp"
#include "model/osdi/osdi_library.hpp"
#include <gtest/gtest.h>
#include <cmath>
#include <cstdlib>
#include <iostream>
using namespace rfsim;

namespace {
std::string projectRootFromTestData() {
    std::string s = RFSIM_TEST_DATA_DIR;
    auto pos = s.find_last_of("/\\");
    if (pos != std::string::npos) s = s.substr(0, pos);
    pos = s.find_last_of("/\\");
    if (pos != std::string::npos) s = s.substr(0, pos);
    return s;
}
std::string diodeLibPath() {
    if (const char* p = std::getenv("RFSIM_OSDI_TEST_LIB")) return p;
    std::string root = projectRootFromTestData();
#ifdef _WIN32
    return root + "/models/simple_diode.dll";
#else
    return root + "/models/simple_diode.so";
#endif
}
} // namespace

// Voltage-driven diode: V=5V, R=1k, D forward biased -> V_anode ~0.7V
TEST(NewtonDiag, DiodeVoltageDriven) {
    OsdiLibrary lib;
    std::string err;
    ASSERT_TRUE(lib.load(diodeLibPath(), err));
    auto libShared = std::make_shared<OsdiLibrary>(std::move(lib));
    const OsdiDescriptor* d = libShared->descriptors();

    std::vector<std::unique_ptr<DeviceModel>> devs;
    devs.push_back(std::make_unique<VoltageSource>("v1", 2, 0, 5.0));
    devs.push_back(std::make_unique<Resistor>("r1", 2, 1, 1000.0));
    auto diode = std::make_unique<OsdiModel>("d1", std::vector<NodeId>{1, 0}, libShared, d, ParamList{});
    Diagnostics diags;
    ASSERT_TRUE(diode->initialize(diags));
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
