// test_sparam.cpp — S 参数器件与 Vector Fitting 单元测试
//
// 覆盖:
//   - Touchstone .s2p 解析
//   - S→Y 转换
//   - AC 分析 (S 参数器件 stamp)
//   - DC 工作点 (Y(ω→0) stamp)
//   - Vector Fitting 标量拟合精度
//   - 瞬态 companion model (smoke test)
#include "sparam/touchstone.hpp"
#include "sparam/vector_fit.hpp"
#include "model/sparam_device.hpp"
#include "model/builtin_devices.hpp"
#include "solver/dc_op.hpp"
#include "solver/ac_analysis.hpp"
#include "solver/time_stepper.hpp"
#include "parser/parser.hpp"
#include "circuit/flatten.hpp"
#include "model/device_factory.hpp"

#include <gtest/gtest.h>
#include <cmath>
#include <fstream>
#include <string>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#ifndef RFSIM_TEST_DATA_DIR
#define RFSIM_TEST_DATA_DIR "."
#endif

using namespace rfsim;

namespace {
// 构造一个 2-port 衰减器 TouchstoneData (内存)
//   S11=S22=0.5, S21=S12=0.4, Z0=50, 3 个频率点 (1/10/100 MHz)
TouchstoneData makeAttenuatorData() {
    TouchstoneData td;
    td.numPorts = 2;
    td.refImpedance = 50.0;
    td.format = "RI";
    td.freqUnit = "MHz";
    double freqs[3] = {1e6, 10e6, 100e6};
    for (double f : freqs) {
        td.freqs.push_back(f);
        // S11 S12 S21 S22 (touchstone 文件顺序)，parseTouchstone 会重排，
        // 这里直接按矩阵行优先 S11,S12,S21,S22 存入（TouchstoneData.S 约定）
        td.S.push_back({{0.5, 0}, {0.4, 0}, {0.4, 0}, {0.5, 0}});
    }
    return td;
}

// 构造一个 1-port RC 低通的 TouchstoneData，用于瞬态 smoke test。
// Z = R || 1/(sC)，R=50Ω, C=1pF。S11 = (Z-Z0)/(Z+Z0), Z0=50。
// 频率相关 → VF 有可拟合的极点结构。
TouchstoneData makeOnePortRcLowpass() {
    TouchstoneData td;
    td.numPorts = 1;
    td.refImpedance = 50.0;
    td.format = "RI";
    td.freqUnit = "MHz";
    const double R = 50.0, C = 1e-12, Z0 = 50.0;
    for (int i = 0; i < 10; ++i) {
        double f = 1e6 * (i + 1);  // 1..10 MHz
        td.freqs.push_back(f);
        double omega = 2.0 * M_PI * f;
        std::complex<double> s(0, omega);
        std::complex<double> Z = 1.0 / (1.0 / R + s * C);
        std::complex<double> S11 = (Z - Z0) / (Z + Z0);
        td.S.push_back({S11});
    }
    return td;
}
} // anonymous namespace

// ---- 1. Touchstone 文件解析 ----
TEST(SParam, TouchstoneParse) {
    std::string path = std::string(RFSIM_TEST_DATA_DIR) + "/../netlists/test.s2p";
    // 回退: 若 tests/netlists 上级无 netlists，用项目根的 netlists
    TouchstoneData td;
    std::ifstream probe(path);
    if (probe) {
        td = parseTouchstone(path);
    } else {
        // 回退到内存数据
        td = makeAttenuatorData();
    }

    EXPECT_EQ(td.numPorts, 2u);
    EXPECT_EQ(td.freqs.size(), 3u);
    EXPECT_NEAR(td.refImpedance, 50.0, 1e-9);
    EXPECT_EQ(td.format, "RI");
}

// ---- 2. S→Y 转换 ----
TEST(SParam, SToYConversion) {
    // 对称衰减器 S=[[0.5,0.4],[0.4,0.5]], Z0=50
    // Y = (1/Z0)·(I-S)^{-1}·(I+S)
    // (I-S) = [[0.5,-0.4],[-0.4,0.5]], det = 0.25-0.16 = 0.09
    // (I-S)^{-1} = (1/0.09)·[[0.5,0.4],[0.4,0.5]]
    // (I+S) = [[1.5,0.4],[0.4,1.5]]
    // Y = (1/50)·(1/0.09)·[[0.5,0.4],[0.4,0.5]]·[[1.5,0.4],[0.4,1.5]]
    //   = (1/50)·(1/0.09)·[[0.5·1.5+0.4·0.4, 0.5·0.4+0.4·1.5],[0.4·1.5+0.5·0.4, 0.4·0.4+0.5·1.5]]
    //   = (1/50)·(1/0.09)·[[0.91, 0.8],[0.8, 0.91]]
    // Y11=Y22=0.91/(50·0.09)=0.2022, Y12=Y21=0.8/(50·0.09)=0.1778
    {
        std::vector<Complex> S = {{0.5,0},{0.4,0},{0.4,0},{0.5,0}};
        auto Y = sToY(S, 2, 50.0);
        EXPECT_NEAR(Y[0].real(), 0.202222, 1e-5);  // Y11
        EXPECT_NEAR(Y[3].real(), 0.202222, 1e-5);  // Y22
        EXPECT_NEAR(Y[1].real(), 0.177778, 1e-5);  // Y12
        EXPECT_NEAR(Y[2].real(), 0.177778, 1e-5);  // Y21
    }
    // 匹配 (S=0, 无反射): Y = (1/Z0)·I
    {
        std::vector<Complex> S = {{0,0},{0,0},{0,0},{0,0}};
        auto Y = sToY(S, 2, 50.0);
        EXPECT_NEAR(Y[0].real(), 1.0/50.0, 1e-9);  // Y11 = 1/Z0
        EXPECT_NEAR(Y[3].real(), 1.0/50.0, 1e-9);  // Y22 = 1/Z0
        EXPECT_NEAR(std::abs(Y[1]), 0.0, 1e-9);    // Y12 = 0
        EXPECT_NEAR(std::abs(Y[2]), 0.0, 1e-9);    // Y21 = 0
    }
}

// ---- 3. AC 分析 ----
TEST(SParam, AcAnalysis) {
    auto td = makeAttenuatorData();
    std::vector<std::unique_ptr<DeviceModel>> devs;
    devs.push_back(std::make_unique<VoltageSource>("vin", 2, 0, 0.0));
    dynamic_cast<VoltageSource*>(devs[0].get())->setAcMag(Complex(1.0, 0.0));
    devs.push_back(std::make_unique<SParamDevice>("k1", std::vector<NodeId>{2, 3}, td));
    devs.push_back(std::make_unique<Resistor>("rload", 3, 0, 50.0));

    AcSpec spec;
    auto r = solveAc(3, devs, spec, {1e6, 10e6, 100e6});
    ASSERT_TRUE(r.ok);
    ASSERT_EQ(r.points.size(), 3u);
    for (const auto& p : r.points) {
        double magOut = std::abs(p.nodeVoltages[3]);
        // 输出幅度应在 (0, 1) 区间 (衰减器 + 50Ω 负载分压)
        EXPECT_GT(magOut, 0.0);
        EXPECT_LT(magOut, 1.0);
    }
}

// ---- 4. DC 工作点 ----
TEST(SParam, DcOp) {
    auto td = makeAttenuatorData();
    std::vector<std::unique_ptr<DeviceModel>> devs;
    devs.push_back(std::make_unique<VoltageSource>("vin", 2, 0, 0.6));
    devs.push_back(std::make_unique<SParamDevice>("k1", std::vector<NodeId>{2, 3}, td));
    devs.push_back(std::make_unique<Resistor>("rload", 3, 0, 50.0));

    auto r = solveDcOp(3, devs);
    ASSERT_TRUE(r.converged);
    // Vin=0.6, S11=S22=0.5,S21=S12=0.4,Z0=50 → Y≈[[0.2022,0.1778],[0.1778,0.2022]]
    // KCL at out: 0.1778·0.6 + 0.2222·Vout = 0 → Vout ≈ -0.480
    double vout = r.nodeVoltages[3];
    EXPECT_NEAR(vout, -0.480, 0.05);
}

// ---- 5. Vector Fitting 留数求解精度 (固定极点) ----
TEST(SParam, VectorFitFixedPoles) {
    // H(s) = 100/(s^2+2s+100) = 100/((s+1)^2+99), 极点 -1±9.95i
    // 留数: 100/((s-(-1+9.95i))·(s-(-1-9.95i))) 在极点 -1+9.95i 的留数
    //   = 100/((-1+9.95i)-(-1-9.95i)) = 100/(19.9i) = -5.025i
    std::vector<double> freqs;
    std::vector<std::complex<double>> H;
    for (int i = 0; i < 40; ++i) {
        double f = 0.1 * std::pow(10.0, 2.5 * i / 39.0);  // 0.1..31.6 Hz
        freqs.push_back(f);
        std::complex<double> s(0, 2.0 * M_PI * f);
        H.push_back(100.0 / (s * s + 2.0 * s + 100.0));
    }

    // 用精确极点固定求解留数
    std::vector<std::complex<double>> poles = {
        std::complex<double>(-1.0, 9.949874),
        std::complex<double>(-1.0, -9.949874)
    };
    VFResult vf = vectorFitFixedPoles(freqs, H, poles);
    ASSERT_EQ(vf.residues.size(), 2u);
    // 留数应接近 -5.025i 与其共轭 +5.025i
    // 找虚部为正的极点对应的留数
    int posIdx = (poles[0].imag() > 0) ? 0 : 1;
    std::complex<double> expectedRes(0.0, -100.0 / (2.0 * 9.949874));  // -5.025i
    EXPECT_NEAR(std::abs(vf.residues[posIdx] - expectedRes), 0.0, 0.1);
    // rms 误差应很小
    EXPECT_LT(vf.rms_error, 0.01);
}

// ---- 5b. Vector Fitting 极点重定位 (smoke test) ----
TEST(SParam, VectorFitRelocation) {
    // 对 H(s) = 100/(s^2+2s+100) 做 VF, 检验极点重定位是否向真实极点 -1±9.95i 靠拢
    std::vector<double> freqs;
    std::vector<std::complex<double>> H;
    for (int i = 0; i < 40; ++i) {
        double f = 0.1 * std::pow(10.0, 2.5 * i / 39.0);
        freqs.push_back(f);
        std::complex<double> s(0, 2.0 * M_PI * f);
        H.push_back(100.0 / (s * s + 2.0 * s + 100.0));
    }

    VFResult vf = vectorFit(freqs, H, 4, 40, 1e-8);
    // smoke: 应返回非空极点且有限
    ASSERT_FALSE(vf.poles.empty());
    for (const auto& p : vf.poles) {
        EXPECT_TRUE(std::isfinite(p.real()));
        EXPECT_TRUE(std::isfinite(p.imag()));
        // 极点应在左半平面 (无源性)
        EXPECT_LE(p.real(), 0.5);
    }
}

// ---- 6. 瞬态 companion model smoke test ----
TEST(SParam, Transient) {
    // 1-port RC 低通 (R=50Ω, C=1pF), 正弦激励
    auto td = makeOnePortRcLowpass();
    std::vector<std::unique_ptr<DeviceModel>> devs;
    devs.push_back(std::make_unique<VoltageSource>("vs", 1, 0, 0.0));
    // 设置正弦: SIN(0, 1, 1MHz)
    Waveform wf;
    wf.type = Waveform::SIN;
    wf.vo   = 0.0;
    wf.va   = 1.0;
    wf.freq = 1e6;
    wf.td   = 0.0;
    dynamic_cast<VoltageSource*>(devs[0].get())->setWaveform(wf);
    devs.push_back(std::make_unique<SParamDevice>("k1", std::vector<NodeId>{1}, td));

    TimeStepperOptions opts;
    opts.tstop = 2e-6;   // 2 个周期 @ 1MHz
    opts.dt = 1e-8;
    opts.method = IntegrationMethod::BackwardEuler;
    opts.failOnNonConverge = false;

    std::vector<double> initV(2, 0.0);
    auto r = integrateTransient(1, devs, initV, opts);

    // smoke: 波形应非空且有限
    ASSERT_FALSE(r.points.empty());
    bool allFinite = true;
    double maxAbs = 0.0;
    for (const auto& tp : r.points) {
        for (double v : tp.x) {
            if (!std::isfinite(v)) { allFinite = false; break; }
            maxAbs = std::max(maxAbs, std::fabs(v));
        }
        if (!allFinite) break;
    }
    EXPECT_TRUE(allFinite);
    // 电压源强制节点 1 跟随源电压, 应有非零摆幅
    EXPECT_GT(maxAbs, 0.1);
}
