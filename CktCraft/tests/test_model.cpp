// test_model.cpp - device model layer tests
#include "model/builtin_devices.hpp"
#include "model/osdi_model.hpp"
#include "model/device_factory.hpp"
#include "circuit/flatten.hpp"
#include "parser/parser.hpp"
#include <gtest/gtest.h>
using namespace rfsim;

TEST(Model, ResistorStampPattern) {
    Resistor r("r1", 1, 2, 1000.0);
    StampPattern sp; r.stamp_pattern(sp);
    ASSERT_EQ(sp.entries.size(), 4u);
}
TEST(Model, ResistorConductance) {
    Resistor r("r1", 1, 2, 1000.0);
    EXPECT_DOUBLE_EQ(r.conductance(), 1e-3);
    EXPECT_TRUE(r.is_linear());
}
TEST(Model, ResistorEval) {
    Resistor r("r1", 1, 2, 500.0);
    OperatingPoint op{{1.0, 0.0}};
    DeviceContribution dc; r.eval(op, dc);
    ASSERT_EQ(dc.jac.size(), 4u);
    EXPECT_DOUBLE_EQ(dc.jac[0], 2e-3);
}
TEST(Model, ResistorNegativeThrows) {
    EXPECT_THROW(Resistor("r1", 1, 2, -100.0), std::invalid_argument);
}
TEST(Model, CurrentSourceEval) {
    CurrentSource cs("i1", 1, 2, 0.005);
    OperatingPoint op{{0,0}};
    DeviceContribution dc; cs.eval(op, dc);
    EXPECT_DOUBLE_EQ(dc.f[0], 0.005);
    EXPECT_DOUBLE_EQ(dc.f[1], -0.005);
}
TEST(Model, VoltageSourceValue) {
    VoltageSource vs("v1", 1, 0, 1.2);
    EXPECT_DOUBLE_EQ(vs.voltage(), 1.2);
    EXPECT_TRUE(vs.needs_branch_current());
}
TEST(Model, FactoryBuildsResistor) {
    auto pr = parseNetlist("title\nR1 a b 2k\n", "<test>");
    ASSERT_TRUE(pr.ok);
    auto fr = flatten(pr.netlist); ASSERT_TRUE(fr.ok);
    ParamEnv env;
    auto fac = buildDeviceModels(fr.circuit, env);
    ASSERT_TRUE(fac.ok);
    ASSERT_EQ(fac.devices.size(), 1u);
    auto* r = dynamic_cast<Resistor*>(fac.devices[0].get());
    ASSERT_NE(r, nullptr);
    EXPECT_DOUBLE_EQ(r->resistance(), 2000.0);
}
TEST(Model, FactoryMosfetBecomesOsdiModel) {
    auto pr = parseNetlist("title\nM1 d g s b nmos w=1u l=180n\n.model nmos nmos\n", "<test>");
    ASSERT_TRUE(pr.ok);
    auto fr = flatten(pr.netlist); ASSERT_TRUE(fr.ok);
    ParamEnv env;
    auto fac = buildDeviceModels(fr.circuit, env);
    ASSERT_TRUE(fac.ok);
    auto* m = dynamic_cast<OsdiModel*>(fac.devices[0].get());
    ASSERT_NE(m, nullptr);
    EXPECT_FALSE(m->is_linear());
}
