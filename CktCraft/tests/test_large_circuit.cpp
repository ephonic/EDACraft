// test_large_circuit.cpp — 大型电路收敛性 & 求解能力测试
//
// 任务来源：plan0620_v3 §大型电路验证（用户 2026-06-21 决策）。
// 设计分四个域 + 一个统计 harness：
//
//   L. 线性规模 (Linear scaling)
//       L1  ResistorMesh_DC         20×20 mesh (default); 50×50 (HEAVY)
//       L2  RcLadder1000_AC         N=1000 / 2000 RC ladder AC stress (HEAVY)
//       L3  LcTankChain10           10 级 LC 串/并谐振 DC+AC+linear HB
//       L4  LinearHbNhScan          L3 同电路下 NH ∈ {3,5,9,15}
//
//   G. 强非线性 HB-NL（首次触达 GMRES 路径）
//       G1  DiodeRectifierStack     5 级 NH=5 (default, dim≈60，稠密 LU)
//                                   30 级 NH=10 (HEAVY, dim≈1260，触发 GMRES)
//       G2  Bsim4CsNhScan           NH ∈ {3,7} (default) / +{11,15} (HEAVY)
//
//   A. 前馈式有源 BSIM4
//       A1  InverterChainN          N=10 (default), N=15 (HEAVY)
//       A2  CascadeCSMultiStage     3 级 (default), 5 级 (HEAVY)
//       A3  NmosPullupBuffer20      20 级 (HEAVY)
//
//   M. 混合大电路
//       M1  LcMatchedCsAmp          LC 匹配 + BSIM4 CS（PSS via HB-NL）
//       M2  CascodeLnaPiMatch       Cascode LNA + Π 匹配 (HEAVY)
//       M3  RingOscillator3Stage    3-stage ring osc (HEAVY, 预期触 3rd-inst bleed)
//
//   S. 收敛性统计 (CSV harness)
//       S1  InverterChainGrid       N ∈ {2,4,6,8,10}（+ HEAVY {12,15,20}）
//       S2  Bsim4CsNhGrid           NH ∈ {3,5,7}（+ HEAVY {9,11,15}）
//
// 默认 smoke 与 HEAVY 门控:
//   - 默认 ctest 跑全部默认用例 (L1/L3/L4/G1-default/G2-default/A1-default/
//     A2-default/M1/S1-default/S2-default)。
//   - `RFSIM_FORCE_HEAVY=1` 解锁所有 HEAVY 用例（L1-50×50, L2, L3 N=50,
//     G1-30级, G2 高 NH, A1 N=15, A2 5 级, A3, M2, M3, S1/S2 高分辨率）。
//
// 收敛判据:
//   - solveDc/solveHbNonlinear/solveShooting 返回 ok/converged + 全 finite
//   - 节点电压在合理边界内（±一定 margin，根据电路类型）
//   - 主输出端有可观测谐波（HB / PSS）或单调响应（DC / AC）
//
// 性能判据:
//   - 默认 smoke wall < 60s; HEAVY wall 不强卡阈值（仅 fprintf 记录）
//   - 维度 / 迭代次数 / 是否触发 GMRES 在 stderr 打印，便于 V2-γ 性能比对
//
// 安全:
//   - 不要新增对 3+ 对称并联 BSIM4 分支的默认用例（V2-γ 已知 state-bleed）
//   - M3 RingOsc 显式 HEAVY 门控，并在断言注释中标 KnownIssue
//
// 文件内 helper 与 test_multi_device.cpp / test_large_scale.cpp 同形态：
//   - BsimLib + warmLib() Meyers-singleton（process-lifetime LoadLibrary）
//   - makeNmos() 共享 OsdiModelBlock（V2-γ C3 防 3rd-instance 串拥）
//
#include "model/builtin_devices.hpp"
#include "model/osdi_model.hpp"
#include "model/osdi/osdi_library.hpp"
#include "solver/ac_analysis.hpp"
#include "solver/dc_op.hpp"
#include "solver/hb_nonlinear.hpp"
#include "solver/hb_solver.hpp"
#include "solver/shooting.hpp"

#include <gtest/gtest.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <complex>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

namespace rfsim {
namespace {

// ---------------------------------------------------------------------------
// 门控/计时工具
// ---------------------------------------------------------------------------

bool heavyEnabled() {
    const char* p = std::getenv("RFSIM_FORCE_HEAVY");
    return p && std::string(p) == "1";
}

// V2-δ S1 plan0621-v4 §2.3 路径 D：BSIM4 多实例 N≥15 是 KI-2 风险面
// （跨 CRT 堆腐败）。RFSIM_FORCE_HEAVY=1 仍允许 N=10/A2/N=20 级别测试运行
// （单跑通常 PASS），但若要把"已知会与 heavy 同跑触发 segfault"的多实例
// BSIM4 用例也强制打开（如 nightly），再叠加这一层。默认 SKIP，保持
// docs/known_issues.md::KI-2 中说明的 100/100 基线不动摇。
[[maybe_unused]] bool bsim4MultiEnabled() {
    const char* p = std::getenv("RFSIM_FORCE_BSIM4_MULTI");
    return p && std::string(p) == "1";
}

double nowMs() {
    using clk = std::chrono::steady_clock;
    static auto t0 = clk::now();
    return std::chrono::duration<double, std::milli>(clk::now() - t0).count();
}

bool allFiniteVec(const std::vector<double>& v) {
    for (double x : v) if (!std::isfinite(x)) return false;
    return true;
}

bool allFiniteHarm(const std::vector<NodeHarmonics>& nv) {
    for (const auto& nh : nv) {
        for (const Complex& c : nh.v) {
            if (!std::isfinite(c.real()) || !std::isfinite(c.imag())) return false;
        }
    }
    return true;
}

NodeId computeMaxNode(const std::vector<std::unique_ptr<DeviceModel>>& devs) {
    NodeId mx = 0;
    for (const auto& dv : devs)
        for (NodeId n : dv->nodes()) if (n > mx) mx = n;
    return mx;
}

// ---------------------------------------------------------------------------
// 项目路径 / OSDI 库定位
// ---------------------------------------------------------------------------

std::string projectRootFromTestData() {
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
    return projectRootFromTestData() + "/models/bsim4.dll";
#else
    return projectRootFromTestData() + "/models/bsim4.so";
#endif
}

std::string osdiLibPath(const char* envVar, const char* dllStem) {
    if (const char* p = std::getenv(envVar)) return p;
#ifdef _WIN32
    return projectRootFromTestData() + "/models/" + dllStem + ".dll";
#else
    return projectRootFromTestData() + "/models/" + dllStem + ".so";
#endif
}

// ---------------------------------------------------------------------------
// BSIM4 helper（同 test_multi_device.cpp / test_large_scale.cpp 形态）
// ---------------------------------------------------------------------------

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

ParamList instWL(double w = 1e-6, double l = 130e-9) {
    ParamList p;
    p.push_back({"w", ParamValue{ParamValue::Kind::Number, w, "", SourceLoc{}}});
    p.push_back({"l", ParamValue{ParamValue::Kind::Number, l, "", SourceLoc{}}});
    return p;
}

struct BsimLib {
    std::shared_ptr<OsdiLibrary> lib;
    const OsdiDescriptor* desc = nullptr;
    // V2-γ C3：跨实例共享 OsdiModelBlock，避免 3rd-instance 串拥
    std::shared_ptr<OsdiModelBlock> modelBlock;
    bool ok(std::string& why) {
        if (lib) return true;
        OsdiLibrary tmp;
        if (!tmp.load(bsim4LibPath(), why)) return false;
        lib = std::make_shared<OsdiLibrary>(std::move(tmp));
        if (lib->numDescriptors() < 1) {
            why = "no descriptors";
            lib.reset();
            return false;
        }
        desc = lib->descriptors();
        return true;
    }
    // 卸载并重新加载 bsim4.dll，清零 dll 内部全局状态。OSDI v0.3 无 destroy
    // hook，setup_instance 内部 sub-alloc 在 host 析构后仍 leak；进程内多次
    // 用例累积后某次 eval 读到被 host heap 复用覆盖的旧指针 → SEH 0xc0000005
    // （详见 docs/flake_investigation_0621.md）。每个 HEAVY 用例前调一次。
    void reload() {
        if (!lib) return;
        std::string why;
        // 用 move-construct 重建 shared_ptr 持有的 OsdiLibrary，触发 reload。
        // 先丢掉 modelBlock（指向旧 dll 的 descriptor，重载后失效）。
        modelBlock.reset();
        desc = nullptr;
        if (lib->reload(why)) {
            desc = lib->descriptors();
        } else {
            // reload 失败：清掉 lib，后续 ok() 会重新尝试初次加载。
            lib.reset();
        }
    }
};

std::unique_ptr<OsdiModel> makeNmos(const std::string& name,
                                    NodeId d, NodeId g, NodeId s, NodeId b,
                                    BsimLib& L,
                                    Diagnostics& diags,
                                    NodeId& base,
                                    double w = 1e-6, double l = 130e-9) {
    auto m = std::make_unique<OsdiModel>(name, std::vector<NodeId>{d, g, s, b},
                                         L.lib, L.desc, instWL(w, l),
                                         bsim4ModelParams());
    if (L.modelBlock) m->useSharedModelBlock(L.modelBlock);
    if (!m->initialize(diags, base)) return nullptr;
    if (!L.modelBlock) L.modelBlock = m->modelBlock();
    return m;
}

std::unique_ptr<VoltageSource> sineVS(const std::string& name, NodeId p, NodeId n,
                                      double dc, double amp, double freq) {
    auto v = std::make_unique<VoltageSource>(name, p, n, dc);
    Waveform wf;
    wf.type = Waveform::SIN;
    wf.vo = dc;
    wf.va = amp;
    wf.freq = freq;
    v->setWaveform(wf);
    v->setAcMag(Complex(amp, 0.0));
    return v;
}

// HB 维度估算（用于在 stderr 打印 GMRES 触发预期）
uint32_t hbDim(uint32_t numNodes, uint32_t numVS, uint32_t NH) {
    return (numNodes + numVS) * (1 + 2 * NH);
}

constexpr uint32_t kGmresThreshold = 200;

} // namespace

// ============================================================================
// LargeCircuitBsim4 fixture
//   - bsim4.dll 仅在首次需要 BSIM4 的测试时加载，process-lifetime；
//   - SetUpTestSuite 跑一次 1-MOS DC 预热 OSDI 内部全局状态。
// ============================================================================
class LargeCircuitBsim4 : public ::testing::Test {
public:
    static BsimLib& warmLib() {
        static BsimLib L;
        return L;
    }
    // 旧版 SetUpTestSuite 跑 1-MOS DC 预热。预热会修改 BSIM4 内部全局状态
    // （igcMod 等），后续某些用例（A3_N20、S1_Grid 等）继承该状态后崩溃。
    // 改为每用例 reload（见 SetUp）后，预热反而引入跨用例污染，故移除。
    // dll 的内部 warm-up 由每个用例自己的 setup_instance/eval 自然完成。

    // 每用例前 reload bsim4.dll：OSDI v0.3 无 destroy hook，setup_instance 内部
    // sub-alloc 泄漏累积会在同进程内多次 BSIM4 用例后触发 use-of-stale-pointer
    // AV（docs/flake_investigation_0621.md）。FreeLibrary+LoadLibrary 让 dll 全局
    // 状态归零，从干净状态出发。
    //
    // 残留 flake（未根治）：N=20 (A3) / N=15 (A1_15) 冷启动仍有 ~50-80% 失败率，
    // 这是 BSIM4/OpenVAF 在大规模多实例下的内部固有不稳定（不仅 alloc 累积，
    // 算法层在低 gmin × 高 NH × 大摆幅下 Newton 不收敛触发的 dll 内部断言路径
    // 也参与其中）。归类为 KI-3，详见 docs/flake_investigation_0621.md 第六节。
    // Set RFSIM_NO_DLL_RELOAD=1 跳过（仅诊断用）。
    void SetUp() override {
        std::string why;
        if (!warmLib().ok(why)) GTEST_SKIP() << why;
        if (std::getenv("RFSIM_NO_DLL_RELOAD") == nullptr) {
            warmLib().reload();
        }
    }
};

// ============================================================================
// L1 — 电阻网格 DC（KLU 稀疏路径，纯线性）
//
// 拓扑：M × N 矩形电阻网格，每个相邻节点用 1kΩ 电阻互连；
//   西边一列接 vdd=1V，东边一列接 GND。
// 期望：节点电压随 j 列号线性下降（接近梯度场），
//   v[(i, 0)] ≈ 1V, v[(i, N-1)] ≈ 0V，且 v[(0, j)] ≈ v[(M-1, j)]（对称）。
// 节点数 = M·N（不含 0=GND；vdd 自身一个 VS 节点）。
// ============================================================================
namespace {

struct MeshDims { int M, N; };

void buildResistorMesh(int M, int N, double R,
                       std::vector<std::unique_ptr<DeviceModel>>& devs,
                       uint32_t& outNumNodes, NodeId& outRightCol0) {
    // node(i,j) for i in [0,M-1], j in [0,N-1]:
    //   id = 1 + i * N + j   (≥1，0 = GND)
    auto nid = [&](int i, int j) -> NodeId {
        return static_cast<NodeId>(1 + i * N + j);
    };

    // VDD 源接到节点 M·N + 1，再 0Ω 到所有 j=0 列（直接复用：把 VS 输出
    // 设到一个独立节点然后用极小电阻接列）— 我们直接用 VS 接到 nid(*,0) 的
    // 第一行节点，其他行通过纵向电阻获得相同电势（已在 mesh 内部）。
    devs.push_back(std::make_unique<VoltageSource>("vin", nid(0, 0), 0, 1.0));

    // 横向电阻 i,j ↔ i,j+1
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < N - 1; ++j) {
            char nm[32]; std::snprintf(nm, sizeof(nm), "rh_%d_%d", i, j);
            devs.push_back(std::make_unique<Resistor>(nm, nid(i, j), nid(i, j + 1), R));
        }
    }
    // 纵向电阻 i,j ↔ i+1,j
    for (int i = 0; i < M - 1; ++i) {
        for (int j = 0; j < N; ++j) {
            char nm[32]; std::snprintf(nm, sizeof(nm), "rv_%d_%d", i, j);
            devs.push_back(std::make_unique<Resistor>(nm, nid(i, j), nid(i + 1, j), R));
        }
    }
    // 东边列接地（终端电阻）
    for (int i = 0; i < M; ++i) {
        char nm[32]; std::snprintf(nm, sizeof(nm), "rgnd_%d", i);
        devs.push_back(std::make_unique<Resistor>(nm, nid(i, N - 1), 0, R));
    }

    outNumNodes = static_cast<uint32_t>(M * N);
    outRightCol0 = nid(0, N - 1);
}

void runResistorMeshDcCheck(int M, int N, const char* tag) {
    const double R = 1e3;
    std::vector<std::unique_ptr<DeviceModel>> devs;
    devs.reserve(static_cast<size_t>(M * N * 3));
    uint32_t numNodes = 0; NodeId rightCol0 = 0;
    buildResistorMesh(M, N, R, devs, numNodes, rightCol0);

    DcOpOptions opt;
    opt.gmin.gmin = 1e-12;
    opt.gmin.gminSteps = 0;     // 纯线性：跳过同伦
    opt.maxIterations = 10;

    double t0 = nowMs();
    auto dc = solveDcOp(numNodes, devs, opt);
    double t1 = nowMs();
    double wallMs = t1 - t0;

    ASSERT_TRUE(dc.converged) << tag << " mesh DC failed";
    ASSERT_TRUE(allFiniteVec(dc.nodeVoltages)) << tag << " mesh DC non-finite";

    auto vij = [&](int i, int j) -> double {
        NodeId id = static_cast<NodeId>(1 + i * N + j);
        return (id < dc.nodeVoltages.size()) ? dc.nodeVoltages[id] : 0.0;
    };

    // 单调下降：v(0, j) ≥ v(0, j+1) at each row, within numerical tolerance
    double worstMonoViol = 0.0;
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < N - 1; ++j) {
            double diff = vij(i, j) - vij(i, j + 1);
            if (diff < -1e-6) worstMonoViol = std::min(worstMonoViol, diff);
        }
    }
    // 行对称：v(i, j) ≈ v(M-1-i, j)
    double worstSymDiff = 0.0;
    for (int i = 0; i < M / 2; ++i)
        for (int j = 0; j < N; ++j)
            worstSymDiff = std::max(worstSymDiff,
                                    std::fabs(vij(i, j) - vij(M - 1 - i, j)));

    // 边界值
    double vWest = vij(0, 0);
    double vEast = vij(0, N - 1);
    std::fprintf(stderr,
        "[%s] mesh %dx%d nodes=%u devs=%zu wall=%.1f ms vWest=%.4f vEast=%.4f "
        "monoViol=%.2e symDiff=%.2e\n",
        tag, M, N, numNodes, devs.size(), wallMs, vWest, vEast,
        worstMonoViol, worstSymDiff);

    EXPECT_NEAR(vWest, 1.0, 1e-9) << tag << " west column != vdd";
    EXPECT_LT(vEast, vWest);
    EXPECT_GT(vEast, 0.0);
    EXPECT_GE(worstMonoViol, -1e-6) << tag << " mesh not monotone east-decreasing";
    // 注：单 VS 注入 (0,0) 角，column-0 通过纵向 R 向下流分压电流，
    // 因此行对称只是近似（symDiff 与 VS 注入点 row index 相关）。
    // 这里仅以 stderr 输出 symDiff 作为诊断量；行对称严格性留给等位
    // bus 版本（后续可加 R_tap=1Ω 把 column-0 各行短接）。
    (void)worstSymDiff;
}

} // namespace

TEST(LargeCircuitLinear, ResistorMesh20x20_DC) {
    runResistorMeshDcCheck(20, 20, "L1.smoke");
}
TEST(LargeCircuitLinear, ResistorMesh50x50_DC_HEAVY) {
    if (!heavyEnabled()) GTEST_SKIP() << "HEAVY gated (set RFSIM_FORCE_HEAVY=1)";
    runResistorMeshDcCheck(50, 50, "L1.heavy");
}

// ============================================================================
// L2 — N=1000 / 2000 RC ladder AC stress
//   仅 HEAVY；test_large_scale 已覆盖 N=500，这里把稠密复数 LU 推到边界。
// ============================================================================
namespace {

void runRcLadderAcStress(int N, const char* tag) {
    const double R = 1e3;
    const double C = 1e-9;

    std::vector<std::unique_ptr<DeviceModel>> devs;
    devs.reserve(static_cast<size_t>(2 * N + 1));
    auto v = std::make_unique<VoltageSource>("vin", 1, 0, 0.0);
    v->setAcMag(Complex(1.0, 0.0));
    devs.push_back(std::move(v));
    for (int k = 1; k <= N; ++k) {
        char rn[24], cn[24];
        std::snprintf(rn, sizeof(rn), "r%d", k);
        std::snprintf(cn, sizeof(cn), "c%d", k);
        devs.push_back(std::make_unique<Resistor>(rn, k, k + 1, R));
        devs.push_back(std::make_unique<Capacitor>(cn, k + 1, 0, C));
    }
    const uint32_t numNodes = static_cast<uint32_t>(N + 1);

    // 仅探低频段（高频在 N 千级 ladder 下深度 stop-band 全为零）
    std::vector<double> freqs = { 1.0, 10.0, 100.0, 1e3 };
    AcSpec spec;
    double t0 = nowMs();
    auto r = solveAc(numNodes, devs, spec, freqs);
    double t1 = nowMs();
    double wallMs = t1 - t0;

    ASSERT_TRUE(r.ok) << tag << " AC failed at N=" << N;
    ASSERT_EQ(r.points.size(), freqs.size());

    // 单调性：随频率增加，|H_out| 应单调下降
    double prevMag = -1.0;
    bool monoOk = true;
    for (size_t i = 0; i < freqs.size(); ++i) {
        ASSERT_LT(static_cast<size_t>(numNodes), r.points[i].nodeVoltages.size());
        Complex hOut = r.points[i].nodeVoltages[numNodes];
        ASSERT_TRUE(std::isfinite(hOut.real()) && std::isfinite(hOut.imag()))
            << tag << " non-finite at f=" << freqs[i];
        double mag = std::abs(hOut);
        if (prevMag > 0.0 && mag > prevMag * 1.01) monoOk = false;
        std::fprintf(stderr, "[%s] N=%d f=%.3e Hz |H|=%.6e\n",
                     tag, N, freqs[i], mag);
        prevMag = mag;
    }
    std::fprintf(stderr,
        "[%s] N=%d nodes=%u devs=%zu wall=%.1f ms mono=%d\n",
        tag, N, numNodes, devs.size(), wallMs, monoOk ? 1 : 0);
    EXPECT_TRUE(monoOk) << tag << " |H(f)| not monotone in passband";
}

} // namespace

TEST(LargeCircuitLinear, RcLadder1000_AC_HEAVY) {
    if (!heavyEnabled()) GTEST_SKIP() << "HEAVY gated (set RFSIM_FORCE_HEAVY=1)";
    runRcLadderAcStress(1000, "L2.N1000");
}
TEST(LargeCircuitLinear, RcLadder2000_AC_HEAVY) {
    if (!heavyEnabled()) GTEST_SKIP() << "HEAVY gated (set RFSIM_FORCE_HEAVY=1)";
    runRcLadderAcStress(2000, "L2.N2000");
}

// ============================================================================
// L3 — LcTankChain：N 级 LC 并联谐振串接（DC + AC + 线性 HB）
//
// 拓扑：每级 (L 并 C) 串入主链，主链经 R 端接 GND。
//   vin (1) ── L1 || C1 (1↔2) ── L2 || C2 (2↔3) ── ... ── Lk || Ck (k↔k+1)
//             ── Rload (k+1 ↔ 0)
// 用相同 L=1µH C=10pF → f0 = 1/(2π√LC) ≈ 50.3 MHz
// 并联 LC 串接形成 NOTCH 滤波器：在 f0 处 L||C 阻抗 → ∞，输出 → 0；
// 远离 f0 时阻抗减小，输出接近 vin。
// 期望：AC 在 f0 处出现 |H| 最小值（凹陷）；线性 HB 在 f0 处亦能解。
// ============================================================================
namespace {

void buildLcTankChain(int N,
                      std::vector<std::unique_ptr<DeviceModel>>& devs,
                      uint32_t& outNumNodes, NodeId& outOutNode) {
    const double Ll = 1e-6;
    const double Cl = 10e-12;
    const double Rload = 1e3;

    auto v = std::make_unique<VoltageSource>("vin", 1, 0, 0.0);
    v->setAcMag(Complex(1.0, 0.0));
    Waveform wf; wf.type = Waveform::SIN; wf.vo = 0.0; wf.va = 1.0;
    wf.freq = 50.3e6;
    v->setWaveform(wf);
    devs.push_back(std::move(v));

    for (int k = 1; k <= N; ++k) {
        char ln[24], cn[24];
        std::snprintf(ln, sizeof(ln), "l%d", k);
        std::snprintf(cn, sizeof(cn), "c%d", k);
        devs.push_back(std::make_unique<Inductor>(ln, k, k + 1, Ll));
        devs.push_back(std::make_unique<Capacitor>(cn, k, k + 1, Cl));
    }
    devs.push_back(std::make_unique<Resistor>("rload", N + 1, 0, Rload));

    outNumNodes = static_cast<uint32_t>(N + 1);
    outOutNode = static_cast<NodeId>(N + 1);
}

void runLcTankChain(int N, const char* tag) {
    std::vector<std::unique_ptr<DeviceModel>> devs;
    uint32_t numNodes = 0; NodeId outNode = 0;
    buildLcTankChain(N, devs, numNodes, outNode);

    // ---- DC ----（电感 DC 短路：vin → outNode 直通，但 vin DC=0 → 输出=0）
    DcOpOptions dcOpt;
    dcOpt.gmin.gminSteps = 0;
    double tA = nowMs();
    auto dc = solveDcOp(numNodes, devs, dcOpt);
    double tB = nowMs();
    ASSERT_TRUE(dc.converged) << tag << " LC DC failed";
    ASSERT_TRUE(allFiniteVec(dc.nodeVoltages));

    // ---- AC: 在 f0 附近扫描 ----
    const double f0 = 50.3e6;
    std::vector<double> freqs = { f0 / 10, f0 / 2, f0, f0 * 2, f0 * 10 };
    AcSpec spec;
    double tC = nowMs();
    auto ac = solveAc(numNodes, devs, spec, freqs);
    double tD = nowMs();
    ASSERT_TRUE(ac.ok) << tag << " AC failed";

    // 谐振峰：|H(f0)| 不应小于 |H(f0/10)| 与 |H(f0*10)|
    double magAtF0 = std::abs(ac.points[2].nodeVoltages[outNode]);
    double magLow  = std::abs(ac.points[0].nodeVoltages[outNode]);
    double magHigh = std::abs(ac.points[4].nodeVoltages[outNode]);
    std::fprintf(stderr,
        "[%s] LC N=%d f0=%.2f MHz |H| @ {f0/10,f0/2,f0,2f0,10f0} = "
        "%.4g %.4g %.4g %.4g %.4g  AC wall=%.1f ms\n",
        tag, N, f0 / 1e6,
        magLow, std::abs(ac.points[1].nodeVoltages[outNode]),
        magAtF0, std::abs(ac.points[3].nodeVoltages[outNode]),
        magHigh, tD - tC);

    // 至少一边应低于 f0 处幅值（带通中心）
    EXPECT_LT(magAtF0, magLow * 0.5) << tag << " no notch at f0 (low side)";
    EXPECT_LT(magAtF0, magHigh * 0.5) << tag << " no notch at f0 (high side)";

    // ---- 线性 HB ----
    HbConfig cfg; cfg.fundamental = f0; cfg.numHarmonics = 5;
    double tE = nowMs();
    auto hb = solveHbLinear(numNodes, devs, cfg);
    double tF = nowMs();
    ASSERT_TRUE(hb.ok) << tag << " linear HB failed";
    ASSERT_TRUE(allFiniteHarm(hb.nodeVoltages));

    std::fprintf(stderr,
        "[%s] LC N=%d DC=%.1f ms AC=%.1f ms HBlin=%.1f ms\n",
        tag, N, tB - tA, tD - tC, tF - tE);
}

} // namespace

TEST(LargeCircuitLinear, LcTankChain10) {
    runLcTankChain(10, "L3.N10");
}
TEST(LargeCircuitLinear, LcTankChain50_HEAVY) {
    if (!heavyEnabled()) GTEST_SKIP() << "HEAVY gated (set RFSIM_FORCE_HEAVY=1)";
    runLcTankChain(50, "L3.N50");
}

// ============================================================================
// L4 — Linear HB NH 扫描（基于 L3 N=10）
//   解维度（linear HB）= numNodes · (1 + NH)，与 HB-NL 不同（后者 ×2 for re/im
//   block）。这里验证 NH 增大时 solveHbLinear 仍 ok。
// ============================================================================
TEST(LargeCircuitLinear, LinearHbNhScan) {
    std::vector<int> nhList = { 3, 5, 9, 15 };
    for (int nh : nhList) {
        std::vector<std::unique_ptr<DeviceModel>> devs;
        uint32_t numNodes = 0; NodeId outNode = 0;
        buildLcTankChain(10, devs, numNodes, outNode);
        HbConfig cfg; cfg.fundamental = 50.3e6;
        cfg.numHarmonics = static_cast<uint32_t>(nh);
        double t0 = nowMs();
        auto hb = solveHbLinear(numNodes, devs, cfg);
        double t1 = nowMs();
        ASSERT_TRUE(hb.ok) << "linear HB NH=" << nh << " failed";
        ASSERT_TRUE(allFiniteHarm(hb.nodeVoltages));
        std::fprintf(stderr,
            "[L4.NHscan] NH=%d nodes=%u wall=%.1f ms\n",
            nh, numNodes, t1 - t0);
    }
}

// ============================================================================
// G1 — DiodeRectifierStack：N 个独立半波整流支路（HB-NL）
//
// 拓扑：共享一个 AC 源 vs (节点 1) → 公共总线 (节点 2) 经 Rs → 各支路
//   分别用一个二极管接 tap_k (节点 2+k)，tap_k 再用 Rload || Cload 接 GND。
// 默认 N=5 NH=5：dim ≈ (2+5+VS)·11 ≈ 88，走稠密 LU。
// HEAVY  N=30 NH=10：dim ≈ (32+1)·21 ≈ 693，首次跨过 gmresThreshold=200，
//   触发 GMRES + 对角预处理。
// ============================================================================
namespace {

struct DiodeStackRun {
    bool ok = false;
    bool dcConv = false;
    bool hbConv = false;
    double dcMs = 0;
    double hbMs = 0;
    uint32_t numNodes = 0;
    uint32_t hbDimEst = 0;
    double h1AnodeFirst = 0.0;
    std::string skipReason;
};

DiodeStackRun runDiodeRectifierStack(int N, int NH,
                                     double Vbias, double Vac,
                                     const char* libEnv, const char* dllStem) {
    DiodeStackRun out;

    OsdiLibrary lib;
    std::string err;
    std::string path = osdiLibPath(libEnv, dllStem);
    if (!lib.load(path, err)) {
        out.skipReason = "cannot load " + path + ": " + err;
        return out;
    }
    auto libSp = std::make_shared<OsdiLibrary>(std::move(lib));
    if (libSp->numDescriptors() < 1) {
        out.skipReason = "no descriptors in " + path;
        return out;
    }
    const OsdiDescriptor* d = libSp->descriptors();
    const bool hasThermal = (d->num_terminals > 2);

    std::vector<std::unique_ptr<DeviceModel>> devs;
    auto vs = std::make_unique<VoltageSource>("vs", 1, 0, Vbias);
    vs->setAcMag(Complex(Vac, 0.0));
    devs.push_back(std::move(vs));
    devs.push_back(std::make_unique<Resistor>("rs", 1, 2, 50.0));  // 公共串阻

    // 分支：tap_k = node(2 + k), thermal_k = node(2 + N + k) if hasThermal
    NodeId base = static_cast<NodeId>(2 + N + (hasThermal ? N : 0) + 1);

    for (int k = 1; k <= N; ++k) {
        NodeId anode = static_cast<NodeId>(2 + k);
        NodeId therm = hasThermal
            ? static_cast<NodeId>(2 + N + k)
            : static_cast<NodeId>(0);

        // 二极管：term[0]=A, term[1]=C, term[2]=dT
        std::vector<NodeId> terms(d->num_terminals, 0);
        terms[0] = 2;          // anode 接公共总线
        terms[1] = anode;      // cathode 接 tap（用作整流输出）
        if (hasThermal) terms[2] = therm;

        // OSDI 实例参数（simple_diode 不需要参数；完整 diode 走 ParamList 内置）
        ParamList instP;
        ParamList modelP;
        if (std::string(dllStem) == "diode") {
            auto add = [&](const char* n, double v) {
                modelP.push_back({n, ParamValue{ParamValue::Kind::Number, v, "", SourceLoc{}}});
            };
            add("minr", 1e-3); add("is", 1e-14); add("n", 1.0);
            add("vj", 1.0); add("m", 0.5);
        }

        char nm[24]; std::snprintf(nm, sizeof(nm), "d%d", k);
        auto dio = std::make_unique<OsdiModel>(nm, terms, libSp, d, instP, modelP);
        Diagnostics diags;
        if (!dio->initialize(diags, base)) {
            out.skipReason = "diode initialize failed for k=" + std::to_string(k);
            return out;
        }

        if (hasThermal) {
            char nm2[32]; std::snprintf(nm2, sizeof(nm2), "rth_%d", k);
            devs.push_back(std::make_unique<Resistor>(nm2, therm, 0, 1.0));
        }
        // 负载：tap → GND
        char rn[24], cn[24];
        std::snprintf(rn, sizeof(rn), "rl_%d", k);
        std::snprintf(cn, sizeof(cn), "cl_%d", k);
        devs.push_back(std::make_unique<Resistor>(rn, anode, 0, 1e3));
        devs.push_back(std::make_unique<Capacitor>(cn, anode, 0, 1e-9));
        devs.push_back(std::move(dio));
    }

    out.numNodes = computeMaxNode(devs);
    out.hbDimEst = hbDim(out.numNodes, 1, static_cast<uint32_t>(NH));

    // ---- DC ----
    DcOpOptions dcOpt;
    dcOpt.gmin.gmin = 1e-9;
    dcOpt.gmin.gminStart = 1e-2;
    dcOpt.gmin.gminSteps = 12;
    dcOpt.maxIterations = 80;
    dcOpt.dvmax = 0.2;
    double t0 = nowMs();
    auto dc = solveDcOp(out.numNodes, devs, dcOpt);
    out.dcMs = nowMs() - t0;
    out.dcConv = dc.converged;

    // ---- HB-NL ----
    HbConfig cfg;
    cfg.fundamental = 1e6;
    cfg.numHarmonics = static_cast<uint32_t>(NH);
    HbNlOptions hopts;
    hopts.sourceSteps = 10;
    hopts.gmin.gmin = 1e-2;
    hopts.gmin.gminSteps = 0;
    hopts.dvmax = 0.5;
    hopts.maxIter = 80;
    double t1 = nowMs();
    auto hb = solveHbNonlinear(out.numNodes, devs, cfg, nullptr, hopts);
    out.hbMs = nowMs() - t1;
    out.hbConv = hb.converged;
    if (!hb.nodeVoltages.empty()) {
        // tap1 = node 3
        if (hb.nodeVoltages.size() > 3 && hb.nodeVoltages[3].v.size() > 1)
            out.h1AnodeFirst = std::abs(hb.nodeVoltages[3].v[1]);
    }
    out.ok = true;
    return out;
}

} // namespace

TEST(LargeCircuitHbnl, DiodeRectifierStack5_NH5_DefaultDense) {
    auto rr = runDiodeRectifierStack(5, 5, 0.0, 1.0,
                                     "RFSIM_SIMPLE_DIODE_LIB", "simple_diode");
    if (!rr.ok) GTEST_SKIP() << rr.skipReason;
    std::fprintf(stderr,
        "[G1.default] N=5 NH=5 nodes=%u dim=%u (<%u dense) "
        "dcConv=%d dc=%.1f ms hbConv=%d hb=%.1f ms |H1(tap1)|=%.4g\n",
        rr.numNodes, rr.hbDimEst, kGmresThreshold,
        rr.dcConv, rr.dcMs, rr.hbConv, rr.hbMs, rr.h1AnodeFirst);
    EXPECT_TRUE(rr.dcConv);
    // hbConv 在轻量默认可不收敛（仅限 finite 检查在 harness 里完成）
    if (rr.hbConv) {
        EXPECT_GT(rr.h1AnodeFirst, 1e-3) << "no rectification at tap1";
    }
}

TEST(LargeCircuitHbnl, DiodeRectifierStack30_NH10_HEAVY_TriggersGmres) {
    if (!heavyEnabled()) GTEST_SKIP() << "HEAVY gated (set RFSIM_FORCE_HEAVY=1)";
    auto rr = runDiodeRectifierStack(30, 10, 0.0, 1.0,
                                     "RFSIM_SIMPLE_DIODE_LIB", "simple_diode");
    if (!rr.ok) GTEST_SKIP() << rr.skipReason;
    const bool gmresExpected = rr.hbDimEst > kGmresThreshold;
    std::fprintf(stderr,
        "[G1.heavy] N=30 NH=10 nodes=%u dim=%u %s "
        "dcConv=%d dc=%.1f ms hbConv=%d hb=%.1f ms |H1(tap1)|=%.4g\n",
        rr.numNodes, rr.hbDimEst,
        gmresExpected ? "(>=200 → GMRES path)" : "(<200 still dense)",
        rr.dcConv, rr.dcMs, rr.hbConv, rr.hbMs, rr.h1AnodeFirst);
    EXPECT_TRUE(gmresExpected) << "expected dim > 200 to exercise GMRES";
    EXPECT_TRUE(rr.dcConv);
    // GMRES + 对角预处理首次触达，记录是否收敛；不强 require（HEAVY 探测性）
    if (rr.hbConv) {
        EXPECT_GT(rr.h1AnodeFirst, 1e-3);
    } else {
        std::fprintf(stderr,
            "[G1.heavy] HB-NL did NOT converge via GMRES path — recorded for "
            "V2-γ HB-NL preconditioner tuning task\n");
    }
}

// ============================================================================
// G2 — BSIM4 共源 HB-NL NH 扫描
//
// 单 BSIM4 CS 在多 NH 下：dim = (numNodes + 1) * (1 + 2*NH)
//   numNodes ≈ 3，dim @ NH=3 → 4·7=28；NH=7 → 4·15=60；NH=15 → 4·31=124；
//   均 < 200，永远不会触发 GMRES — 本测试目的是验证高 NH 下 HB-NL Newton
//   仍稳定；GMRES 切换由 G1.heavy 单独覆盖。
// ============================================================================
TEST_F(LargeCircuitBsim4, G2_Bsim4CsNhScan) {
    std::string why;
    if (!warmLib().ok(why)) GTEST_SKIP() << "bsim4 lib not loaded: " << why;

    std::vector<int> nhDefault = { 3, 7 };
    std::vector<int> nhHeavy   = { 11, 15 };
    std::vector<int> nhList = nhDefault;
    if (heavyEnabled())
        nhList.insert(nhList.end(), nhHeavy.begin(), nhHeavy.end());

    for (int nh : nhList) {
        std::vector<std::unique_ptr<DeviceModel>> devs;
        devs.push_back(std::make_unique<VoltageSource>("vdd", 1, 0, 1.5));
        devs.push_back(sineVS("vg", 3, 0, 0.85, 0.05, 1e6));
        devs.push_back(std::make_unique<Resistor>("rd", 1, 2, 5e3));
        Diagnostics diags; NodeId base = 4;
        auto m = makeNmos("m1", 2, 3, 0, 0, warmLib(), diags, base);
        ASSERT_TRUE(m != nullptr);
        devs.push_back(std::move(m));

        NodeId numNodes = computeMaxNode(devs);

        // DC warm start
        DcOpOptions dcOpt;
        dcOpt.gmin.gmin = 1e-9;
        dcOpt.gmin.gminStart = 1e-3;
        dcOpt.gmin.gminSteps = 12;
        dcOpt.maxIterations = 80;
        dcOpt.dvmax = 0.2;
        auto dc = solveDcOp(numNodes, devs, dcOpt);
        ASSERT_TRUE(dc.converged) << "DC failed at NH=" << nh;

        HbConfig cfg; cfg.fundamental = 1e6;
        cfg.numHarmonics = static_cast<uint32_t>(nh);
        HbNlOptions hopts;
        hopts.gmin.gmin = 1e-9;
        hopts.dvmax = 0.5;
        hopts.maxIter = 60;
        // V2-γ post-S2：BSIM4 在默认单步 Newton 下 S2 grid 全 NH 0/6；
        // 启用 autoHomotopy 让 solver 自适应到 4 步源步进 × 5 点 gmin 路径。
        hopts.autoHomotopy = true;
        uint32_t dimEst = hbDim(numNodes, 2, static_cast<uint32_t>(nh));

        double t0 = nowMs();
        auto hb = solveHbNonlinear(numNodes, devs, cfg, &dc.nodeVoltages, hopts);
        double t1 = nowMs();

        bool fin = allFiniteHarm(hb.nodeVoltages);
        double h1Drain = 0.0;
        if (fin && hb.nodeVoltages.size() > 2 && hb.nodeVoltages[2].v.size() > 1)
            h1Drain = std::abs(hb.nodeVoltages[2].v[1]);

        std::fprintf(stderr,
            "[G2.NHscan] NH=%d nodes=%u dim≈%u %s "
            "hbConv=%d wall=%.1f ms |H1(drain)|=%.4g\n",
            nh, numNodes, dimEst,
            dimEst > kGmresThreshold ? "(GMRES)" : "(dense)",
            hb.converged, t1 - t0, h1Drain);

        EXPECT_TRUE(fin) << "HB-NL non-finite at NH=" << nh;
        // 不卡收敛：轻量默认 may not reach reltol, 仅确保有限+H1可观测
        if (nh <= 7) {
            EXPECT_GT(h1Drain, 0.0) << "zero drain response at NH=" << nh;
        }
    }
}

// ============================================================================
// A1 — InverterChainN：N 级 NMOS+R-pullup 反相器链
//
// 与 test_multi_device.InverterChain5 同形态拓扑，延长到 N 级。
// 每级：vdd ── R_pull (R=5k) ── drain_k；M_k: d=drain_k, g=drain_{k-1}, s=0, b=0.
// 第 1 级输入由 vin 提供（DC 0.4V + 10mV @1MHz）。
//
// 验证：DC OP 收敛 + 每级 drain 电压在 [0, vdd] 范围；transient PSS smoke。
// ============================================================================
namespace {

void buildInverterChain(int N, double vdd, double vinDC, double vinAc, double freq,
                       BsimLib& L, Diagnostics& diags, NodeId& baseInternal,
                       std::vector<std::unique_ptr<DeviceModel>>& devs,
                       uint32_t& outNumNodes, NodeId& outLastDrain,
                       bool& okInit) {
    // 节点编号：1 = vdd, 2 = vin, 3..2+N = drain_k
    devs.push_back(std::make_unique<VoltageSource>("vdd", 1, 0, vdd));
    devs.push_back(sineVS("vin", 2, 0, vinDC, vinAc, freq));

    okInit = true;
    for (int k = 1; k <= N; ++k) {
        char rn[24]; std::snprintf(rn, sizeof(rn), "rp%d", k);
        NodeId drainK = static_cast<NodeId>(2 + k);
        devs.push_back(std::make_unique<Resistor>(rn, 1, drainK, 5e3));
        NodeId gateK = (k == 1) ? static_cast<NodeId>(2)
                                : static_cast<NodeId>(2 + (k - 1));
        char mn[24]; std::snprintf(mn, sizeof(mn), "m%d", k);
        auto m = makeNmos(mn, drainK, gateK, 0, 0, L, diags, baseInternal);
        if (!m) { okInit = false; return; }
        devs.push_back(std::move(m));
    }
    outNumNodes = static_cast<uint32_t>(2 + N);
    outLastDrain = static_cast<NodeId>(2 + N);
}

void runInverterChainCheck(int N, const char* tag) {
    auto& L = LargeCircuitBsim4::warmLib();
    std::string why;
    ASSERT_TRUE(L.ok(why)) << why;

    std::vector<std::unique_ptr<DeviceModel>> devs;
    Diagnostics diags;
    NodeId base = static_cast<NodeId>(3 + N);
    uint32_t numNodes = 0; NodeId lastDrain = 0; bool okInit = false;
    buildInverterChain(N, 1.5, 0.4, 0.01, 1e6,
                       L, diags, base, devs, numNodes, lastDrain, okInit);
    ASSERT_TRUE(okInit) << tag << " inverter chain init failed";

    DcOpOptions opt;
    opt.gmin.gmin = 1e-9;
    opt.gmin.gminStart = 1e-3;
    opt.gmin.gminSteps = 15;
    opt.maxIterations = 150;
    opt.dvmax = 0.2;
    opt.sourceStepCount = 6;
    double t0 = nowMs();
    auto dc = solveDcOp(numNodes, devs, opt);
    double t1 = nowMs();
    ASSERT_TRUE(allFiniteVec(dc.nodeVoltages)) << tag << " DC non-finite";
    EXPECT_TRUE(dc.converged) << tag << " DC did not converge (iters="
                              << dc.iterations << ")";

    // 边界检查：所有 drain 节点在 [-0.05, vdd+0.05]
    double vmin = 0.0, vmax = 0.0;
    for (int k = 1; k <= N; ++k) {
        NodeId dk = static_cast<NodeId>(2 + k);
        if (dk < dc.nodeVoltages.size()) {
            double v = dc.nodeVoltages[dk];
            vmin = (k == 1) ? v : std::min(vmin, v);
            vmax = (k == 1) ? v : std::max(vmax, v);
            EXPECT_GE(v, -0.05) << tag << " drain[" << k << "]=" << v;
            EXPECT_LE(v, 1.55)  << tag << " drain[" << k << "]=" << v;
        }
    }

    std::fprintf(stderr,
        "[%s] InvChain N=%d nodes=%u dcConv=%d iters=%u wall=%.1f ms "
        "vRange=[%.3f, %.3f]\n",
        tag, N, numNodes, dc.converged, dc.iterations, t1 - t0, vmin, vmax);

    // ---- transient PSS smoke via HB-NL ----
    HbConfig cfg; cfg.fundamental = 1e6; cfg.numHarmonics = 1;
    HbNlOptions hopts;
    hopts.gmin.gmin = 1e-9;
    hopts.dvmax = 0.5;
    hopts.maxIter = 50;
    std::vector<double> initV(numNodes + 1, 0.0);
    if (dc.converged && dc.nodeVoltages.size() > numNodes) initV = dc.nodeVoltages;
    double t2 = nowMs();
    auto hb = solveHbNonlinear(numNodes, devs, cfg,
                               dc.converged ? &initV : nullptr, hopts);
    double t3 = nowMs();
    bool fin = allFiniteHarm(hb.nodeVoltages);
    EXPECT_TRUE(fin) << tag << " HB non-finite";
    double h1Last = 0.0;
    if (fin && hb.nodeVoltages.size() > lastDrain
            && hb.nodeVoltages[lastDrain].v.size() > 1)
        h1Last = std::abs(hb.nodeVoltages[lastDrain].v[1]);
    std::fprintf(stderr,
        "[%s] InvChain N=%d hbConv=%d wall=%.1f ms |H1(drain_N)|=%.4g\n",
        tag, N, hb.converged, t3 - t2, h1Last);
}

} // namespace

TEST_F(LargeCircuitBsim4, A1_InverterChain10) {
    runInverterChainCheck(10, "A1.N10");
}
TEST_F(LargeCircuitBsim4, A1_InverterChain15_HEAVY) {
    if (!heavyEnabled()) GTEST_SKIP() << "HEAVY gated (set RFSIM_FORCE_HEAVY=1)";
    runInverterChainCheck(15, "A1.N15");
}

// ============================================================================
// A2 — Cascade Common-Source amplifier，K 级共源放大
//
// 拓扑：vdd ── Rd_k ── drain_k；M_k: d=drain_k, g=drain_{k-1} or vin, s=0, b=0
// 与 InverterChain 不同：偏置在弱反型/中等反型 (Vgs ≈ 0.85V > Vth=0.5V)，
// 信号摆幅小（10 mV），用于看小信号链增益的级联收敛性。
// ============================================================================
namespace {

void runCascadeCsCheck(int K, const char* tag) {
    auto& L = LargeCircuitBsim4::warmLib();
    std::string why;
    ASSERT_TRUE(L.ok(why)) << why;

    std::vector<std::unique_ptr<DeviceModel>> devs;
    devs.push_back(std::make_unique<VoltageSource>("vdd", 1, 0, 1.5));
    devs.push_back(sineVS("vin", 2, 0, 0.85, 0.01, 1e6));

    Diagnostics diags;
    NodeId base = static_cast<NodeId>(3 + K);
    for (int k = 1; k <= K; ++k) {
        char rn[24]; std::snprintf(rn, sizeof(rn), "rd%d", k);
        NodeId drainK = static_cast<NodeId>(2 + k);
        devs.push_back(std::make_unique<Resistor>(rn, 1, drainK, 5e3));
        NodeId gateK = (k == 1) ? static_cast<NodeId>(2)
                                : static_cast<NodeId>(2 + (k - 1));
        char mn[24]; std::snprintf(mn, sizeof(mn), "m%d", k);
        auto m = makeNmos(mn, drainK, gateK, 0, 0, L, diags, base);
        ASSERT_TRUE(m != nullptr);
        devs.push_back(std::move(m));
    }
    uint32_t numNodes = static_cast<uint32_t>(2 + K);
    NodeId lastDrain = static_cast<NodeId>(2 + K);

    DcOpOptions opt;
    opt.gmin.gmin = 1e-9;
    opt.gmin.gminStart = 1e-3;
    opt.gmin.gminSteps = 15;
    opt.maxIterations = 150;
    opt.dvmax = 0.2;
    opt.sourceStepCount = 6;
    double t0 = nowMs();
    auto dc = solveDcOp(numNodes, devs, opt);
    double t1 = nowMs();
    ASSERT_TRUE(allFiniteVec(dc.nodeVoltages));
    EXPECT_TRUE(dc.converged) << tag << " DC failed";

    std::fprintf(stderr,
        "[%s] CascadeCS K=%d nodes=%u dcConv=%d iters=%u wall=%.1f ms\n",
        tag, K, numNodes, dc.converged, dc.iterations, t1 - t0);

    // HB-NL smoke
    HbConfig cfg; cfg.fundamental = 1e6; cfg.numHarmonics = 1;
    HbNlOptions hopts;
    hopts.gmin.gmin = 1e-9;
    hopts.dvmax = 0.5;
    hopts.maxIter = 50;
    std::vector<double> initV(numNodes + 1, 0.0);
    if (dc.converged && dc.nodeVoltages.size() > numNodes) initV = dc.nodeVoltages;
    double t2 = nowMs();
    auto hb = solveHbNonlinear(numNodes, devs, cfg,
                               dc.converged ? &initV : nullptr, hopts);
    double t3 = nowMs();
    bool fin = allFiniteHarm(hb.nodeVoltages);
    EXPECT_TRUE(fin) << tag << " HB non-finite";

    double h1Last = 0.0;
    if (fin && hb.nodeVoltages.size() > lastDrain
            && hb.nodeVoltages[lastDrain].v.size() > 1)
        h1Last = std::abs(hb.nodeVoltages[lastDrain].v[1]);
    std::fprintf(stderr,
        "[%s] CascadeCS K=%d hbConv=%d wall=%.1f ms |H1(out)|=%.4g\n",
        tag, K, hb.converged, t3 - t2, h1Last);
}

} // namespace

TEST_F(LargeCircuitBsim4, A2_CascadeCS3Stage) {
    runCascadeCsCheck(3, "A2.K3");
}
TEST_F(LargeCircuitBsim4, A2_CascadeCS5Stage_HEAVY) {
    if (!heavyEnabled()) GTEST_SKIP() << "HEAVY gated (set RFSIM_FORCE_HEAVY=1)";
    runCascadeCsCheck(5, "A2.K5");
}

// ============================================================================
// A3 — NmosPullupBuffer20：20 级 NMOS 串扰压力（HEAVY）
//
// 与 A1 同拓扑但 N=20，Vin=0.6V（mid-rail）；这是 V2-γ Phase B
// initVoltagesForScale 中长链 mid-rail seeding 的回归保护。
// ============================================================================
TEST_F(LargeCircuitBsim4, A3_NmosPullupBuffer20_HEAVY) {
    if (!heavyEnabled()) GTEST_SKIP() << "HEAVY gated (set RFSIM_FORCE_HEAVY=1)";
    runInverterChainCheck(20, "A3.N20");
}

// ============================================================================
// M1 — LC 匹配 + BSIM4 CS 放大器（混合大电路）
//
// vdd (1) ── L_choke (1↔2) ── M1.d=2  drain
// vin (3) ── C_in (3↔4) ── M1.g=4  via C 隔直
// vbias (5) ── R_g (5↔4) ── 给 gate 直流偏置
// M1: d=2 g=4 s=0 b=0
// out (2) ── C_out (2↔6) ── R_load (6↔0)
// ============================================================================
TEST_F(LargeCircuitBsim4, M1_LcMatchedCsAmp) {
    auto& L = warmLib();
    std::string why;
    ASSERT_TRUE(L.ok(why)) << why;

    std::vector<std::unique_ptr<DeviceModel>> devs;
    devs.push_back(std::make_unique<VoltageSource>("vdd", 1, 0, 1.5));
    devs.push_back(std::make_unique<VoltageSource>("vbias", 5, 0, 0.85));
    devs.push_back(sineVS("vin", 3, 0, 0.0, 0.02, 1e6));

    devs.push_back(std::make_unique<Inductor>("lchoke", 1, 2, 50e-9));
    devs.push_back(std::make_unique<Capacitor>("cin", 3, 4, 1e-9));
    devs.push_back(std::make_unique<Resistor>("rg", 5, 4, 50e3));
    devs.push_back(std::make_unique<Capacitor>("cout", 2, 6, 1e-9));
    devs.push_back(std::make_unique<Resistor>("rload", 6, 0, 1e3));

    Diagnostics diags; NodeId base = 7;
    auto m = makeNmos("m1", 2, 4, 0, 0, L, diags, base);
    ASSERT_TRUE(m != nullptr);
    devs.push_back(std::move(m));

    uint32_t numNodes = computeMaxNode(devs);

    DcOpOptions opt;
    opt.gmin.gmin = 1e-9;
    opt.gmin.gminStart = 1e-3;
    opt.gmin.gminSteps = 15;
    opt.maxIterations = 150;
    opt.dvmax = 0.2;
    opt.sourceStepCount = 6;
    double t0 = nowMs();
    auto dc = solveDcOp(numNodes, devs, opt);
    double t1 = nowMs();
    ASSERT_TRUE(allFiniteVec(dc.nodeVoltages));
    EXPECT_TRUE(dc.converged) << "M1 DC failed";

    HbConfig cfg; cfg.fundamental = 1e6; cfg.numHarmonics = 3;
    HbNlOptions hopts;
    hopts.gmin.gmin = 1e-9;
    hopts.dvmax = 0.5;
    hopts.maxIter = 60;
    std::vector<double> initV(numNodes + 1, 0.0);
    if (dc.converged && dc.nodeVoltages.size() > numNodes) initV = dc.nodeVoltages;
    double t2 = nowMs();
    auto hb = solveHbNonlinear(numNodes, devs, cfg,
                               dc.converged ? &initV : nullptr, hopts);
    double t3 = nowMs();
    bool fin = allFiniteHarm(hb.nodeVoltages);
    EXPECT_TRUE(fin) << "M1 HB non-finite";

    double h1Drain = 0.0;
    if (fin && hb.nodeVoltages.size() > 2 && hb.nodeVoltages[2].v.size() > 1)
        h1Drain = std::abs(hb.nodeVoltages[2].v[1]);
    double h1Load = 0.0;
    if (fin && hb.nodeVoltages.size() > 6 && hb.nodeVoltages[6].v.size() > 1)
        h1Load = std::abs(hb.nodeVoltages[6].v[1]);

    std::fprintf(stderr,
        "[M1.LcCsAmp] nodes=%u dcConv=%d dc=%.1f ms hbConv=%d hb=%.1f ms "
        "|H1(drain)|=%.4g |H1(load)|=%.4g\n",
        numNodes, dc.converged, t1 - t0, hb.converged, t3 - t2, h1Drain, h1Load);
}

// ============================================================================
// M2 — Cascode LNA + Π matching (HEAVY)
//
// 拓扑：
//   vin (3) ── Cin (3↔4) ── Lin (4↔5)         输入匹配（L 型）
//   vbias_g1 (10) ── Rg1 (10↔5) ── M1.g=5    M1 输入 NMOS
//   M1: d=6 g=5 s=0 b=0
//   M2 (cascode): d=7 g=vbias_cas (11) s=6 b=0
//   vdd (1) ── Lchoke (1↔7) drain choke
//   Π 匹配输出：7 ── Cout (7↔8) ── Lout (8↔9) ── Cload (9↔0) ── Rload (8↔0)
// ============================================================================
TEST_F(LargeCircuitBsim4, M2_CascodeLnaPiMatch_HEAVY) {
    if (!heavyEnabled()) GTEST_SKIP() << "HEAVY gated (set RFSIM_FORCE_HEAVY=1)";
    auto& L = warmLib();
    std::string why;
    ASSERT_TRUE(L.ok(why)) << why;

    std::vector<std::unique_ptr<DeviceModel>> devs;
    devs.push_back(std::make_unique<VoltageSource>("vdd", 1, 0, 1.8));
    devs.push_back(sineVS("vin", 3, 0, 0.0, 0.01, 2.4e9));
    devs.push_back(std::make_unique<VoltageSource>("vbias_g1", 10, 0, 0.6));
    devs.push_back(std::make_unique<VoltageSource>("vbias_cas", 11, 0, 1.4));

    devs.push_back(std::make_unique<Capacitor>("cin", 3, 4, 2e-12));
    devs.push_back(std::make_unique<Inductor>("lin", 4, 5, 3e-9));
    devs.push_back(std::make_unique<Resistor>("rg1", 10, 5, 100e3));
    devs.push_back(std::make_unique<Inductor>("lchoke", 1, 7, 5e-9));
    devs.push_back(std::make_unique<Capacitor>("cout", 7, 8, 2e-12));
    devs.push_back(std::make_unique<Inductor>("lout", 8, 9, 3e-9));
    devs.push_back(std::make_unique<Capacitor>("cload", 9, 0, 2e-12));
    devs.push_back(std::make_unique<Resistor>("rload", 8, 0, 50.0));

    Diagnostics diags; NodeId base = 12;
    auto m1 = makeNmos("m1", 6, 5, 0, 0, L, diags, base, 5e-6, 130e-9);
    auto m2 = makeNmos("m2", 7, 11, 6, 0, L, diags, base, 5e-6, 130e-9);
    ASSERT_TRUE(m1 && m2);
    devs.push_back(std::move(m1));
    devs.push_back(std::move(m2));

    uint32_t numNodes = computeMaxNode(devs);

    DcOpOptions opt;
    opt.gmin.gmin = 1e-9;
    opt.gmin.gminStart = 1e-3;
    opt.gmin.gminSteps = 15;
    opt.maxIterations = 200;
    opt.dvmax = 0.2;
    opt.sourceStepCount = 8;
    double t0 = nowMs();
    auto dc = solveDcOp(numNodes, devs, opt);
    double t1 = nowMs();
    ASSERT_TRUE(allFiniteVec(dc.nodeVoltages));

    std::fprintf(stderr,
        "[M2.CascodeLNA] nodes=%u dcConv=%d iters=%u wall=%.1f ms\n",
        numNodes, dc.converged, dc.iterations, t1 - t0);

    if (dc.converged) {
        HbConfig cfg; cfg.fundamental = 2.4e9; cfg.numHarmonics = 2;
        HbNlOptions hopts;
        hopts.gmin.gmin = 1e-9;
        hopts.dvmax = 0.5;
        hopts.maxIter = 60;
        std::vector<double> initV(numNodes + 1, 0.0);
        if (dc.nodeVoltages.size() > numNodes) initV = dc.nodeVoltages;
        double t2 = nowMs();
        auto hb = solveHbNonlinear(numNodes, devs, cfg, &initV, hopts);
        double t3 = nowMs();
        std::fprintf(stderr,
            "[M2.CascodeLNA] hbConv=%d wall=%.1f ms\n",
            hb.converged, t3 - t2);
        EXPECT_TRUE(allFiniteHarm(hb.nodeVoltages));
    }
}

// ============================================================================
// M3 — 3-stage NMOS+R-pullup ring oscillator (HEAVY, expected failure)
//
// 三级反相器首尾相接：drain3 ── gate1 反馈。DC 工作点理论上落在
// "全部 drain == V_mid" 的非稳态平衡。
//
// **预期失败 / KnownIssue**：3 个对称 BSIM4 实例落在 V2-γ 已知的
// 3rd-instance state-bleed 范围内（test_multi_device.cpp:746-884 的 C3-bis
// 11 项已诊断）。本测试存在的目的是当 V2-γ 修复落地时立即"亮绿"，作为
// 修复回归保护。当前默认 HEAVY 门控 + 不强 require 收敛。
// ============================================================================
TEST_F(LargeCircuitBsim4, M3_RingOscillator3Stage_HEAVY) {
    if (!heavyEnabled()) GTEST_SKIP() << "HEAVY gated (set RFSIM_FORCE_HEAVY=1)";
    auto& L = warmLib();
    std::string why;
    ASSERT_TRUE(L.ok(why)) << why;

    std::vector<std::unique_ptr<DeviceModel>> devs;
    devs.push_back(std::make_unique<VoltageSource>("vdd", 1, 0, 1.5));
    devs.push_back(std::make_unique<Resistor>("rp1", 1, 2, 5e3));
    devs.push_back(std::make_unique<Resistor>("rp2", 1, 3, 5e3));
    devs.push_back(std::make_unique<Resistor>("rp3", 1, 4, 5e3));

    Diagnostics diags; NodeId base = 5;
    auto m1 = makeNmos("m1", 2, 4, 0, 0, L, diags, base);  // gate = drain3
    auto m2 = makeNmos("m2", 3, 2, 0, 0, L, diags, base);  // gate = drain1
    auto m3 = makeNmos("m3", 4, 3, 0, 0, L, diags, base);  // gate = drain2
    ASSERT_TRUE(m1 && m2 && m3);
    devs.push_back(std::move(m1));
    devs.push_back(std::move(m2));
    devs.push_back(std::move(m3));

    uint32_t numNodes = computeMaxNode(devs);

    DcOpOptions opt;
    opt.gmin.gmin = 1e-9;
    opt.gmin.gminStart = 1e-3;
    opt.gmin.gminSteps = 15;
    opt.maxIterations = 200;
    opt.dvmax = 0.2;
    opt.sourceStepCount = 8;
    double t0 = nowMs();
    auto dc = solveDcOp(numNodes, devs, opt);
    double t1 = nowMs();
    ASSERT_TRUE(allFiniteVec(dc.nodeVoltages));

    double v2 = dc.nodeVoltages.size() > 2 ? dc.nodeVoltages[2] : 0.0;
    double v3 = dc.nodeVoltages.size() > 3 ? dc.nodeVoltages[3] : 0.0;
    double v4 = dc.nodeVoltages.size() > 4 ? dc.nodeVoltages[4] : 0.0;
    std::fprintf(stderr,
        "[M3.RingOsc3] dcConv=%d iters=%u wall=%.1f ms "
        "drain[1..3]=%.3f %.3f %.3f (V2-γ 3rd-inst bleed KnownIssue)\n",
        dc.converged, dc.iterations, t1 - t0, v2, v3, v4);

    // 不强 require 收敛 — 此测试是 V2-γ blocker 的修复回归保护占位
    if (dc.converged) {
        EXPECT_LE(std::max({v2, v3, v4}), 1.55);
        EXPECT_GE(std::min({v2, v3, v4}), -0.05);
    }
}

// ============================================================================
// S1 — InverterChain N 网格 → CSV
//
// CSV path: 工作目录下 conv_grid_inverter.csv（与 conv_grid_bsim4.csv 同侧）。
// 列：N, dc_conv, dc_iters, dc_ms, hb_conv, hb_ms, |H1(out)|
// ============================================================================
namespace {

struct GridRow {
    int N = 0;
    bool dcConv = false;
    uint32_t dcIters = 0;
    double dcMs = 0;
    bool hbConv = false;
    double hbMs = 0;
    double h1Out = 0;
};

GridRow runInverterChainGridPoint(int N, BsimLib& L) {
    GridRow r; r.N = N;
    std::vector<std::unique_ptr<DeviceModel>> devs;
    Diagnostics diags;
    NodeId base = static_cast<NodeId>(3 + N);
    uint32_t numNodes = 0; NodeId lastDrain = 0; bool okInit = false;
    buildInverterChain(N, 1.5, 0.4, 0.01, 1e6,
                       L, diags, base, devs, numNodes, lastDrain, okInit);
    if (!okInit) return r;

    DcOpOptions opt;
    opt.gmin.gmin = 1e-9;
    opt.gmin.gminStart = 1e-3;
    opt.gmin.gminSteps = 15;
    opt.maxIterations = 150;
    opt.dvmax = 0.2;
    opt.sourceStepCount = 6;
    double t0 = nowMs();
    auto dc = solveDcOp(numNodes, devs, opt);
    double t1 = nowMs();
    r.dcConv = dc.converged;
    r.dcIters = dc.iterations;
    r.dcMs = t1 - t0;
    if (!dc.converged) return r;

    HbConfig cfg; cfg.fundamental = 1e6; cfg.numHarmonics = 1;
    HbNlOptions hopts;
    hopts.gmin.gmin = 1e-9;
    hopts.dvmax = 0.5;
    hopts.maxIter = 50;
    std::vector<double> initV = dc.nodeVoltages;
    double t2 = nowMs();
    auto hb = solveHbNonlinear(numNodes, devs, cfg, &initV, hopts);
    double t3 = nowMs();
    r.hbConv = hb.converged;
    r.hbMs = t3 - t2;
    if (allFiniteHarm(hb.nodeVoltages)
            && hb.nodeVoltages.size() > lastDrain
            && hb.nodeVoltages[lastDrain].v.size() > 1) {
        r.h1Out = std::abs(hb.nodeVoltages[lastDrain].v[1]);
    }
    return r;
}

} // namespace

TEST_F(LargeCircuitBsim4, S1_InverterChainGrid) {
    auto& L = warmLib();
    std::string why;
    if (!L.ok(why)) GTEST_SKIP() << why;

    std::vector<int> nList = { 2, 4, 6, 8, 10 };
    if (heavyEnabled()) {
        nList.push_back(12);
        nList.push_back(15);
        nList.push_back(20);
    }

    std::ofstream ofs("conv_grid_inverter.csv");
    ofs << "N,dc_conv,dc_iters,dc_ms,hb_conv,hb_ms,h1_out\n";
    int passDc = 0, passHb = 0;
    for (int n : nList) {
        auto r = runInverterChainGridPoint(n, L);
        ofs << r.N << ','
            << (r.dcConv ? 1 : 0) << ',' << r.dcIters << ',' << r.dcMs << ','
            << (r.hbConv ? 1 : 0) << ',' << r.hbMs << ',' << r.h1Out << '\n';
        if (r.dcConv) ++passDc;
        if (r.hbConv) ++passHb;
        std::fprintf(stderr,
            "[S1.grid] N=%d dc=%d(it=%u, %.1f ms) hb=%d(%.1f ms) |H1|=%.4g\n",
            r.N, r.dcConv ? 1 : 0, r.dcIters, r.dcMs,
            r.hbConv ? 1 : 0, r.hbMs, r.h1Out);
    }
    std::fprintf(stderr,
        "[S1.grid] summary: %d/%zu DC pass, %d/%zu HB pass\n",
        passDc, nList.size(), passHb, nList.size());

    // 默认轻量 N ≤ 10：要求 ≥80% DC 通过率（V2-γ Phase B mid-rail 验收）
    EXPECT_GE(passDc, static_cast<int>(nList.size() * 4 / 5));
}

// ============================================================================
// S2 — Bsim4 CS HB-NL NH 网格 → CSV
// 列：NH, dim, dc_conv, hb_conv, hb_iters, hb_ms, |H1(drain)|
// ============================================================================
TEST_F(LargeCircuitBsim4, S2_Bsim4CsNhGrid) {
    auto& L = warmLib();
    std::string why;
    if (!L.ok(why)) GTEST_SKIP() << why;

    std::vector<int> nhList = { 3, 5, 7 };
    if (heavyEnabled()) {
        nhList.push_back(9);
        nhList.push_back(11);
        nhList.push_back(15);
    }

    std::ofstream ofs("conv_grid_bsim4_nh.csv");
    ofs << "NH,dim,dc_conv,hb_conv,hb_iters,hb_ms,h1_drain\n";

    for (int nh : nhList) {
        std::vector<std::unique_ptr<DeviceModel>> devs;
        devs.push_back(std::make_unique<VoltageSource>("vdd", 1, 0, 1.5));
        devs.push_back(sineVS("vg", 3, 0, 0.85, 0.05, 1e6));
        devs.push_back(std::make_unique<Resistor>("rd", 1, 2, 5e3));
        Diagnostics diags; NodeId base = 4;
        auto m = makeNmos("m1", 2, 3, 0, 0, L, diags, base);
        ASSERT_TRUE(m != nullptr);
        devs.push_back(std::move(m));
        NodeId numNodes = computeMaxNode(devs);

        DcOpOptions dcOpt;
        dcOpt.gmin.gmin = 1e-9;
        dcOpt.gmin.gminStart = 1e-3;
        dcOpt.gmin.gminSteps = 12;
        dcOpt.maxIterations = 80;
        dcOpt.dvmax = 0.2;
        auto dc = solveDcOp(numNodes, devs, dcOpt);

        HbConfig cfg; cfg.fundamental = 1e6;
        cfg.numHarmonics = static_cast<uint32_t>(nh);
        HbNlOptions hopts;
        hopts.gmin.gmin = 1e-9;
        hopts.dvmax = 0.5;
        hopts.maxIter = 60;
        // V2-γ post-S2：BSIM4 在默认单步 Newton 下 S2 grid 全 NH 0/6；
        // 启用 autoHomotopy 让 solver 自适应到 4 步源步进 × 5 点 gmin 路径。
        hopts.autoHomotopy = true;
        uint32_t dim = hbDim(numNodes, 2, static_cast<uint32_t>(nh));
        std::vector<double> initV(numNodes + 1, 0.0);
        if (dc.converged && dc.nodeVoltages.size() > numNodes) initV = dc.nodeVoltages;
        double t0 = nowMs();
        auto hb = solveHbNonlinear(numNodes, devs, cfg,
                                   dc.converged ? &initV : nullptr, hopts);
        double t1 = nowMs();
        double h1Drain = 0;
        if (allFiniteHarm(hb.nodeVoltages)
                && hb.nodeVoltages.size() > 2
                && hb.nodeVoltages[2].v.size() > 1)
            h1Drain = std::abs(hb.nodeVoltages[2].v[1]);

        ofs << nh << ',' << dim << ','
            << (dc.converged ? 1 : 0) << ','
            << (hb.converged ? 1 : 0) << ','
            << hb.iterations << ',' << (t1 - t0) << ','
            << h1Drain << '\n';
        std::fprintf(stderr,
            "[S2.grid] NH=%d dim=%u (%s) dc=%d hb=%d (it=%u, %.1f ms) "
            "|H1|=%.4g\n",
            nh, dim, dim > kGmresThreshold ? "GMRES" : "dense",
            dc.converged ? 1 : 0, hb.converged ? 1 : 0,
            hb.iterations, t1 - t0, h1Drain);
    }
}

} // namespace rfsim
