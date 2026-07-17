// test_edge_cases.cpp — plan0620_v2 §B3 退化情形与边界
//
// 验证求解器在病态/退化输入下的行为：
//   B3.1  极大电阻 (1TΩ) 仅有 gmin-级路径
//   B3.2  极小电阻 (1pΩ) 直连两节点，KLU 不数值崩溃
//   B3.3  弱接地 BSIM4 body 节点（1TΩ tie）— 验证 P3-14 类
//          OSDI 模型在病态联通下 DC 仍收敛或失败时不静默
//   B3.4  OSDI diode 反偏（cathode > anode），验证 limiting
//          不会把节点 latch 到正向偏置错误状态
//
// 通过判据（plan §B3）：
//   "要么收敛，要么明确警告 + 不 NaN（不允许静默错误）。"
//
// 即每个用例都要满足：
//   - 全部节点电压 finite（无 NaN/Inf）
//   - converged==true OR diags 中含 warning/error
#include "model/builtin_devices.hpp"
#include "model/osdi_model.hpp"
#include "model/osdi/osdi_library.hpp"
#include "solver/dc_op.hpp"

#include <gtest/gtest.h>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <memory>
#include <string>
#include <vector>

namespace rfsim {
namespace {

// ---- 共用助手（与 multi_device 风格一致；保留独立避免链接耦合）----
std::string projectRootFromTestData() {
    std::string s = RFSIM_TEST_DATA_DIR;
    auto pos = s.find_last_of("/\\");
    if (pos != std::string::npos) s = s.substr(0, pos);
    pos = s.find_last_of("/\\");
    if (pos != std::string::npos) s = s.substr(0, pos);
    return s;
}

std::string osdiPath(const char* env, const char* name) {
    if (const char* p = std::getenv(env)) return p;
#ifdef _WIN32
    return projectRootFromTestData() + "/models/" + name + ".dll";
#else
    return projectRootFromTestData() + "/models/" + name + ".so";
#endif
}

ParamList bsim4Model() {
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

ParamList instWL(double w = 1e-6, double l = 130e-9) {
    ParamList p;
    p.push_back({"w", ParamValue{ParamValue::Kind::Number, w, "", SourceLoc{}}});
    p.push_back({"l", ParamValue{ParamValue::Kind::Number, l, "", SourceLoc{}}});
    return p;
}

ParamList diodeFullModel() {
    ParamList p;
    auto add = [&](const char* n, double v) {
        p.push_back({n, ParamValue{ParamValue::Kind::Number, v, "", SourceLoc{}}});
    };
    add("minr", 1e-3);
    add("is", 1e-14);
    add("n", 1.0);
    add("vj", 1.0);
    add("m", 0.5);
    return p;
}

NodeId computeMaxNode(const std::vector<std::unique_ptr<DeviceModel>>& devs) {
    NodeId mx = 0;
    for (const auto& dv : devs) {
        for (NodeId n : dv->nodes()) if (n > mx) mx = n;
    }
    return mx;
}

bool allFinite(const std::vector<double>& v) {
    for (double x : v) if (!std::isfinite(x)) return false;
    return true;
}

// 是否含 warning/error（plan: "要么收敛，要么明确警告"）
bool hasDiagnostic(const Diagnostics& d) {
    return !d.errors.empty() || !d.warnings.empty();
}

} // namespace

// ============================================================
// B3.1 — 极大电阻 1TΩ：仅一条 1TΩ 路径接地，gmin floor 不应崩
// 拓扑：vs(1V) ─ 1TΩ ─ GND
// 期望：DC 收敛，V[1]=1.0V，I 在 1pA 量级，全 finite
// ============================================================
TEST(EdgeCase, HugeResistor_1TOhm) {
    std::vector<std::unique_ptr<DeviceModel>> devs;
    devs.push_back(std::make_unique<VoltageSource>("vs", 1, 0, 1.0));
    devs.push_back(std::make_unique<Resistor>("r", 1, 0, 1e12));

    DcOpOptions opts;
    auto r = solveDcOp(1, devs, opts);

    EXPECT_TRUE(r.converged) << "1TΩ DC failed to converge";
    ASSERT_TRUE(allFinite(r.nodeVoltages))
        << "non-finite node voltage with 1TΩ shunt";
    EXPECT_NEAR(r.nodeVoltages[1], 1.0, 1e-9);
    std::fprintf(stderr,
        "[EdgeCase.HugeResistor_1TOhm] V[1]=%.6e (expected 1.0)\n",
        r.nodeVoltages[1]);
}

// ============================================================
// B3.2 — 极小电阻 1pΩ：相当于强短路；KLU 处理超大 1/R 项
// 拓扑：vs(1V) ─ 1pΩ ─ node 2 ─ 1kΩ ─ GND
// 期望：DC 收敛或失败但不 NaN；V[2] ≈ V[1]（1pΩ 上压降几乎为 0）
// ============================================================
TEST(EdgeCase, TinyResistor_1pOhm) {
    std::vector<std::unique_ptr<DeviceModel>> devs;
    devs.push_back(std::make_unique<VoltageSource>("vs", 1, 0, 1.0));
    devs.push_back(std::make_unique<Resistor>("rtiny", 1, 2, 1e-12));
    devs.push_back(std::make_unique<Resistor>("rload", 2, 0, 1e3));

    DcOpOptions opts;
    auto r = solveDcOp(2, devs, opts);

    ASSERT_TRUE(allFinite(r.nodeVoltages))
        << "non-finite node voltage with 1pΩ series resistor";
    if (r.converged) {
        // 1pΩ 与 1kΩ 串联，电流由 1kΩ 主导；V[1]-V[2] = I·1pΩ ≈ 1pV
        EXPECT_NEAR(r.nodeVoltages[1], 1.0, 1e-6);
        EXPECT_NEAR(r.nodeVoltages[2], 1.0, 1e-6);
    } else {
        EXPECT_TRUE(hasDiagnostic(r.diags))
            << "1pΩ DC did not converge silently";
    }
    std::fprintf(stderr,
        "[EdgeCase.TinyResistor_1pOhm] conv=%d V[1]=%.6e V[2]=%.6e\n",
        r.converged, r.nodeVoltages[1], r.nodeVoltages[2]);
}

// ============================================================
// B3.3 — BSIM4 body 节点弱接地（1TΩ tie）
// 拓扑：vdd(1V) ─ rd(5kΩ) ─ drain ; gate=0.7V ; source=GND ;
//       body ─ 1TΩ ─ GND
// 期望：DC 路径仍可收敛（gmin homotopy + 1TΩ 弱 tie 提供唯一接地路径），
//       OR 收敛失败 + 显式 warning；不允许 NaN。
// ============================================================
TEST(EdgeCase, FloatingBsim4Body) {
    std::string libPath = osdiPath("RFSIM_BSIM4_LIB", "bsim4");
    OsdiLibrary tmp; std::string err;
    if (!tmp.load(libPath, err)) GTEST_SKIP() << "bsim4: " << err;
    auto lib = std::make_shared<OsdiLibrary>(std::move(tmp));
    if (lib->numDescriptors() < 1) GTEST_SKIP() << "no bsim4 descriptor";
    const OsdiDescriptor* desc = lib->descriptors();

    std::vector<std::unique_ptr<DeviceModel>> devs;
    devs.push_back(std::make_unique<VoltageSource>("vdd", 1, 0, 1.0));
    devs.push_back(std::make_unique<VoltageSource>("vg",  3, 0, 0.7));
    devs.push_back(std::make_unique<Resistor>("rd", 1, 2, 5e3));
    // body=4 弱接地 1TΩ —— 这是该测试的核心病态点
    devs.push_back(std::make_unique<Resistor>("rb_weak", 4, 0, 1e12));

    Diagnostics diags;
    NodeId base = 5;
    auto m = std::make_unique<OsdiModel>(
        "m1", std::vector<NodeId>{2, 3, 0, 4},  // d, g, s, b
        lib, desc, instWL(), bsim4Model());
    if (!m->initialize(diags, base)) GTEST_SKIP() << "BSIM4 init failed";
    devs.push_back(std::move(m));

    NodeId nN = computeMaxNode(devs);
    DcOpOptions opts;
    opts.gmin.gmin = 1e-9;
    opts.gmin.gminStart = 1e-3;
    opts.gmin.gminSteps = 12;
    opts.maxIterations = 100;
    opts.dvmax = 0.2;
    auto r = solveDcOp(nN, devs, opts);

    ASSERT_TRUE(allFinite(r.nodeVoltages))
        << "BSIM4 with 1TΩ body tie produced NaN/Inf";
    if (!r.converged) {
        EXPECT_TRUE(hasDiagnostic(r.diags))
            << "non-convergence reported silently";
    } else {
        // body 节点电压必须 ∈ [-vdd, vdd]，1TΩ 的轻量 tie 不会反推出大电流
        double vb = r.nodeVoltages[4];
        EXPECT_GT(vb, -2.0); EXPECT_LT(vb, 2.0);
    }
    std::fprintf(stderr,
        "[EdgeCase.FloatingBsim4Body] conv=%d V[drain]=%.3fV V[body]=%.3e V\n",
        r.converged, r.nodeVoltages[2], r.nodeVoltages[4]);
}

// ============================================================
// B3.4 — OSDI diode 反偏（cathode > anode）
// 拓扑：vs(-0.5V on anode) ─ 100Ω ─ anode ─ diode ─ cathode=GND
// 期望：DC 收敛；diode 反向截止（电流 ~ Is = 1e-14 A 量级），
//       limiting 不应把 Vd latch 到正向。
// ============================================================
TEST(EdgeCase, ReverseBiasDiode) {
    std::string libPath = osdiPath("RFSIM_DIODE_LIB", "diode");
    OsdiLibrary tmp; std::string err;
    if (!tmp.load(libPath, err)) GTEST_SKIP() << "diode: " << err;
    auto lib = std::make_shared<OsdiLibrary>(std::move(tmp));
    if (lib->numDescriptors() < 1) GTEST_SKIP() << "no diode descriptor";
    const OsdiDescriptor* desc = lib->descriptors();

    std::vector<std::unique_ptr<DeviceModel>> devs;
    // vs 给反偏：在 anode 上施加 -0.5V，cathode 接地
    devs.push_back(std::make_unique<VoltageSource>("vs", 1, 0, -0.5));
    devs.push_back(std::make_unique<Resistor>("rs", 1, 2, 100.0));

    // 端子序：A, C, dT —— dT 单独节点 + Rth 拉地（与 A3 一致）
    std::vector<NodeId> nodes(desc->num_terminals, 0);
    if (desc->num_terminals > 0) nodes[0] = 2;
    if (desc->num_terminals > 1) nodes[1] = 0;
    if (desc->num_terminals > 2) nodes[2] = 4;
    if (desc->num_terminals > 2)
        devs.push_back(std::make_unique<Resistor>("rth", 4, 0, 1.0));

    Diagnostics diags;
    NodeId base = 5;
    auto dio = std::make_unique<OsdiModel>(
        "d1", nodes, lib, desc, ParamList{}, diodeFullModel());
    if (!dio->initialize(diags, base)) GTEST_SKIP() << "diode init failed";
    devs.push_back(std::move(dio));

    NodeId nN = computeMaxNode(devs);
    DcOpOptions opts;
    opts.gmin.gminSteps = 10;
    opts.maxIterations = 80;
    auto r = solveDcOp(nN, devs, opts);

    ASSERT_TRUE(allFinite(r.nodeVoltages))
        << "reverse-biased diode produced NaN";
    EXPECT_TRUE(r.converged) << "reverse-bias DC failed";
    if (r.converged) {
        // anode 电压应接近 -0.5V（反向电流极小，100Ω 上几乎无压降）。
        // 关键：anode 不能被 limiting "latch" 到 ~+0.7V（典型正向开启）。
        double va = r.nodeVoltages[2];
        EXPECT_LT(va, 0.0)
            << "reverse-bias anode latched positive (latching bug?), V=" << va;
        EXPECT_GT(va, -0.6); // anode ≈ -0.5 ± 1pV·100Ω
    }
    std::fprintf(stderr,
        "[EdgeCase.ReverseBiasDiode] conv=%d V[anode]=%.6e V (vs=-0.5V)\n",
        r.converged, r.nodeVoltages[2]);
}

} // namespace rfsim
