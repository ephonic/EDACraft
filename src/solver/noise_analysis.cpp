// noise_analysis.cpp — 线性电路噪声分析实现
//
// 详见 noise_analysis.hpp。电阻热噪声经 AC 传输到输出节点。
// 使用 KluZSolver 复数求解（与 AC 分析同款 SparseCmplxMatrix + KluZSolver）。
#include "noise_analysis.hpp"
#include "../assembly/sparse_cmpl_matrix.hpp"

#ifdef RFSIM_USE_KLU
#include "../assembly/klu_z_solver.hpp"
#endif

#include <cmath>
#include <iomanip>
#include <iostream>

namespace rfsim {

namespace {
constexpr double k_B = 1.380649e-23;

// 电阻列表（含节点 + 阻值），用于噪声源
struct ResistorNoise {
    uint32_t n1, n2;  // 节点（0=gnd）
    double g;          // 电导 1/R
};
} // namespace

NoiseResult solveNoise(uint32_t numNodes,
                       const std::vector<std::unique_ptr<DeviceModel>>& devices,
                       const NoiseSpec& spec,
                       double temperature) {
    NoiseResult r;
    r.outputNodeId = spec.outputNodeId;
    if (spec.outputNodeId == 0 || spec.outputNodeId > numNodes) {
        r.diags.error({}, "noise: invalid output node id");
        return r;
    }
    const uint32_t outIdx = spec.outputNodeId - 1;  // 0-based

    // 收集电阻（噪声源）
    std::vector<ResistorNoise> rlist;
    for (const auto& d : devices) {
        if (auto* res = dynamic_cast<const Resistor*>(d.get())) {
            const auto& nds = d->nodes();
            rlist.push_back({nds.size() > 0 ? nds[0] : 0,
                             nds.size() > 1 ? nds[1] : 0,
                             res->conductance()});
        }
    }

    // 收集电压源（分支扩展）
    uint32_t numVS = 0;
    for (const auto& d : devices)
        if (dynamic_cast<const VoltageSource*>(d.get())) ++numVS;
    uint32_t n = numNodes + numVS;
    if (n == 0) { r.diags.error({}, "noise: empty circuit"); return r; }

    // 频率列表（DEC 扫描）
    std::vector<double> freqs;
    if (spec.startFreq > 0 && spec.stopFreq > 0 && spec.pointsPerDecade > 0) {
        double f = spec.startFreq;
        double ratio = std::pow(10.0, 1.0 / spec.pointsPerDecade);
        while (f <= spec.stopFreq * 1.0001) { freqs.push_back(f); f *= ratio; }
    }
    if (freqs.empty()) { r.diags.error({}, "noise: invalid frequency range"); return r; }

    const double kT = k_B * temperature;

    bool firstFreq = true;
    for (double f : freqs) {
        double omega = 6.283185307176586 * f;

        // 建 Y(jω)
        SparseCmplxMatrix G;
        G.resize(n);
        for (const auto& d : devices) {
            const auto& nds = d->nodes();
            uint32_t n1 = nds.size() > 0 ? nds[0] : 0;
            uint32_t n2 = nds.size() > 1 ? nds[1] : 0;
            if (auto* res = dynamic_cast<const Resistor*>(d.get())) {
                Complex y(res->conductance(), 0);
                if (n1 != 0) G.add(n1-1, n1-1, y);
                if (n2 != 0) G.add(n2-1, n2-1, y);
                if (n1 != 0 && n2 != 0) { G.add(n1-1, n2-1, -y); G.add(n2-1, n1-1, -y); }
            } else if (auto* cap = dynamic_cast<const Capacitor*>(d.get())) {
                Complex y = cap->admittance(omega);
                if (n1 != 0) G.add(n1-1, n1-1, y);
                if (n2 != 0) G.add(n2-1, n2-1, y);
                if (n1 != 0 && n2 != 0) { G.add(n1-1, n2-1, -y); G.add(n2-1, n1-1, -y); }
            } else if (auto* ind = dynamic_cast<const Inductor*>(d.get())) {
                Complex y = ind->admittance(omega);
                if (n1 != 0) G.add(n1-1, n1-1, y);
                if (n2 != 0) G.add(n2-1, n2-1, y);
                if (n1 != 0 && n2 != 0) { G.add(n1-1, n2-1, -y); G.add(n2-1, n1-1, -y); }
            }
        }
        // VS 分支
        uint32_t vsIdx = 0;
        for (const auto& d : devices) {
            if (auto* v = dynamic_cast<const VoltageSource*>(d.get())) {
                const auto& nds = d->nodes();
                uint32_t br = numNodes + vsIdx++;
                uint32_t n1 = nds.size() > 0 ? nds[0] : 0;
                uint32_t n2 = nds.size() > 1 ? nds[1] : 0;
                if (n1 != 0) { G.add(n1-1, br, Complex(1,0)); G.add(br, n1-1, Complex(1,0)); }
                if (n2 != 0) { G.add(n2-1, br, Complex(-1,0)); G.add(br, n2-1, Complex(-1,0)); }
                G.add(br, br, Complex(0,0));
            }
        }
        // gmin 正则化
        for (uint32_t i = 0; i < numNodes; ++i) G.add(i, i, Complex(1e-12, 0));
        G.finalize();

        // KLU 复数求解
#ifdef RFSIM_USE_KLU
        KluZSolver solver;
        solver.factorize(static_cast<int>(n), G.rowPtr(), G.colIdx(), G.values());

        double outPSD = 0.0;
        // 对每个电阻噪声源：注入电流到其节点对，求 V_out
        for (const auto& rn : rlist) {
            double psd_src = 4.0 * kT * rn.g;  // 电流噪声 PSD (A²/Hz)
            // 构造 RHS：在 n1 注入 +1A，n2 注入 -1A（噪声电流源方向）
            std::vector<double> B(2 * n, 0.0);  // interleaved Re,Im
            if (rn.n1 != 0 && rn.n1 <= numNodes) B[2 * (rn.n1 - 1)] = 1.0;
            if (rn.n2 != 0 && rn.n2 <= numNodes) B[2 * (rn.n2 - 1)] = -1.0;
            solver.solve(B.data());  // in-place
            // V_out = B[2*outIdx] + j·B[2*outIdx+1]
            Complex vout(B[2 * outIdx], B[2 * outIdx + 1]);
            outPSD += std::norm(vout) * psd_src;
        }

        NoisePoint pt;
        pt.freq = f;
        pt.outputNoisePSD = outPSD;
        pt.outputNoiseDbV = (outPSD > 0) ? 10.0 * std::log10(std::sqrt(outPSD)) : -999.0;
        pt.inputReferencedPSD = 0.0;
        r.points.push_back(pt);
#else
        // 无 KLU：无法求解复数系统，返回零
        NoisePoint pt;
        pt.freq = f;
        pt.outputNoisePSD = 0.0;
        pt.outputNoiseDbV = -999.0;
        pt.inputReferencedPSD = 0.0;
        r.points.push_back(pt);
#endif
        (void)firstFreq;
    }

    // 积分噪声 RMS（梯形积分，对频率）
    double integPSD = 0.0;
    for (size_t i = 1; i < r.points.size(); ++i) {
        double df = r.points[i].freq - r.points[i-1].freq;
        integPSD += 0.5 * (r.points[i].outputNoisePSD + r.points[i-1].outputNoisePSD) * df;
    }
    r.integratedNoiseV = std::sqrt(integPSD);
    r.ok = true;
    return r;
}

void writeNoiseResult(std::ostream& os, const NoiseResult& r) {
    if (!r.ok) { os << "noise analysis failed\n"; return; }
    os << "\n=== Noise Analysis (linear, R thermal) ===\n";
    os << "  output node: " << r.outputNodeId << "\n";
    os << "  freq(Hz)       noise(PSD V²/Hz)   noise(dBV/√Hz)\n";
    os.setf(std::ios::scientific);
    for (const auto& p : r.points) {
        os << "  " << std::setprecision(4) << std::setw(12) << p.freq
           << "  " << std::setw(16) << p.outputNoisePSD
           << "  " << std::setw(12) << p.outputNoiseDbV << "\n";
    }
    os.unsetf(std::ios::scientific);
    os << "\n  integrated output noise: " << r.integratedNoiseV * 1e6 << " µV RMS\n";
}

} // namespace rfsim
