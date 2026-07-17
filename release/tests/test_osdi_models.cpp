// test_osdi_models.cpp — OSDI model matrix coverage (plan0620_v2 V2-α)
//
// 目标：把 8 个 OSDI 模型在 DC OP / HB-NL / Shooting 三层的"格子"逐步填满。
// 每个测试在模型 DLL 缺失时显式 GTEST_SKIP，使 CI 在不同环境下都能给出
// 明确的 PASS / SKIP 状态。最终的"模型 × 层"小结由 OsdiMatrixSummary
// 的析构函数在程序退出前打印（A5 表格化输出）。

#include "model/osdi/osdi_library.hpp"
#include "model/osdi_model.hpp"
#include "model/builtin_devices.hpp"
#include "solver/dc_op.hpp"
#include "solver/hb_nonlinear.hpp"
#include "solver/shooting.hpp"

#include <gtest/gtest.h>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

using namespace rfsim;

namespace {

#ifndef RFSIM_TEST_DATA_DIR
#define RFSIM_TEST_DATA_DIR "."
#endif

std::string projectRoot() {
    std::string s = RFSIM_TEST_DATA_DIR;
    auto pos = s.find_last_of("/\\");
    if (pos != std::string::npos) s = s.substr(0, pos); // <project>/tests
    pos = s.find_last_of("/\\");
    if (pos != std::string::npos) s = s.substr(0, pos); // <project>
    return s;
}

std::string modelPath(const char* envVar, const char* dllName) {
    if (const char* p = std::getenv(envVar)) return p;
#ifdef _WIN32
    return projectRoot() + "/models/" + dllName + ".dll";
#else
    return projectRoot() + "/models/" + dllName + ".so";
#endif
}

ParamValue numParam(double v) {
    return ParamValue{ParamValue::Kind::Number, v, "", SourceLoc{}};
}

void addParam(ParamList& p, const char* n, double v) {
    p.push_back({n, numParam(v)});
}

// ---- 每模型的"最小可工作"模型卡 helper ---------------------------------
// OpenVAF 在 descriptor 内置默认值，所以多数情况下可以传空 ParamList，
// 但部分模型在偏置点 (Vgs≈Vth) 处对 vth0/u0/toxe 极敏感，我们仍按 bsim4
// 模板给出近似 130nm 工艺值。

ParamList bsim4Params() {
    ParamList p;
    addParam(p, "toxe", 3e-9); addParam(p, "toxp", 3e-9);
    addParam(p, "vth0", 0.5); addParam(p, "k1", 0.5); addParam(p, "k2", 0.0); addParam(p, "k3", 0.0);
    addParam(p, "dvt0", 1.0); addParam(p, "dvt1", 2.0); addParam(p, "dvt2", -0.032);
    addParam(p, "u0", 0.045); addParam(p, "ua", -1e-10); addParam(p, "ub", 0.0);
    addParam(p, "vsat", 1.5e5); addParam(p, "rdsw", 160); addParam(p, "nfactor", 1.2);
    addParam(p, "cgso", 0.1e-9); addParam(p, "cgdo", 0.1e-9); addParam(p, "cgbo", 0.0);
    addParam(p, "cjs", 1e-3); addParam(p, "cjd", 1e-3);
    addParam(p, "cjsws", 1e-10); addParam(p, "cjswd", 1e-10);
    addParam(p, "mjs", 0.5); addParam(p, "mjd", 0.5);
    addParam(p, "mjsws", 0.33); addParam(p, "mjswd", 0.33);
    addParam(p, "pbs", 0.88); addParam(p, "pbd", 0.88);
    addParam(p, "pbsws", 0.88); addParam(p, "pbswd", 0.88);
    return p;
}

// bsim4soi / bsimsoi 的 Verilog-A 与 BSIM4 共享大部分参数语义；先复用 bsim4 模板。
// 当前 V2-α 没有实例化 bsim4soi / bsimsoi 的 .model 卡（仅在 BSIMSOI DC OP 用了
// 内置默认），先用 [[maybe_unused]] 抑制警告，等 V2-β 接入实际参数扫描时再启用。
[[maybe_unused]] ParamList bsim4soiParams() { return bsim4Params(); }
[[maybe_unused]] ParamList bsimsoiParams()  { return bsim4Params(); }

// EKV / BSIM-CMG 用其内置默认（descriptor 已编译 default）；空表 = OpenVAF 默认。
ParamList ekvParams()      { return ParamList{}; }
ParamList bsimcmgParams()  { return ParamList{}; }
ParamList nmosShParams()   { return ParamList{}; }

// 完整 diode（不是 simple_diode）：包含 $simparam("minr",...) 的参数表达式，
// 在 OsdiSimParas 为空时若不显式提供 minr，OpenVAF 生成的初始化代码会解引用 NULL。
ParamList diodeFullParams() {
    ParamList p;
    addParam(p, "minr", 1e-3);
    addParam(p, "is", 1e-14);
    addParam(p, "n", 1.0);
    addParam(p, "vj", 1.0);
    addParam(p, "m", 0.5);
    return p;
}

ParamList instWL() {
    ParamList p;
    addParam(p, "w", 1e-6);
    addParam(p, "l", 130e-9);
    return p;
}

// ---- 跨测试结果汇总（A5 表格化跑分）------------------------------------
struct ModelRow {
    std::string model;
    std::string dcop = "-";
    std::string hb = "-";
    std::string shoot = "-";
    int dcopIters = 0;
    int hbIters = 0;
    double dcopMs = 0;
    double hbMs = 0;
    double shootMs = 0;
};

class OsdiMatrixSummary {
public:
    static OsdiMatrixSummary& get() {
        static OsdiMatrixSummary s;
        return s;
    }
    void update(const std::string& m, const std::function<void(ModelRow&)>& fn) {
        std::lock_guard<std::mutex> g(mu_);
        auto& row = rows_[m];
        row.model = m;
        fn(row);
    }
    ~OsdiMatrixSummary() {
        std::lock_guard<std::mutex> g(mu_);
        if (rows_.empty()) return;
        std::fprintf(stderr,
            "\n=== OSDI Model Matrix Summary (plan0620_v2 V2-α) ===\n");
        std::fprintf(stderr,
            "%-15s | %-6s | %-6s | %-6s | %6s | %6s | %8s | %8s\n",
            "model", "dcop", "hb", "shoot", "dcIt", "hbIt", "dcMs", "hbMs");
        std::fprintf(stderr,
            "----------------|--------|--------|--------|--------|--------|----------|----------\n");
        for (auto& [k, r] : rows_) {
            std::fprintf(stderr,
                "%-15s | %-6s | %-6s | %-6s | %6d | %6d | %8.1f | %8.1f\n",
                k.c_str(),
                r.dcop.c_str(), r.hb.c_str(), r.shoot.c_str(),
                r.dcopIters, r.hbIters, r.dcopMs, r.hbMs);
        }
        std::fprintf(stderr, "\n");
    }
private:
    std::mutex mu_;
    std::map<std::string, ModelRow> rows_;
};

double nowMs() {
    using namespace std::chrono;
    return duration<double, std::milli>(
        steady_clock::now().time_since_epoch()).count();
}

// ---- 共源 DC OP 通用执行器 ---------------------------------------------
// 拓扑：VDD(1V)─Rd(1k)─drain ; gate=VGS ; source=body=GND
// 返回收敛/迭代/wall。
struct DcOpRunResult {
    bool converged;
    uint32_t iters;
    double wallMs;
    std::vector<double> nodeV;
};

DcOpRunResult runCommonSourceDcOp(
        const std::shared_ptr<OsdiLibrary>& lib,
        const OsdiDescriptor* d,
        const ParamList& modelP,
        double vdd, double vgs)
{
    std::vector<std::unique_ptr<DeviceModel>> devs;
    devs.push_back(std::make_unique<VoltageSource>("vdd", 1, 0, vdd));   // n1
    devs.push_back(std::make_unique<Resistor>("rd", 1, 2, 1000.0));      // drain at n2
    devs.push_back(std::make_unique<VoltageSource>("vg", 3, 0, vgs));    // gate n3

    // 节点拓扑：drain=2, gate=3, source=0, bulk=0
    std::vector<NodeId> nodes(d->num_terminals, 0);
    if (d->num_terminals > 0) nodes[0] = 2;
    if (d->num_terminals > 1) nodes[1] = 3;
    auto mos = std::make_unique<OsdiModel>("m1", nodes, lib, d, instWL(), modelP);
    Diagnostics diags;
    NodeId internalBase = 4;
    if (!mos->initialize(diags, internalBase)) {
        return {false, 0, 0.0, {}};
    }
    // collapse 之后，模型可能仍然引用 internalBase 之前若干 NodeId。
    // 用 mos->nodes() 中的最大值作为 numNodes，确保 MNA 矩阵不会越界 stamp。
    NodeId maxN = 3;
    for (NodeId nn : mos->nodes()) if (nn > maxN) maxN = nn;
    devs.push_back(std::move(mos));

    DcOpOptions opts;
    opts.gmin.gminSteps = 10;
    double t0 = nowMs();
    auto r = solveDcOp(static_cast<uint32_t>(maxN), devs, opts);
    double t1 = nowMs();
    return {r.converged, r.iterations, t1 - t0, r.nodeVoltages};
}

// ---- 共源 HB-NL 通用执行器 ---------------------------------------------
struct HbRunResult {
    bool converged;
    uint32_t iters;
    double wallMs;
};

HbRunResult runCommonSourceHbNl(
        const std::shared_ptr<OsdiLibrary>& lib,
        const OsdiDescriptor* d,
        const ParamList& modelP,
        double vdd, double vgs, double acMag)
{
    std::vector<std::unique_ptr<DeviceModel>> devs;
    devs.push_back(std::make_unique<VoltageSource>("vdd", 1, 0, vdd));
    devs.push_back(std::make_unique<Resistor>("rd", 1, 2, 1000.0));
    auto vg = std::make_unique<VoltageSource>("vg", 3, 0, vgs);
    vg->setAcMag(Complex(acMag, 0.0));
    devs.push_back(std::move(vg));

    std::vector<NodeId> nodes(d->num_terminals, 0);
    if (d->num_terminals > 0) nodes[0] = 2;
    if (d->num_terminals > 1) nodes[1] = 3;
    auto mos = std::make_unique<OsdiModel>("m1", nodes, lib, d, instWL(), modelP);
    Diagnostics diags;
    NodeId internalBase = 4;
    if (!mos->initialize(diags, internalBase)) {
        return {false, 0, 0.0};
    }
    NodeId maxN = 3;
    for (NodeId nn : mos->nodes()) if (nn > maxN) maxN = nn;
    devs.push_back(std::move(mos));

    HbConfig cfg; cfg.fundamental = 1e6; cfg.numHarmonics = 1;
    HbNlOptions opts;
    opts.sourceSteps = 0;
    opts.gmin.gmin = 1e-12;
    opts.dvmax = 0.5;
    opts.maxIter = 50;
    double t0 = nowMs();
    auto r = solveHbNonlinear(static_cast<uint32_t>(maxN), devs, cfg, nullptr, opts);
    double t1 = nowMs();
    return {r.converged, 0, t1 - t0}; // HbResult 没有公开 iter 字段，先填 0
}

// ---- 公共加载 helper ----------------------------------------------------
struct LoadedModel {
    bool ok;
    std::shared_ptr<OsdiLibrary> lib;
    const OsdiDescriptor* d = nullptr;
    std::string skipReason;
};

LoadedModel loadOsdi(const char* envVar, const char* dllName) {
    LoadedModel L{false, {}, nullptr, {}};
    OsdiLibrary lib;
    std::string err;
    std::string path = modelPath(envVar, dllName);
    if (!lib.load(path, err)) {
        L.skipReason = "cannot load " + path + ": " + err;
        return L;
    }
    L.lib = std::make_shared<OsdiLibrary>(std::move(lib));
    if (L.lib->numDescriptors() < 1) {
        L.skipReason = "no descriptors in " + path;
        return L;
    }
    L.d = L.lib->descriptors();
    L.ok = true;
    return L;
}

} // namespace

// ============================================================
// A1 — bsimsoi DC OP 收敛
// ============================================================
TEST(OsdiMatrix, BsimsoiDcOpConverges) {
    auto L = loadOsdi("RFSIM_BSIMSOI_LIB", "bsimsoi");
    if (!L.ok) GTEST_SKIP() << L.skipReason;

    auto rr = runCommonSourceDcOp(L.lib, L.d, ParamList{}, 1.0, 0.6);
    OsdiMatrixSummary::get().update("bsimsoi", [&](ModelRow& r){
        r.dcop = rr.converged ? "PASS" : "FAIL";
        r.dcopIters = static_cast<int>(rr.iters);
        r.dcopMs = rr.wallMs;
    });
    EXPECT_TRUE(rr.converged) << "bsimsoi DC OP did not converge";
    if (rr.converged) {
        ASSERT_GE(rr.nodeV.size(), 4u);
        for (double v : rr.nodeV) EXPECT_TRUE(std::isfinite(v));
        EXPECT_LT(std::fabs(rr.nodeV[1]), 2.0);
        EXPECT_LT(std::fabs(rr.nodeV[2]), 2.0);
    }
}

// ============================================================
// A2.1 — ekv 共源 HB-NL 收敛
// ============================================================
TEST(OsdiMatrix, EkvHbNlCommonSource) {
    auto L = loadOsdi("RFSIM_EKV_LIB", "ekv");
    if (!L.ok) GTEST_SKIP() << L.skipReason;

    auto rr = runCommonSourceHbNl(L.lib, L.d, ekvParams(), 1.0, 0.55, 0.05);
    OsdiMatrixSummary::get().update("ekv", [&](ModelRow& r){
        r.hb = rr.converged ? "PASS" : "FAIL";
        r.hbIters = static_cast<int>(rr.iters);
        r.hbMs = rr.wallMs;
    });
    EXPECT_TRUE(rr.converged) << "ekv HB-NL did not converge";
}

// ============================================================
// A2.2 — bsim4soi 共源 HB-NL 收敛
// ============================================================
TEST(OsdiMatrix, Bsim4soiHbNlCommonSource) {
    auto L = loadOsdi("RFSIM_BSIM4SOI_LIB", "bsim4soi");
    if (!L.ok) GTEST_SKIP() << L.skipReason;

    auto rr = runCommonSourceHbNl(L.lib, L.d, ParamList{}, 1.0, 0.55, 0.05);
    OsdiMatrixSummary::get().update("bsim4soi", [&](ModelRow& r){
        r.hb = rr.converged ? "PASS" : "FAIL";
        r.hbIters = static_cast<int>(rr.iters);
        r.hbMs = rr.wallMs;
    });
    EXPECT_TRUE(rr.converged) << "bsim4soi HB-NL did not converge";
}

// ============================================================
// A2.3 — bsimcmg 共源 HB-NL 收敛
// ============================================================
TEST(OsdiMatrix, BsimcmgHbNlCommonSource) {
    auto L = loadOsdi("RFSIM_BSIMCMG_LIB", "bsimcmg");
    if (!L.ok) GTEST_SKIP() << L.skipReason;

    auto rr = runCommonSourceHbNl(L.lib, L.d, bsimcmgParams(), 1.0, 0.55, 0.05);
    OsdiMatrixSummary::get().update("bsimcmg", [&](ModelRow& r){
        r.hb = rr.converged ? "PASS" : "FAIL";
        r.hbIters = static_cast<int>(rr.iters);
        r.hbMs = rr.wallMs;
    });
    EXPECT_TRUE(rr.converged) << "bsimcmg HB-NL did not converge";
}

// ============================================================
// A3 — diode 完整模型 DC + HB（半波整流 / 偏置点）
// ============================================================
namespace {

// 拓扑：V+(0.7V or AC)──R(100Ω)──anode──diode──GND
// 节点：1 = source, 2 = anode, 3 (cathode) = 0 (GND)
struct DiodeRunResult {
    bool converged;
    double wallMs;
    std::vector<double> nodeV;
    double h1Anode = 0.0;  // HB 用：anode 节点基波幅值
};

DiodeRunResult runDiodeDc(const std::shared_ptr<OsdiLibrary>& lib,
                          const OsdiDescriptor* d,
                          const ParamList& modelP,
                          double vSrc) {
    std::vector<std::unique_ptr<DeviceModel>> devs;
    devs.push_back(std::make_unique<VoltageSource>("vs", 1, 0, vSrc));
    devs.push_back(std::make_unique<Resistor>("rs", 1, 2, 100.0));

    // diode.va 端子序：A (anode), C (cathode), dT (thermal)。
    // dT 是 thermal discipline，需要一个可识别的全局 NodeId（不能直接接地，
    // 否则 OSDI 模型在 eval 时 node_mapping 全零会踩 prev_solve[0]）。
    // 给它单独一个节点 nDT=4，再用 R_th 拉到地。
    std::vector<NodeId> nodes(d->num_terminals, 0);
    if (d->num_terminals > 0) nodes[0] = 2;     // anode
    if (d->num_terminals > 1) nodes[1] = 0;     // cathode → GND
    if (d->num_terminals > 2) nodes[2] = 4;     // dT thermal
    if (d->num_terminals > 2) {
        devs.push_back(std::make_unique<Resistor>("rth_test", 4, 0, 1.0));
    }
    auto dio = std::make_unique<OsdiModel>("d1", nodes, lib, d, ParamList{}, modelP);
    Diagnostics diags;
    NodeId internalBase = 5;
    if (!dio->initialize(diags, internalBase)) {
        return {false, 0.0, {}};
    }
    NodeId maxN = 4;
    for (NodeId nn : dio->nodes()) if (nn > maxN) maxN = nn;
    devs.push_back(std::move(dio));

    DcOpOptions opts;
    opts.gmin.gminSteps = 10;
    double t0 = nowMs();
    auto r = solveDcOp(static_cast<uint32_t>(maxN), devs, opts);
    double t1 = nowMs();
    return {r.converged, t1 - t0, r.nodeVoltages};
}

DiodeRunResult runDiodeHb(const std::shared_ptr<OsdiLibrary>& lib,
                          const OsdiDescriptor* d,
                          const ParamList& modelP,
                          double vBias, double acMag) {
    std::vector<std::unique_ptr<DeviceModel>> devs;
    auto vs = std::make_unique<VoltageSource>("vs", 1, 0, vBias);
    vs->setAcMag(Complex(acMag, 0.0));
    devs.push_back(std::move(vs));
    devs.push_back(std::make_unique<Resistor>("rs", 1, 2, 100.0));

    // 与 runDiodeDc 保持一致：A=2, C=0, dT=4 + R_th
    std::vector<NodeId> nodes(d->num_terminals, 0);
    if (d->num_terminals > 0) nodes[0] = 2;
    if (d->num_terminals > 1) nodes[1] = 0;
    if (d->num_terminals > 2) nodes[2] = 4;
    if (d->num_terminals > 2) {
        devs.push_back(std::make_unique<Resistor>("rth_test", 4, 0, 1.0));
    }
    auto dio = std::make_unique<OsdiModel>("d1", nodes, lib, d, ParamList{}, modelP);
    Diagnostics diags;
    NodeId internalBase = 5;
    if (!dio->initialize(diags, internalBase)) return {false, 0.0, {}};
    NodeId maxN = 4;
    for (NodeId nn : dio->nodes()) if (nn > maxN) maxN = nn;
    devs.push_back(std::move(dio));

    HbConfig cfg; cfg.fundamental = 1e6; cfg.numHarmonics = 1;
    HbNlOptions opts;
    // 沿用已验证的 simple_diode 整流器收敛配方：source-stepping 慢慢加大 AC，
    // 配合较大的 gmin 提供分流。完整 diode_va（带热端口与 $simparam）相比
    // simple_diode 非线性更强，一旦直接给 0.7V 大偏置会让 exp(vd/vt) 发散。
    opts.sourceSteps = 10;
    opts.gmin.gmin = 1e-2;
    opts.gmin.gminSteps = 0;
    opts.dvmax = 0.5;
    opts.maxIter = 80;
    double t0 = nowMs();
    auto r = solveHbNonlinear(static_cast<uint32_t>(maxN), devs, cfg, nullptr, opts);
    double t1 = nowMs();
    DiodeRunResult out;
    out.converged = r.converged;
    out.wallMs = t1 - t0;
    if (r.converged && r.nodeVoltages.size() > 2 && !r.nodeVoltages[2].v.empty()) {
        // anode = 节点 2，HB 解的 v[1] 是基波复数幅值
        if (r.nodeVoltages[2].v.size() > 1)
            out.h1Anode = std::abs(r.nodeVoltages[2].v[1]);
    }
    return out;
}

} // namespace

TEST(OsdiMatrix, DiodeFullDcOpConverges) {
    auto L = loadOsdi("RFSIM_DIODE_LIB", "diode");
    if (!L.ok) GTEST_SKIP() << L.skipReason;

    auto rr = runDiodeDc(L.lib, L.d, diodeFullParams(), 0.7);
    OsdiMatrixSummary::get().update("diode", [&](ModelRow& r){
        r.dcop = rr.converged ? "PASS" : "FAIL";
        r.dcopMs = rr.wallMs;
    });
    EXPECT_TRUE(rr.converged) << "diode DC OP did not converge";
    if (rr.converged) {
        ASSERT_GE(rr.nodeV.size(), 3u);
        // 0.7V 输入下，二极管应导通：anode 电压 ~0.5–0.7V
        EXPECT_GT(rr.nodeV[2], 0.0);
        EXPECT_LT(rr.nodeV[2], 0.75);
    }
}

TEST(OsdiMatrix, DiodeFullHbNlConverges) {
    auto L = loadOsdi("RFSIM_DIODE_LIB", "diode");
    if (!L.ok) GTEST_SKIP() << L.skipReason;

    // 0V DC 偏置 + 1V AC 驱动 + source-stepping，是 OSDI diode_va 在
    // gmin=1e-2 下的稳态收敛配方（参见 test_hb_nl 的 DiodeRectifierContinuation）。
    auto rr = runDiodeHb(L.lib, L.d, diodeFullParams(), 0.0, 1.0);
    OsdiMatrixSummary::get().update("diode", [&](ModelRow& r){
        r.hb = rr.converged ? "PASS" : "FAIL";
        r.hbMs = rr.wallMs;
    });
    EXPECT_TRUE(rr.converged) << "diode HB-NL did not converge";
    if (rr.converged) {
        // 半波整流：anode 节点的基波幅值必须显著非零（drive=1V，
        // 经 R=100Ω 与导通二极管分压，H1 至少在 50mV 以上）
        EXPECT_GT(rr.h1Anode, 0.05)
            << "diode HB rectification yielded weak H1 (" << rr.h1Anode << " V)";
    }
}

// ============================================================
// A4 — nmos_sh：自定义 short-channel NMOS（DC + 小信号 HB）
// ============================================================
TEST(OsdiMatrix, NmosShDcOpConverges) {
    auto L = loadOsdi("RFSIM_NMOSSH_LIB", "nmos_sh");
    if (!L.ok) GTEST_SKIP() << L.skipReason;

    // nmos_sh 端子数未知；runCommonSourceDcOp 已根据 num_terminals 自适应
    auto rr = runCommonSourceDcOp(L.lib, L.d, nmosShParams(), 1.0, 0.6);
    OsdiMatrixSummary::get().update("nmos_sh", [&](ModelRow& r){
        r.dcop = rr.converged ? "PASS" : "FAIL";
        r.dcopIters = static_cast<int>(rr.iters);
        r.dcopMs = rr.wallMs;
    });
    EXPECT_TRUE(rr.converged) << "nmos_sh DC OP did not converge";
}

TEST(OsdiMatrix, NmosShHbNlConverges) {
    auto L = loadOsdi("RFSIM_NMOSSH_LIB", "nmos_sh");
    if (!L.ok) GTEST_SKIP() << L.skipReason;

    auto rr = runCommonSourceHbNl(L.lib, L.d, nmosShParams(), 1.0, 0.55, 0.05);
    OsdiMatrixSummary::get().update("nmos_sh", [&](ModelRow& r){
        r.hb = rr.converged ? "PASS" : "FAIL";
        r.hbMs = rr.wallMs;
    });
    EXPECT_TRUE(rr.converged) << "nmos_sh HB-NL did not converge";
}
