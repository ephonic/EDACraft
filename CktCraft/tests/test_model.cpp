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

// ===== C1-level54: HSPICE level=54 BSIM4 → bsim4va (OSDI) 路由 =====
TEST(Model, FactoryLevel54NmosRoutesToBsim4va) {
    // .model nch nmos (level=54 ...) 应路由到 bsim4va descriptor。
    // 验证：buildDeviceModels 后器件是 OsdiModel（非 placeholder）。
    // 若 bsim4.dll 不可加载（无 RFSIM_BSIM4_LIB），器件 ready()=false 但仍是 OsdiModel。
    const char* dir = RFSIM_TEST_DATA_DIR;
    std::string dllPath = std::string(dir) + "/../../models/bsim4.dll";
    // 简化：构造一个含 level=54 的最小网表
    std::string netlist =
        "title\n"
        "M1 d g 0 0 nch w=1u l=130n\n"
        ".model nch nmos (level=54 toxe=3e-9 vth0=0.4 k1=0.3 u0=0.021 vsat=491929)\n";
    auto pr = parseNetlist(netlist, "<test>");
    ASSERT_TRUE(pr.ok);
    auto fr = flatten(pr.netlist); ASSERT_TRUE(fr.ok);
    ParamEnv env;
    env.libSearchDir = std::string(dir) + "/../../models";
    auto fac = buildDeviceModels(fr.circuit, env);
    ASSERT_TRUE(fac.ok);
    ASSERT_EQ(fac.devices.size(), 1u);
    auto* m = dynamic_cast<OsdiModel*>(fac.devices[0].get());
    ASSERT_NE(m, nullptr) << "level=54 nmos should become OsdiModel";
    // fallbackTypeName 在 level=54 路由后被设为 "bsim4va"（descriptor 名）
    EXPECT_EQ(m->modelName(), "bsim4va");
}

TEST(Model, FactoryLevel54PmosRoutesToBsim4va) {
    // pmos 同样路由到 bsim4va，且应注入 type=-1 极性。
    std::string netlist =
        "title\n"
        "M1 d g 0 0 pch w=1u l=130n\n"
        ".model pch pmos (level=54 toxe=3e-9 vth0=-0.4 k1=0.3 u0=0.008 vsat=491929)\n";
    auto pr = parseNetlist(netlist, "<test>");
    ASSERT_TRUE(pr.ok);
    auto fr = flatten(pr.netlist); ASSERT_TRUE(fr.ok);
    ParamEnv env;
    const char* dir = RFSIM_TEST_DATA_DIR;
    env.libSearchDir = std::string(dir) + "/../../models";
    auto fac = buildDeviceModels(fr.circuit, env);
    ASSERT_TRUE(fac.ok);
    auto* m = dynamic_cast<OsdiModel*>(fac.devices[0].get());
    ASSERT_NE(m, nullptr);
    EXPECT_EQ(m->modelName(), "bsim4va");
}

TEST(Model, FactoryLevel54NonBsimLevelNotRouted) {
    // level=1 (Shichman-Hodges) 不应路由到 bsim4va（保持原 type）。
    std::string netlist =
        "title\n"
        "M1 d g 0 0 nch w=1u l=130n\n"
        ".model nch nmos (level=1 vth0=0.5 kp=50u)\n";
    auto pr = parseNetlist(netlist, "<test>");
    ASSERT_TRUE(pr.ok);
    auto fr = flatten(pr.netlist); ASSERT_TRUE(fr.ok);
    ParamEnv env;
    auto fac = buildDeviceModels(fr.circuit, env);
    ASSERT_TRUE(fac.ok);
    auto* m = dynamic_cast<OsdiModel*>(fac.devices[0].get());
    ASSERT_NE(m, nullptr);
    // level=1 不路由 → fallbackTypeName 仍是 "nmos"（原 type）
    EXPECT_EQ(m->modelName(), "nmos");
}
