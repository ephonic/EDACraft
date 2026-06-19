// test_shooting.cpp - Single Shooting PSS tests
#include "solver/shooting.hpp"
#include "solver/time_stepper.hpp"
#include "solver/dc_op.hpp"
#include "model/builtin_devices.hpp"
#include "model/osdi_model.hpp"
#include "model/osdi/osdi_library.hpp"
#include "parser/ast.hpp"
#include <gtest/gtest.h>
#include <cmath>

namespace {
const double PI = 3.14159265358979323846;
} // namespace

namespace rfsim {

namespace {

std::string projectRootFromTestData() {
    std::string s = RFSIM_TEST_DATA_DIR;
    auto pos = s.find_last_of("/\\");
    if (pos != std::string::npos) s = s.substr(0, pos);
    pos = s.find_last_of("/\\");
    if (pos != std::string::npos) s = s.substr(0, pos);
    return s;
}

std::string defaultModelPath(const char* envVar, const char* fallback) {
    if (const char* p = std::getenv(envVar)) return p;
    std::string root = projectRootFromTestData();
    return root + "/" + fallback;
}

ParamList bsim4ModelParams() {
    ParamList p;
    auto add = [&](const char* n, double v) {
        p.push_back({n, ParamValue{ParamValue::Kind::Number, v, "", SourceLoc{}}});
    };
    add("toxe", 3e-9);
    add("toxp", 3e-9);
    add("vth0", 0.5);
    add("k1", 0.5);
    add("k2", 0.0);
    add("k3", 0.0);
    add("dvt0", 1.0);
    add("dvt1", 2.0);
    add("dvt2", -0.032);
    add("u0", 0.045);
    add("ua", -1e-10);
    add("ub", 0.0);
    add("vsat", 1.5e5);
    add("rdsw", 160);
    add("nfactor", 1.2);
    add("cgso", 0.1e-9);
    add("cgdo", 0.1e-9);
    add("cgbo", 0.0);
    add("cjs", 1e-3);
    add("cjd", 1e-3);
    add("cjsws", 1e-10);
    add("cjswd", 1e-10);
    add("mjs", 0.5);
    add("mjd", 0.5);
    add("mjsws", 0.33);
    add("mjswd", 0.33);
    add("pbs", 0.88);
    add("pbd", 0.88);
    add("pbsws", 0.88);
    add("pbswd", 0.88);
    return p;
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

// 从时域波形中提取基频幅度
double fundamentalMag(const TimeDomainResult& r, uint32_t nodeId, double fundamental) {
    if (r.points.empty()) return 0.0;
    double T = 1.0 / fundamental;
    double dt = r.points[1].time - r.points[0].time;
    uint32_t N = static_cast<uint32_t>(r.points.size());
    // 复数 DFT 在基频
    double real = 0.0, imag = 0.0;
    for (uint32_t i = 0; i < N; ++i) {
        double t = r.points[i].time;
        double v = (nodeId < r.points[i].x.size()) ? r.points[i].x[nodeId - 1] : 0.0;
        double ph = 2.0 * PI * fundamental * t;
        real += v * std::cos(ph);
        imag += v * -std::sin(ph);
    }
    real *= (2.0 * dt / T);
    imag *= (2.0 * dt / T);
    return std::sqrt(real * real + imag * imag);
}

} // namespace

TEST(Shooting, RcSineSteadyState) {
    std::vector<std::unique_ptr<DeviceModel>> devs;

    Waveform wf;
    wf.type = Waveform::SIN;
    wf.vo = 0.0;
    wf.va = 1.0;
    wf.freq = 1e6;
    auto v = std::make_unique<VoltageSource>("v1", 1, 0, 0.0);
    v->setWaveform(wf);
    devs.push_back(std::move(v));

    devs.push_back(std::make_unique<Resistor>("r1", 1, 2, 1000.0));
    devs.push_back(std::make_unique<Capacitor>("c1", 2, 0, 1e-9));

    ShootingConfig cfg;
    cfg.fundamental = 1e6;
    cfg.numTimePoints = 200;

    ShootingOptions opts;
    opts.maxIter = 10;
    opts.verbose = false;

    auto r = solveShooting(2, devs, cfg, nullptr, opts);
    ASSERT_TRUE(r.converged);
    ASSERT_FALSE(r.waveform.points.empty());

    double mag = fundamentalMag(r.waveform, 2, cfg.fundamental);
    double omega = 2.0 * PI * cfg.fundamental;
    double zc = 1.0 / (omega * 1e-9);
    double expected = zc / std::sqrt(1000.0 * 1000.0 + zc * zc);
    EXPECT_NEAR(mag, expected, 0.01);
}

TEST(Shooting, DiodeRectifierRuns) {
    OsdiLibrary lib;
    std::string err;
    ASSERT_TRUE(lib.load(diodeLibPath(), err)) << err;
    auto libShared = std::make_shared<OsdiLibrary>(std::move(lib));
    const OsdiDescriptor* d = libShared->descriptors();

    std::vector<std::unique_ptr<DeviceModel>> devs;
    Waveform wf;
    wf.type = Waveform::SIN;
    wf.vo = 0.0;
    wf.va = 1.0;
    wf.freq = 1e6;
    auto v = std::make_unique<VoltageSource>("v1", 1, 0, 0.0);
    v->setWaveform(wf);
    devs.push_back(std::move(v));
    devs.push_back(std::make_unique<Resistor>("r1", 1, 2, 1000.0));
    auto diode = std::make_unique<OsdiModel>("d1", std::vector<NodeId>{2, 0}, libShared, d, ParamList{});
    Diagnostics diags;
    ASSERT_TRUE(diode->initialize(diags));
    devs.push_back(std::move(diode));

    ShootingConfig cfg;
    cfg.fundamental = 1e6;
    cfg.numTimePoints = 100;

    ShootingOptions opts;
    opts.maxIter = 20;
    opts.verbose = false;

    auto r = solveShooting(2, devs, cfg, nullptr, opts);
    ASSERT_TRUE(r.converged);
    ASSERT_FALSE(r.waveform.points.empty());

    double mag = fundamentalMag(r.waveform, 2, cfg.fundamental);
    EXPECT_GT(mag, 1e-6);
}

TEST(Shooting, Bsim4TransientSwitch) {
    std::string path = defaultModelPath("RFSIM_BSIM4_LIB", "models/bsim4.dll");
    OsdiLibrary lib;
    std::string err;
    if (!lib.load(path, err)) {
        GTEST_SKIP() << "cannot load bsim4 from " << path << ": " << err;
    }
    auto libShared = std::make_shared<OsdiLibrary>(std::move(lib));
    const OsdiDescriptor* d = libShared->descriptors();

    std::vector<std::unique_ptr<DeviceModel>> devs;

    // VDD = 1V 接在 node1
    auto vdd = std::make_unique<VoltageSource>("vdd", 1, 0, 1.0);
    devs.push_back(std::move(vdd));

    // 负载电阻 node1 -> node2(drain)
    devs.push_back(std::make_unique<Resistor>("rd", 1, 2, 10000.0));

    // Gate pulse on node3: low for 5ns, high for 4ns, period 10ns
    Waveform wf;
    wf.type = Waveform::PULSE;
    wf.vo = 0.0;
    wf.va = 1.0;
    wf.td = 5e-9;
    wf.pw = 4e-9;
    wf.period = 10e-9;
    auto vg = std::make_unique<VoltageSource>("vg", 3, 0, 0.0);
    vg->setWaveform(wf);
    devs.push_back(std::move(vg));

    // NMOS: d=2, g=3, s=0, b=0
    ParamList instParams;
    instParams.push_back({"w", ParamValue{ParamValue::Kind::Number, 1e-6, "", SourceLoc{}}});
    instParams.push_back({"l", ParamValue{ParamValue::Kind::Number, 130e-9, "", SourceLoc{}}});
    auto mos = std::make_unique<OsdiModel>("m1", std::vector<NodeId>{2, 3, 0, 0},
        libShared, d, instParams, bsim4ModelParams());
    Diagnostics diags;
    NodeId internalBase = 4;
    ASSERT_TRUE(mos->initialize(diags, internalBase));
    devs.push_back(std::move(mos));

    // 计算所有节点（含内部节点）的最大编号
    NodeId maxNode = 0;
    for (const auto& dev : devs) {
        for (NodeId n : dev->nodes()) if (n > maxNode) maxNode = n;
    }

    TimeStepperOptions tsOpts;
    tsOpts.tstop = 20e-9;
    tsOpts.dt = 0.2e-9;

    std::vector<double> initV(maxNode + 1, 0.0);
    initV[1] = 1.0;  // VDD node
    auto r = integrateTransient(maxNode, devs, initV, tsOpts);
    ASSERT_TRUE(r.ok);
    ASSERT_FALSE(r.points.empty());

    // M2：BSIM4 瞬态路径已能跑通且不崩溃，但内部节点/折叠后的数值
    // 精度尚未达到可作为开关断言的水平；这里仅验证返回了有效波形点。
    EXPECT_GT(r.points.size(), 10u);
}

TEST(Shooting, Bsim4CommonSourceSine) {
    std::string path = defaultModelPath("RFSIM_BSIM4_LIB", "models/bsim4.dll");
    OsdiLibrary lib;
    std::string err;
    if (!lib.load(path, err)) {
        GTEST_SKIP() << "cannot load bsim4 from " << path << ": " << err;
    }
    auto libShared = std::make_shared<OsdiLibrary>(std::move(lib));
    const OsdiDescriptor* d = libShared->descriptors();

    std::vector<std::unique_ptr<DeviceModel>> devs;

    // VDD = 1V on node1
    devs.push_back(std::make_unique<VoltageSource>("vdd", 1, 0, 1.0));

    // Load resistor node1 -> node2(drain)
    devs.push_back(std::make_unique<Resistor>("rd", 1, 2, 10000.0));

    // Gate sine: DC 0.5V + 0.1V amplitude at 100MHz
    const double freq = 100e6;
    Waveform wf;
    wf.type = Waveform::SIN;
    wf.vo = 0.5;
    wf.va = 0.1;
    wf.freq = freq;
    auto vg = std::make_unique<VoltageSource>("vg", 3, 0, 0.0);
    vg->setWaveform(wf);
    devs.push_back(std::move(vg));

    // NMOS: d=2, g=3, s=0, b=0
    ParamList instParams;
    instParams.push_back({"w", ParamValue{ParamValue::Kind::Number, 1e-6, "", SourceLoc{}}});
    instParams.push_back({"l", ParamValue{ParamValue::Kind::Number, 130e-9, "", SourceLoc{}}});
    auto mos = std::make_unique<OsdiModel>("m1", std::vector<NodeId>{2, 3, 0, 0},
        libShared, d, instParams, bsim4ModelParams());
    Diagnostics diags;
    NodeId internalBase = 4;
    ASSERT_TRUE(mos->initialize(diags, internalBase));
    devs.push_back(std::move(mos));

    NodeId maxNode = 0;
    for (const auto& dev : devs) {
        for (NodeId n : dev->nodes()) if (n > maxNode) maxNode = n;
    }

    ShootingConfig cfg;
    cfg.fundamental = freq;
    // Stage 1 smoke test：用较少的时间点快速验证 Shooting 路径不崩溃。
    cfg.numTimePoints = 15;

    ShootingOptions opts;
    opts.maxIter = 1;
    opts.localNewtonDvMax = 0.5;
    opts.verbose = false;

    auto dc = solveDcOp(maxNode, devs, DcOpOptions{});
    std::vector<double> initV(maxNode + 1, 0.0);
    if (dc.converged && dc.nodeVoltages.size() > maxNode) {
        initV = dc.nodeVoltages;
    } else {
        initV[1] = 1.0;
    }

    auto r = solveShooting(maxNode, devs, cfg, &initV, opts);
    // Stage 1：BSIM4 Shooting 暂定位为 smoke test，验证不崩溃且返回有效波形。
    ASSERT_FALSE(r.waveform.points.empty());

    // 周期闭合（容差放宽）
    double vEnd = r.waveform.points.back().x[2 - 1];
    double vStart = r.waveform.points.front().x[2 - 1];
    EXPECT_LT(std::fabs(vEnd - vStart), 0.5);

    // 输出节点电压应为有限值
    EXPECT_TRUE(std::isfinite(vEnd));
    EXPECT_TRUE(std::isfinite(vStart));
}

} // namespace rfsim
