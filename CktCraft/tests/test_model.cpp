// test_model.cpp - device model layer tests
#include "model/builtin_devices.hpp"
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
TEST(Model, FactoryMosfetBecomesDeviceModel) {
    // 使用已知生成模型类型 simple_diode 验证工厂路由
    auto pr = parseNetlist("title\nD1 a 0 dmod\n.model dmod simple_diode\n", "<test>");
    ASSERT_TRUE(pr.ok);
    auto fr = flatten(pr.netlist); ASSERT_TRUE(fr.ok);
    ParamEnv env;
    auto fac = buildDeviceModels(fr.circuit, env);
    ASSERT_TRUE(fac.ok);
    ASSERT_NE(fac.devices[0], nullptr);
    EXPECT_FALSE(fac.devices[0]->is_linear());
}

// ===== C1-level54: HSPICE level=54 BSIM4 → bsim4va (generated) 路由 =====
TEST(Model, FactoryLevel54NmosRoutesToBsim4va) {
    std::string netlist =
        "title\n"
        "M1 d g 0 0 nch w=1u l=130n\n"
        ".model nch nmos (level=54 toxe=3e-9 vth0=0.4 k1=0.3 u0=0.021 vsat=491929)\n";
    auto pr = parseNetlist(netlist, "<test>");
    ASSERT_TRUE(pr.ok);
    auto fr = flatten(pr.netlist); ASSERT_TRUE(fr.ok);
    ParamEnv env;
    auto fac = buildDeviceModels(fr.circuit, env);
    ASSERT_TRUE(fac.ok);
    ASSERT_EQ(fac.devices.size(), 1u);
    EXPECT_FALSE(fac.devices[0]->is_linear());
}

TEST(Model, FactoryLevel54PmosRoutesToBsim4va) {
    std::string netlist =
        "title\n"
        "M1 d g 0 0 pch w=1u l=130n\n"
        ".model pch pmos (level=54 toxe=3e-9 vth0=-0.4 k1=0.3 u0=0.008 vsat=491929)\n";
    auto pr = parseNetlist(netlist, "<test>");
    ASSERT_TRUE(pr.ok);
    auto fr = flatten(pr.netlist); ASSERT_TRUE(fr.ok);
    ParamEnv env;
    auto fac = buildDeviceModels(fr.circuit, env);
    ASSERT_TRUE(fac.ok);
    EXPECT_FALSE(fac.devices[0]->is_linear());
}

#ifdef RFSIM_USE_GENERATED_MODELS
TEST(Model, FactoryLevel54GeneratedRoutesToGenBsim4va) {
    std::string netlist =
        "title\n"
        "M1 d g 0 0 nch w=1u l=130n\n"
        ".model nch nmos (level=54 generated=1 toxe=3e-9 vth0=0.4 k1=0.3 u0=0.021 vsat=491929)\n";
    auto pr = parseNetlist(netlist, "<test>");
    ASSERT_TRUE(pr.ok);
    auto fr = flatten(pr.netlist); ASSERT_TRUE(fr.ok);
    ParamEnv env;
    const char* dir = RFSIM_TEST_DATA_DIR;
    env.libSearchDir = std::string(dir) + "/../../models";
    auto fac = buildDeviceModels(fr.circuit, env);
    ASSERT_TRUE(fac.ok);
    ASSERT_EQ(fac.devices.size(), 1u);
    EXPECT_FALSE(fac.devices[0]->is_linear());
}
#endif // RFSIM_USE_GENERATED_MODELS

TEST(Model, FactoryLevel54NonBsimLevelNotRouted) {
    // level=1 (Shichman-Hodges) 不应路由到 bsim4va。
    // 纯生成模型模式下，无对应模型 → fac.ok=false。
    std::string netlist =
        "title\n"
        "M1 d g 0 0 nch w=1u l=130n\n"
        ".model nch nmos (level=1 vth0=0.5 kp=50u)\n";
    auto pr = parseNetlist(netlist, "<test>");
    ASSERT_TRUE(pr.ok);
    auto fr = flatten(pr.netlist); ASSERT_TRUE(fr.ok);
    ParamEnv env;
    auto fac = buildDeviceModels(fr.circuit, env);
    // level=1 无对应生成模型，工厂报错
    EXPECT_FALSE(fac.ok);
}
