// test_convergence_grid.cpp — plan0620_v2 §B1
//
// 参数扫描收敛率统计 harness：在 (VG, VDD, T) 三维网格上对 BSIM4 共源放大器
// 跑 solveDcOp + solveHbNonlinear，记录 converged / iters / wall_ms 到 CSV。
//
// 网格设计（plan §B1 节选）：
//   - VG  ∈ [0.30, 0.90] step 0.05  → 13 点
//   - VDD ∈ [0.60, 1.50] step 0.10  → 10 点
//   - T   ∈ {250, 300, 400} K       → 3 点
//   合计 = 13 × 10 × 3 = 390 个工作点；DC + HB 各跑一次。
//
// 输出：build/conv_grid_<model>.csv，列：
//   model, vg, vdd, tempK, dc_conv, dc_iters, dc_ms, hb_conv, hb_ms
//
// 断言：
//   - 整体 DC OP 收敛率 ≥ 80%（覆盖深亚阈值与三极管极端区）
//   - 弱非线性窗口（VG ∈ [0.50, 0.80]）DC OP 收敛率 ≥ 95%
//   - HB-NL 在弱非线性窗口收敛率 ≥ 80%（强非线性靠 V2-γ 的 continuation 改进）
//
// 注意：这不是单点功能验证，而是统计回归基线。后续若引入 limiting / 起跳
// 改进，本测试的"收敛率"应当稳定上升或持平，不允许下降。
#include "model/builtin_devices.hpp"
#include "model/osdi_model.hpp"
#include "model/osdi/osdi_library.hpp"
#include "solver/dc_op.hpp"
#include "solver/hb_nonlinear.hpp"
#include "solver/hb_solver.hpp"

#include <gtest/gtest.h>

#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>

using namespace rfsim;

namespace {

double nowMs() {
    using clk = std::chrono::steady_clock;
    static auto t0 = clk::now();
    return std::chrono::duration<double, std::milli>(clk::now() - t0).count();
}

std::string projectRoot() {
    std::string s = RFSIM_TEST_DATA_DIR;
    auto pos = s.find_last_of("/\\");
    if (pos != std::string::npos) s = s.substr(0, pos);
    pos = s.find_last_of("/\\");
    if (pos != std::string::npos) s = s.substr(0, pos);
    return s;
}

std::string bsim4LibPath() {
    if (const char* p = std::getenv("RFSIM_BSIM4_LIB")) return p;
#ifdef _WIN32
    return projectRoot() + "/models/bsim4.dll";
#else
    return projectRoot() + "/models/bsim4.so";
#endif
}

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

ParamList instWL() {
    ParamList p;
    p.push_back({"w", ParamValue{ParamValue::Kind::Number, 1e-6,   "", SourceLoc{}}});
    p.push_back({"l", ParamValue{ParamValue::Kind::Number, 130e-9, "", SourceLoc{}}});
    return p;
}

// 单个工作点的 DC + HB 结果
struct GridPoint {
    double vg = 0.0;
    double vdd = 0.0;
    double tempK = 300.0;
    bool   dcConv = false;
    uint32_t dcIters = 0;
    double dcMs = 0.0;
    bool   hbConv = false;
    double hbMs = 0.0;
};

// 共源放大器：vdd→Rd→drain；vg→gate；source/bulk = GND
// 节点：1 = vdd 网络, 2 = drain, 3 = gate
struct GridRunner {
    std::shared_ptr<OsdiLibrary> lib;
    const OsdiDescriptor* d = nullptr;

    bool load(std::string& whyNot) {
        OsdiLibrary tmp;
        if (!tmp.load(bsim4LibPath(), whyNot)) return false;
        lib = std::make_shared<OsdiLibrary>(std::move(tmp));
        if (lib->numDescriptors() < 1) {
            whyNot = "no descriptors in " + bsim4LibPath();
            return false;
        }
        d = lib->descriptors();
        return true;
    }

    GridPoint runOnce(double vg, double vdd, double tempK) {
        GridPoint pt{vg, vdd, tempK};

        // 每次都重建 device 列表（OsdiClient::init 是一次性）
        std::vector<std::unique_ptr<DeviceModel>> devs;
        devs.push_back(std::make_unique<VoltageSource>("vdd", 1, 0, vdd));
        devs.push_back(std::make_unique<Resistor>("rd", 1, 2, 1000.0));
        auto vgSrc = std::make_unique<VoltageSource>("vg", 3, 0, vg);
        vgSrc->setAcMag(Complex(0.1 * vg, 0.0));  // 10% 小信号
        devs.push_back(std::move(vgSrc));

        auto mos = std::make_unique<OsdiModel>("m1", std::vector<NodeId>{2, 3, 0, 0},
            lib, d, instWL(), bsim4ModelParams());
        mos->setTemperature(tempK);
        Diagnostics diags;
        NodeId internalBase = 4;
        if (!mos->initialize(diags, internalBase)) {
            return pt;  // 默认 unconverged
        }
        NodeId maxN = 3;
        for (NodeId nn : mos->nodes()) if (nn > maxN) maxN = nn;

        // ---- DC OP ----
        {
            auto devsDc = std::move(devs);
            // 把 mos clone 到 dc-only devs 之前先存指针
            // 这里直接 move 进 devsDc：我们把 mos 加进去后再移给 HB。
            // 注：solveDcOp 不会持有 OsdiClient 状态以外的副作用，跑完后
            // 我们重建一个新的 mos 给 HB（限幅状态干净）。
            devsDc.push_back(std::move(mos));
            DcOpOptions opts;
            opts.gmin.gminSteps = 10;
            double t0 = nowMs();
            auto r = solveDcOp(static_cast<uint32_t>(maxN), devsDc, opts);
            double t1 = nowMs();
            pt.dcConv  = r.converged;
            pt.dcIters = r.iterations;
            pt.dcMs    = t1 - t0;
        }

        // ---- HB-NL（重建以重置 limiting）----
        {
            std::vector<std::unique_ptr<DeviceModel>> devsHb;
            devsHb.push_back(std::make_unique<VoltageSource>("vdd", 1, 0, vdd));
            devsHb.push_back(std::make_unique<Resistor>("rd", 1, 2, 1000.0));
            auto vg2 = std::make_unique<VoltageSource>("vg", 3, 0, vg);
            vg2->setAcMag(Complex(0.1 * vg, 0.0));
            devsHb.push_back(std::move(vg2));
            auto mos2 = std::make_unique<OsdiModel>("m1", std::vector<NodeId>{2, 3, 0, 0},
                lib, d, instWL(), bsim4ModelParams());
            mos2->setTemperature(tempK);
            Diagnostics diags2;
            NodeId base2 = 4;
            if (!mos2->initialize(diags2, base2)) return pt;
            NodeId maxN2 = 3;
            for (NodeId nn : mos2->nodes()) if (nn > maxN2) maxN2 = nn;
            devsHb.push_back(std::move(mos2));

            HbConfig cfg; cfg.fundamental = 1e6; cfg.numHarmonics = 1;
            HbNlOptions opts;
            opts.sourceSteps = 0;
            opts.gmin.gmin = 1e-12;
            opts.dvmax = 0.5;
            opts.maxIter = 50;
            // V2-γ post-S2: BSIM4 等 OSDI 强非线性器件在 S2 grid (NH∈{3..15}) 上
            // 单点起跳难以收敛，开启自动同伦让 solver 自适应到 4×4 schedule。
            opts.autoHomotopy = true;
            double t0 = nowMs();
            auto r = solveHbNonlinear(static_cast<uint32_t>(maxN2), devsHb, cfg, nullptr, opts);
            double t1 = nowMs();
            pt.hbConv = r.converged;
            pt.hbMs   = t1 - t0;
        }

        return pt;
    }
};

void writeCsv(const std::string& outPath, const std::string& modelTag,
              const std::vector<GridPoint>& pts) {
    std::ofstream ofs(outPath);
    if (!ofs) return;
    ofs << "model,vg,vdd,tempK,dc_conv,dc_iters,dc_ms,hb_conv,hb_ms\n";
    for (const auto& p : pts) {
        ofs << modelTag << ','
            << p.vg << ',' << p.vdd << ',' << p.tempK << ','
            << (p.dcConv ? 1 : 0) << ','
            << p.dcIters << ',' << p.dcMs << ','
            << (p.hbConv ? 1 : 0) << ','
            << p.hbMs << '\n';
    }
}

bool inWeakNonlinearWindow(double vg) {
    return vg >= 0.50 - 1e-9 && vg <= 0.80 + 1e-9;
}

} // namespace

// 主测试：BSIM4 (VG × VDD × T) 网格扫描
TEST(ConvergenceGrid, Bsim4CommonSource) {
    GridRunner runner;
    std::string why;
    if (!runner.load(why)) {
        GTEST_SKIP() << "cannot load bsim4: " << why;
    }

    std::vector<double> vgGrid;
    for (double v = 0.30; v <= 0.90 + 1e-9; v += 0.05) vgGrid.push_back(v);
    std::vector<double> vddGrid;
    for (double v = 0.60; v <= 1.50 + 1e-9; v += 0.10) vddGrid.push_back(v);
    const std::vector<double> tGrid{250.0, 300.0, 400.0};

    std::vector<GridPoint> pts;
    pts.reserve(vgGrid.size() * vddGrid.size() * tGrid.size());
    for (double T : tGrid) {
        for (double vdd : vddGrid) {
            for (double vg : vgGrid) {
                pts.push_back(runner.runOnce(vg, vdd, T));
            }
        }
    }

    // CSV 落盘 — 路径相对当前工作目录（gtest 运行时通常是 build/）
    writeCsv("conv_grid_bsim4.csv", "bsim4", pts);

    // 统计
    size_t total = pts.size();
    size_t dcOk = 0, hbOk = 0;
    size_t weakTotal = 0, weakDcOk = 0, weakHbOk = 0;
    for (const auto& p : pts) {
        if (p.dcConv) ++dcOk;
        if (p.hbConv) ++hbOk;
        if (inWeakNonlinearWindow(p.vg)) {
            ++weakTotal;
            if (p.dcConv) ++weakDcOk;
            if (p.hbConv) ++weakHbOk;
        }
    }
    double dcRate     = static_cast<double>(dcOk)     / static_cast<double>(total);
    double hbRate     = static_cast<double>(hbOk)     / static_cast<double>(total);
    double weakDcRate = static_cast<double>(weakDcOk) / static_cast<double>(weakTotal);
    double weakHbRate = static_cast<double>(weakHbOk) / static_cast<double>(weakTotal);

    std::fprintf(stderr,
        "[ConvergenceGrid] bsim4: %zu points; DC=%.1f%% (weak=%.1f%%), HB=%.1f%% (weak=%.1f%%)\n",
        total, 100.0 * dcRate, 100.0 * weakDcRate,
        100.0 * hbRate, 100.0 * weakHbRate);

    EXPECT_GE(dcRate, 0.80) << "BSIM4 DC OP overall convergence below 80%";
    EXPECT_GE(weakDcRate, 0.95) << "BSIM4 DC OP convergence in weak-nonlinear window below 95%";
    EXPECT_GE(weakHbRate, 0.80) << "BSIM4 HB-NL convergence in weak-nonlinear window below 80%";
}
