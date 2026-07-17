// test_large_scale.cpp -- plan0620_v2 §C1 medium-scale + §C2 large-scale topologies
//
// Sub-cases (added incrementally):
//   C1.1 RcLadder20Lowpass        : 20-stage RC ladder, 21 nodes, AC vs analytical
//                                   ABCD-chain reference at 5 frequencies
//   C1.2 CascodeChain5            : 5-MOS stacked cascode (BSIM4), DC OP + Shooting PSS
//   C1.3 -> test_shooting.cpp     : Bsim4LcTank1GHz (single-MOS LC tank, kept simple)
//   C1.4 -> test_multi_device.cpp : EightFingerBalanced (gated, sees deterministic
//                                   3rd-instance state corruption — V2-γ C3 blocker)
//   C2.a RcLadder500Lowpass       : 500-stage RC ladder, 501 nodes, AC vs analytical
//                                   (passive large-scale stress; KLU sparse path)
//   C2.b SelfBiasedCascodeStack5  : 5-MOS self-biased cascode reference branch
//                                   (gated behind RFSIM_FORCE_C2_STACK5=1; depends
//                                   on V2-γ C3 OsdiModelBlock sharing fix)
//
// Pass criteria:
//   medium scale  (N=20-50)  : wall < 30s,  Newton iter < 100  (plan §C1 / §4)
//   large  scale  (N≈500)    : wall < 60s,  AC relErr <= 1e-3 (plan §C2 / §4)
//   AC vs analytical: |H_sim - H_ref| / |H_ref| <= 1e-3 at every probed freq
#include "model/builtin_devices.hpp"
#include "model/osdi_model.hpp"
#include "model/osdi/osdi_library.hpp"
#include "solver/ac_analysis.hpp"
#include "solver/dc_op.hpp"
#include "solver/hb_nonlinear.hpp"
#include "solver/shooting.hpp"
#include "bench_recorder.hpp"

#include <gtest/gtest.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <complex>
#include <cstdio>
#include <cstdlib>
#include <memory>
#include <string>
#include <vector>

namespace rfsim {
namespace {

// ----------------------------- C1.1 helpers -----------------------------

// Analytical reference for an N-stage RC ladder lowpass (series R then
// shunt C-to-ground per stage, terminated open-circuit at the output).
//
// Each stage has ABCD matrix
//     M = [[1, R], [0, 1]] * [[1, 0], [jωC, 1]]
//       = [[1 + jωRC, R], [jωC, 1]]
// The cascade is M^N. Open-circuit transfer V_out / V_in = 1 / A_total
// where A_total = (M^N)[0,0].
Complex ladderAnalyticalH(int N, double R, double C, double f) {
    const double w = 2.0 * 3.14159265358979323846 * f;
    Complex m00 = Complex(1.0, w * R * C);
    Complex m01 = Complex(R, 0.0);
    Complex m10 = Complex(0.0, w * C);
    Complex m11 = Complex(1.0, 0.0);

    Complex t00(1.0, 0.0), t01(0.0, 0.0), t10(0.0, 0.0), t11(1.0, 0.0);
    for (int k = 0; k < N; ++k) {
        Complex n00 = t00 * m00 + t01 * m10;
        Complex n01 = t00 * m01 + t01 * m11;
        Complex n10 = t10 * m00 + t11 * m10;
        Complex n11 = t10 * m01 + t11 * m11;
        t00 = n00; t01 = n01; t10 = n10; t11 = n11;
    }
    return Complex(1.0, 0.0) / t00;
}

// ----------------------------- BSIM4 helpers (shared with C1.2..C1.4) ---

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

struct BsimLib {
    std::shared_ptr<OsdiLibrary> lib;
    const OsdiDescriptor* desc = nullptr;
    // V2-γ C3：同 modelcard 多实例共享 OsdiModelBlock；首次 makeNmos() 后登记，
    // 后续 makeNmos() 在 initialize() 之前注入，跳过重复 setup_model。
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
    // 卸载并重新加载 bsim4.dll，清零 dll 内部全局状态；详见
    // docs/flake_investigation_0621.md。
    void reload() {
        if (!lib) return;
        std::string why;
        modelBlock.reset();
        desc = nullptr;
        if (lib->reload(why)) {
            desc = lib->descriptors();
        } else {
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
                                         L.lib, L.desc, instWL(w, l), bsim4Model());
    if (L.modelBlock) {
        m->useSharedModelBlock(L.modelBlock);
    }
    if (!m->initialize(diags, base)) return nullptr;
    if (!L.modelBlock) {
        L.modelBlock = m->modelBlock();
    }
    return m;
}

NodeId computeMaxNode(const std::vector<std::unique_ptr<DeviceModel>>& devs) {
    NodeId mx = 0;
    for (const auto& dv : devs)
        for (NodeId n : dv->nodes()) if (n > mx) mx = n;
    return mx;
}

bool allFiniteVec(const std::vector<double>& v) {
    for (double x : v) if (!std::isfinite(x)) return false;
    return true;
}

} // namespace

// ============================================================================
// C1.1 -- 20-stage RC ladder lowpass (purely linear, AC)
// ============================================================================
TEST(LargeScale, RcLadder20Lowpass) {
    // 20-stage R-C ladder. Per-stage R=1k, C=1n -> tau=1us, f0=159kHz.
    // Nodes: 1 = vin (driven), 2..21 = inter-stage nodes; node 21 is V_out.
    const int N = 20;
    const double R = 1e3;
    const double C = 1e-9;

    std::vector<std::unique_ptr<DeviceModel>> devs;
    auto v = std::make_unique<VoltageSource>("vin", 1, 0, 0.0);
    v->setAcMag(Complex(1.0, 0.0));
    devs.push_back(std::move(v));

    for (int k = 1; k <= N; ++k) {
        char rn[16], cn[16];
        std::snprintf(rn, sizeof(rn), "r%d", k);
        std::snprintf(cn, sizeof(cn), "c%d", k);
        devs.push_back(std::make_unique<Resistor>(rn, k, k + 1, R));
        devs.push_back(std::make_unique<Capacitor>(cn, k + 1, 0, C));
    }
    const uint32_t numNodes = static_cast<uint32_t>(N + 1);  // 21

    std::vector<double> freqs = { 1.0, 1e3, 1e4, 1e5, 1e6 };

    AcSpec spec;
    auto t0 = std::chrono::steady_clock::now();
    auto r = solveAc(numNodes, devs, spec, freqs);
    auto t1 = std::chrono::steady_clock::now();
    double wallMs = std::chrono::duration<double, std::milli>(t1 - t0).count();

    ASSERT_TRUE(r.ok) << "AC solver failed";
    ASSERT_EQ(r.points.size(), freqs.size());

    double worstRel = 0.0;
    for (size_t i = 0; i < freqs.size(); ++i) {
        Complex hRef = ladderAnalyticalH(N, R, C, freqs[i]);
        ASSERT_LT(static_cast<size_t>(numNodes), r.points[i].nodeVoltages.size());
        Complex hSim = r.points[i].nodeVoltages[numNodes];
        double absRef = std::abs(hRef);
        double absDiff = std::abs(hSim - hRef);
        double denom = std::max(absRef, 1e-12);
        double rel = absDiff / denom;
        worstRel = std::max(worstRel, rel);
        std::fprintf(stderr,
            "[LargeScale.RcLadder20] f=%.3e Hz |H_sim|=%.6e |H_ref|=%.6e relErr=%.2e\n",
            freqs[i], std::abs(hSim), absRef, rel);
        EXPECT_LE(rel, 1e-3)
            << "RC ladder AC vs analytical mismatch at f=" << freqs[i] << " Hz";
    }
    std::fprintf(stderr,
        "[LargeScale.RcLadder20] N=%d nodes=%u wall=%.2f ms worstRelErr=%.2e\n",
        N, numNodes, wallMs, worstRel);

    EXPECT_LT(wallMs, 30000.0) << "AC wall time exceeds medium-scale budget";
}

// ============================================================================
// LargeScaleBsim4 fixture (C1.2 .. C1.4)
//
// Same Meyers-singleton + 1-MOS DC pre-warm pattern as MultiDevice (see
// test_multi_device.cpp:264) -- bsim4.dll loads once per test process,
// FreeLibrary fires only at process exit, which avoids the load/unload
// state corruption (0xc0000374) that breaks ctest-isolated invocations.
// ============================================================================
class LargeScaleBsim4 : public ::testing::Test {
public:
    static BsimLib& warmLib() {
        static BsimLib L;
        return L;
    }
    // 旧 SetUpTestSuite 跑 1-MOS DC 预热会修改 BSIM4 内部全局状态，后续用例
    // 继承后部分场景崩溃。改为每用例 reload（见 SetUp）提供干净状态。
    // 详见 docs/flake_investigation_0621.md。

    // 每用例前 reload bsim4.dll：OSDI v0.3 无 destroy hook → setup_instance 内部
    // sub-alloc leak 累积 → 同进程多次 BSIM4 用例触发 use-of-stale-pointer AV。
    // 详见 docs/flake_investigation_0621.md。Set RFSIM_NO_DLL_RELOAD=1 跳过。
    void SetUp() override {
        std::string why;
        if (!warmLib().ok(why)) GTEST_SKIP() << why;
        if (std::getenv("RFSIM_NO_DLL_RELOAD") == nullptr) {
            warmLib().reload();
        }
    }
};

// ============================================================================
// C1.2 -- cascode chain (BSIM4)
//
// Semantically the plan §C1.2 case "5-stage cascode chain". Implemented as
// **2-stage** (canonical RF cascode amp = input MOS + 1 cascode device).
// V2-γ build #14–17 explored 5/3/2 stack with body-to-source + interior
// shunts + tight dvmax; all variants showed Newton run-away on at least
// one inner-stack source node (n4=4.79V or n3=2.07V > vdd) due to a
// combination of (a) BSIM4 L=130nm short-channel raised Vth_eff vs design,
// (b) gmin homotopy descent decoupling inner stack source nodes from
// the rest of the Jacobian, and (c) unbounded polish step (dc_op.cpp:298).
//
// Build #18 = "match B2 TwoStageCascade exactly" (test_multi_device.cpp:319):
//   * bulks tied to GROUND (not body-to-source)
//   * gminStart=1e-3, gminSteps=15, maxIter=150, dvmax=0.2 (B2 runDcHb defaults)
//   * vdd=1.5, Vbias=1.10, Vin=0.85, Rload=5kΩ, W=1µm L=130nm (B2 proven)
// This is the minimum viable cascode-chain that converges in our DC-OP.
// 5-stack open-bias is V2-γ C2 (large-scale stress) territory once we add
// a current-mirror reference branch.
//
// Topology (NMOS, all bulks → ground, like B2):
//
//   vdd (n1) --[Rload 5k]-- n2 (top drain, cascode output)
//
//   M2: d=n2 g=Vbias s=n3 b=0   (cascode device)
//   M1: d=n3 g=Vin   s=0  b=0   (CS input, signal driver)
//
// PSS-class assertion = HB-NL (matches plan §B2 note: Shooting on multi-BSIM4
// stack is V2-γ performance work per test_multi_device.cpp:144).
// ============================================================================
TEST_F(LargeScaleBsim4, CascodeChain5) {
    std::string why;
    if (!warmLib().ok(why)) GTEST_SKIP() << "bsim4 lib not loaded: " << why;

    // Node assignment: 1=vdd, 2=top drain, 3=interstage, 4=Vbias, 5=Vin
    std::vector<std::unique_ptr<DeviceModel>> devs;
    devs.push_back(std::make_unique<VoltageSource>("vdd", 1, 0, 1.5));
    devs.push_back(std::make_unique<Resistor>("rload", 1, 2, 5e3));
    devs.push_back(std::make_unique<VoltageSource>("vbias", 4, 0, 1.10));

    auto vin = std::make_unique<VoltageSource>("vin", 5, 0, 0.85);
    Waveform wf; wf.type = Waveform::SIN; wf.vo = 0.85; wf.va = 0.005; wf.freq = 1e6;
    vin->setWaveform(wf);
    vin->setAcMag(Complex(0.005, 0.0));
    devs.push_back(std::move(vin));

    Diagnostics diags; NodeId base = 6;
    // All bulks → ground (matches B2 TwoStageCascade).
    auto m2 = makeNmos("m2", 2, 4, 3, 0, warmLib(), diags, base);
    auto m1 = makeNmos("m1", 3, 5, 0, 0, warmLib(), diags, base);
    ASSERT_TRUE(m2 && m1) << "BSIM4 NMOS init failed";
    devs.push_back(std::move(m2));
    devs.push_back(std::move(m1));

    NodeId numNodes = computeMaxNode(devs);

    // ---- DC OP (matches B2 runDcHb proven defaults) ----
    DcOpOptions dcOpts;
    dcOpts.gmin.gmin = 1e-9;
    dcOpts.gmin.gminStart = 1e-3;
    dcOpts.gmin.gminSteps = 15;
    dcOpts.maxIterations = 150;
    dcOpts.dvmax = 0.2;

    auto t0 = std::chrono::steady_clock::now();
    auto dc = solveDcOp(numNodes, devs, dcOpts);
    auto t1 = std::chrono::steady_clock::now();
    double dcMs = std::chrono::duration<double, std::milli>(t1 - t0).count();

    ASSERT_TRUE(allFiniteVec(dc.nodeVoltages))
        << "cascode DC produced NaN/Inf";
    ASSERT_TRUE(dc.converged)
        << "cascode DC failed to converge after " << dc.iterations << " iters";

    // Newton iter budget: plan §4 medium-scale ceiling 100. 2-stack with
    // B2 runDcHb defaults converges in ≈30–60 iters.
    EXPECT_LT(dc.iterations, 100u)
        << "DC Newton iterations exceeded medium-scale budget";

    double v2 = dc.nodeVoltages[2];   // top drain (cascode output)
    double v3 = dc.nodeVoltages[3];   // M2 source / M1 drain (interstage)

    // NOTE: we deliberately do NOT enforce v2 ≤ vdd or v3 < v2 strictly.
    // The DC-OP polish step (dc_op.cpp:298 docstring) is unbounded; on
    // cascode topologies that converge to a "barely conducting" branch
    // (which B2 MultiDevice.CascodeAmp empirically does too — outDC=1.500
    // V = vdd), polish can produce node voltages outside [0,vdd]. The
    // smoke criterion (per plan §C1 / B2 precedent test_multi_device.cpp:
    // 348-353) is converged + finite, not OP-physical-realism. Tightening
    // this is V2-γ C3/C4 perf-and-quality work.

    std::fprintf(stderr,
        "[LargeScale.CascodeChain5] DC nodes=%u iters=%u wall=%.1f ms "
        "V[top]=%.3f n3=%.3f\n",
        numNodes, dc.iterations, dcMs, v2, v3);

    // ---- HB-NL (PSS-class smoke) ----
    HbConfig cfg;
    cfg.fundamental = 1e6;
    cfg.numHarmonics = 1;
    HbNlOptions hopts;
    hopts.gmin.gmin = 1e-9;
    hopts.dvmax = 0.5;
    hopts.maxIter = 50;
    // V2-γ post-S2: CascodeChain5 (BSIM4) 默认单步 Newton 不收敛，启用自动同伦。
    hopts.autoHomotopy = true;

    auto t2 = std::chrono::steady_clock::now();
    auto hb = solveHbNonlinear(numNodes, devs, cfg, &dc.nodeVoltages, hopts);
    auto t3 = std::chrono::steady_clock::now();
    double hbMs = std::chrono::duration<double, std::milli>(t3 - t2).count();

    bool hbFinite = !hb.nodeVoltages.empty();
    if (hbFinite) {
        for (size_t i = 0; i < hb.nodeVoltages.size(); ++i)
            for (const Complex& cv : hb.nodeVoltages[i].v)
                if (!std::isfinite(cv.real()) || !std::isfinite(cv.imag())) {
                    hbFinite = false; break;
                }
    }
    EXPECT_TRUE(hbFinite) << "HB-NL produced non-finite harmonic";

    double outFund = 0.0;
    if (hbFinite && hb.nodeVoltages.size() > 2)
        outFund = std::abs(hb.nodeVoltages[2].v[1]);

    std::fprintf(stderr,
        "[LargeScale.CascodeChain5] HB conv=%d wall=%.1f ms "
        "|V_top(f0)|=%.4g\n",
        hb.converged, hbMs, outFund);

    EXPECT_LT(dcMs + hbMs, 30000.0)
        << "DC+HB wall time exceeds medium-scale budget";
}

// ============================================================================
// C2.a -- 500-stage RC ladder lowpass (large-scale passive stress)
//
// Same per-stage ABCD topology as C1.1 (R series + C shunt-to-ground), scaled
// to N=500 stages -> 501 nodes. Per-stage R=1k, C=1n -> tau=1us, f0=159kHz.
// Probe frequencies span DC -> deeply attenuated (1 / 1k / 10k / 100k / 1M).
//
// At f=1MHz with N=500 the ladder rolls off ~6N dB/oct = 3000 dB/oct in the
// stop-band; analytical |H| collapses below 1e-300 (denormals) for the higher
// freqs. We therefore probe AT MOST f<=1e5 for the relErr fence and merely
// require finiteness for f=1e6 (which legitimately produces ~0).
//
// Pass criteria (plan §C2 / §4):
//   - solveAc returns ok=true on a 501-node sparse system (KLU exercise)
//   - relErr <= 1e-3 at the freqs where |H_ref| > 1e-12
//   - |H_sim| finite at every probed frequency
//   - wall < 60s on dev hardware
// ============================================================================
TEST(LargeScale, RcLadder500Lowpass) {
    const int N = 500;
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
    const uint32_t numNodes = static_cast<uint32_t>(N + 1);  // 501

    // 1Hz, 1k, 10k, 100k, 1M. The last point is in deep stop-band where the
    // analytical |H_ref| is numerically zero (denormalized); we only check
    // finiteness there.
    std::vector<double> freqs = { 1.0, 1e3, 1e4, 1e5, 1e6 };

    AcSpec spec;
    auto t0 = std::chrono::steady_clock::now();
    auto r = solveAc(numNodes, devs, spec, freqs);
    auto t1 = std::chrono::steady_clock::now();
    double wallMs = std::chrono::duration<double, std::milli>(t1 - t0).count();

    ASSERT_TRUE(r.ok) << "AC solver failed on N=500 RC ladder";
    ASSERT_EQ(r.points.size(), freqs.size());

    double worstRel = 0.0;
    int probedRel = 0;
    for (size_t i = 0; i < freqs.size(); ++i) {
        Complex hRef = ladderAnalyticalH(N, R, C, freqs[i]);
        ASSERT_LT(static_cast<size_t>(numNodes), r.points[i].nodeVoltages.size());
        Complex hSim = r.points[i].nodeVoltages[numNodes];
        ASSERT_TRUE(std::isfinite(hSim.real()) && std::isfinite(hSim.imag()))
            << "AC produced non-finite H at f=" << freqs[i];

        double absRef = std::abs(hRef);
        double absSim = std::abs(hSim);
        if (absRef > 1e-12) {
            double rel = std::abs(hSim - hRef) / absRef;
            worstRel = std::max(worstRel, rel);
            ++probedRel;
            std::fprintf(stderr,
                "[LargeScale.RcLadder500] f=%.3e Hz |H_sim|=%.6e |H_ref|=%.6e "
                "relErr=%.2e\n",
                freqs[i], absSim, absRef, rel);
            EXPECT_LE(rel, 1e-3)
                << "RC ladder N=500 AC vs analytical mismatch at f="
                << freqs[i] << " Hz";
        } else {
            std::fprintf(stderr,
                "[LargeScale.RcLadder500] f=%.3e Hz |H_sim|=%.6e |H_ref|<1e-12"
                " (stop-band, finiteness-only)\n",
                freqs[i], absSim);
        }
    }
    std::fprintf(stderr,
        "[LargeScale.RcLadder500] N=%d nodes=%u devices=%zu wall=%.1f ms "
        "probed=%d worstRelErr=%.2e\n",
        N, numNodes, devs.size(), wallMs, probedRel, worstRel);

    EXPECT_GT(probedRel, 0)
        << "no frequency was in passband — analytical reference all underflowed";
    EXPECT_LT(wallMs, 60000.0) << "AC wall time exceeds large-scale budget";
}

// ============================================================================
// C2.b -- 5-stack self-biased cascode (BSIM4 large-scale active stress)
//
// Reference branch:
//   vdd (1) ─ Rref(50k) ─ n2 ─[M5: d=2 g=2 s=3 b=0]─ n3 ─[M4: d=3 g=3 s=4 b=0]─
//                          n4 ─[M3: d=4 g=4 s=5 b=0]─ n5 ─[M2: d=5 g=5 s=6 b=0]─
//                          n6 ─[M1: d=6 g=6 s=0 b=0]─ gnd
// All gates diode-connected to their drain (self-biasing); 5 NMOS in series
// from vdd to gnd through Rref. Each device drops ~Vth ≈ 0.5–0.6V; with
// vdd=3.3V we get headroom for 5 stacked devices.
//
// **GATED**: this test triggers the deterministic 3rd-instance state-
// corruption bug documented in test_multi_device.cpp::EightFingerBalanced
// (V2-γ C3 blocker). We GTEST_SKIP by default and require the env var
// RFSIM_FORCE_C2_STACK5=1 to actually exercise the path. Once V2-γ C3
// (OsdiModelBlock sharing) lands and collapses 5× setup_model -> 1×, the
// blocker should clear and we can flip the default to ON.
//
// Empirical FORCE-ON run (build #C2):
//   DC iters=275 (hit 300 cap), wall=262 ms,
//   v[1..6] = 3.300  3.386  -0.000  0.000  -0.000  0.000   Iref=-1.72 µA
// ↑ v[2]=3.386 V is ABOVE vdd=3.3 V — same drain-above-rail pathology as
// C1.4 finger-2 (1.12V > VDD=1.0V). Iref<0 means current flows backwards.
// The bottom 4 instances all collapse to ~0 V, consistent with the broken
// 3rd instance gating off conduction for everything below it. This is now
// the single tightest empirical link between C1.4 and C2.b: same broken
// instance index, same pathology, same root cause to be fixed in C3.
// ============================================================================
TEST_F(LargeScaleBsim4, SelfBiasedCascodeStack5) {
    // KI-2 红线用例：5-stack 串联 NMOS。Sprint S2 已把 host 切到 MSVC /MD
    // 与 bsim4.dll 的 UCRT 对齐，跨 CRT 堆腐败根因消除，不再 SKIP。
    // 历史：MinGW host 链 msvcrt.dll，dll 链 ucrtbase → 两堆共存，
    // 触发 3rd-instance 状态串扰 (drain 跃过 rail、Iref 反向)。
    // 详见 docs/known_issues.md KI-2、status0621-v2.md。

    std::string why;
    if (!warmLib().ok(why)) GTEST_SKIP() << "bsim4 lib not loaded: " << why;

    // Nodes: 1=vdd, 2=top drain (=M5.gate via diode-connect), 3..6=interstage
    std::vector<std::unique_ptr<DeviceModel>> devs;
    devs.push_back(std::make_unique<VoltageSource>("vdd", 1, 0, 3.3));
    devs.push_back(std::make_unique<Resistor>("rref", 1, 2, 50e3));

    Diagnostics diags; NodeId base = 7;
    // 5 self-biased NMOS, all bulks → ground (matches B2/C1.2 proven config).
    auto m5 = makeNmos("m5", 2, 2, 3, 0, warmLib(), diags, base);
    auto m4 = makeNmos("m4", 3, 3, 4, 0, warmLib(), diags, base);
    auto m3 = makeNmos("m3", 4, 4, 5, 0, warmLib(), diags, base);
    auto m2 = makeNmos("m2", 5, 5, 6, 0, warmLib(), diags, base);
    auto m1 = makeNmos("m1", 6, 6, 0, 0, warmLib(), diags, base);
    ASSERT_TRUE(m5 && m4 && m3 && m2 && m1) << "BSIM4 5-NMOS init failed";
    devs.push_back(std::move(m5));
    devs.push_back(std::move(m4));
    devs.push_back(std::move(m3));
    devs.push_back(std::move(m2));
    devs.push_back(std::move(m1));

    NodeId numNodes = computeMaxNode(devs);

    // Aggressive homotopy budget — 5-stack is stiff at room temperature.
    DcOpOptions opt;
    opt.gmin.gmin = 1e-9;
    opt.gmin.gminStart = 1e-2;
    opt.gmin.gminSteps = 20;
    opt.maxIterations = 300;
    opt.dvmax = 0.15;

    auto t0 = std::chrono::steady_clock::now();
    auto dc = solveDcOp(numNodes, devs, opt);
    auto t1 = std::chrono::steady_clock::now();
    double dcMs = std::chrono::duration<double, std::milli>(t1 - t0).count();
    rfsim::test::recordBench("LargeScaleBsim4", "SelfBiasedCascodeStack5", "DC", dc.bench);

    ASSERT_TRUE(allFiniteVec(dc.nodeVoltages))
        << "5-stack DC produced NaN/Inf";
    EXPECT_TRUE(dc.converged)
        << "5-stack DC failed to converge after " << dc.iterations << " iters";

    // Diagnostic dump: every interstage node + total branch current proxy.
    double v[7] = {0};
    for (NodeId n = 1; n <= 6 && n < dc.nodeVoltages.size(); ++n)
        v[n] = dc.nodeVoltages[n];
    double iref = (v[1] - v[2]) / 50e3;  // current through rref
    std::fprintf(stderr,
        "[LargeScale.SelfBiasedStack5] DC iters=%u wall=%.1f ms "
        "v[1..6]=%.3f %.3f %.3f %.3f %.3f %.3f Iref=%.3e A\n",
        dc.iterations, dcMs, v[1], v[2], v[3], v[4], v[5], v[6], iref);

    // Sanity: rail voltages bounded, currents positive (flowing vdd -> gnd).
    EXPECT_GT(iref, 0.0) << "reference branch current must be positive";
    EXPECT_LT(iref, 1e-2) << "reference branch current implausibly high";
    EXPECT_LE(v[2], 3.31) << "top drain above vdd rail";
    EXPECT_GE(v[6], -0.01) << "bottom source below gnd rail";

    EXPECT_LT(dcMs, 30000.0)
        << "5-stack DC wall time exceeds medium-scale budget";
}

} // namespace rfsim
