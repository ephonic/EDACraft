// ac_analysis.cpp — 稀疏复数 AC 小信号分析实现
//
// 方案1: 稀疏复数 KLU (klu_z_*) 替代 dense complexSolve
// 方案3: pattern 固化——首次建 pattern+commit, 每频率点只更新 jωC 值
// 方案4: R 导纳预存 (staticValues), 跨频率不重算
#include "ac_analysis.hpp"
#include "../model/builtin_devices.hpp"
#include "../model/osdi_model.hpp"
#include "../model/sparam_device.hpp"
#include "../assembly/sparse_cmpl_matrix.hpp"
#include "../assembly/klu_z_solver.hpp"
#include <algorithm>
#include <cmath>
#include <cstdio>

namespace rfsim {

AcResult solveAc(uint32_t numNodes,
                 const std::vector<std::unique_ptr<DeviceModel>>& devices,
                 const AcSpec& spec,
                 const std::vector<double>& spec_freqs) {
    AcResult r;

    // 从 spec 生成频率列表（若调用方未显式传入）
    std::vector<double> freqs = spec_freqs;
    if (freqs.empty() && spec.startFreq > 0 && spec.stopFreq > 0) {
        if (spec.sweep == AcSpec::Sweep::Dec) {
            double f = spec.startFreq;
            double ratio = std::pow(10.0, 1.0 / spec.pointsPerDecade);
            while (f <= spec.stopFreq * 1.0001) {
                freqs.push_back(f);
                f *= ratio;
            }
        } else {
            int pts = spec.pointsPerDecade;
            for (int i = 0; i < pts; ++i)
                freqs.push_back(spec.startFreq + (spec.stopFreq - spec.startFreq) * i / (pts - 1));
        }
    }

    // H5: 检测非线性器件
    static bool warnedNonlinear = false;
    for (const auto& d : devices) {
        if (dynamic_cast<const OsdiModel*>(d.get())) {
            if (!warnedNonlinear) {
                std::fprintf(stderr,
                    "[AC] 警告: 电路含非线性器件 (%s)，AC 分析将跳过该器件。\n"
                    "      完整 AC 需先做 DC OP 线性化（待实现）。\n",
                    d->name().c_str());
                warnedNonlinear = true;
            }
        }
    }

    // 统计电压源
    std::vector<const VoltageSource*> vsList;
    for (const auto& d : devices) {
        if (auto* v = dynamic_cast<const VoltageSource*>(d.get()))
            vsList.push_back(v);
    }
    uint32_t numVS = static_cast<uint32_t>(vsList.size());
    uint32_t n = numNodes + numVS;

    // 方案1+3+4: 稀疏复数矩阵 + pattern固化 + R预存
    SparseCmplxMatrix G;
    G.resize(n);

    // 方案4: R 导纳 + VS pattern 预存到 staticValues（不随频率变）
    for (const auto& d : devices) {
        const auto& nds = d->nodes();
        uint32_t n1 = nds.size() > 0 ? nds[0] : 0;
        uint32_t n2 = nds.size() > 1 ? nds[1] : 0;
        if (auto* res = dynamic_cast<const Resistor*>(d.get())) {
            Complex y(1.0 / res->resistance(), 0);
            if (n1 != 0) G.addStatic(n1 - 1, n1 - 1, y);
            if (n2 != 0) G.addStatic(n2 - 1, n2 - 1, y);
            if (n1 != 0 && n2 != 0) {
                G.addStatic(n1 - 1, n2 - 1, -y);
                G.addStatic(n2 - 1, n1 - 1, -y);
            }
        }
    }
    // VS 分支 pattern（静态）
    for (uint32_t k = 0; k < numVS; ++k) {
        const auto* v = vsList[k];
        uint32_t br = numNodes + k;
        uint32_t n1 = v->nodes().size() > 0 ? v->nodes()[0] : 0;
        uint32_t n2 = v->nodes().size() > 1 ? v->nodes()[1] : 0;
        if (n1 != 0) { G.addStatic(n1 - 1, br, Complex(1, 0)); G.addStatic(br, n1 - 1, Complex(1, 0)); }
        if (n2 != 0) { G.addStatic(n2 - 1, br, Complex(-1, 0)); G.addStatic(br, n2 - 1, Complex(-1, 0)); }
        G.addStatic(br, br, Complex(0, 0));
    }

    // gmin 对角正则化——防止 RC ladder 高频时矩阵奇异（jωC 主导，R 被淹没）
    const double gmin = 1e-12;
    for (uint32_t i = 0; i < numNodes; ++i)
        G.addStatic(i, i, Complex(gmin, 0));

    bool firstFreq = true;
    KluZSolver solver;

    for (double f : freqs) {
        double omega = 6.283185307179586 * f;

        if (firstFreq) {
            // 首次：建 C/L pattern + 值 + finalize + commit
            for (const auto& d : devices) {
                const auto& nds = d->nodes();
                uint32_t n1 = nds.size() > 0 ? nds[0] : 0;
                uint32_t n2 = nds.size() > 1 ? nds[1] : 0;
                if (auto* cap = dynamic_cast<const Capacitor*>(d.get())) {
                    Complex y = cap->admittance(omega);
                    if (n1 != 0) G.add(n1 - 1, n1 - 1, y);
                    if (n2 != 0) G.add(n2 - 1, n2 - 1, y);
                    if (n1 != 0 && n2 != 0) { G.add(n1 - 1, n2 - 1, -y); G.add(n2 - 1, n1 - 1, -y); }
                } else if (auto* ind = dynamic_cast<const Inductor*>(d.get())) {
                    Complex y = ind->admittance(omega);
                    if (n1 != 0) G.add(n1 - 1, n1 - 1, y);
                    if (n2 != 0) G.add(n2 - 1, n2 - 1, y);
                    if (n1 != 0 && n2 != 0) { G.add(n1 - 1, n2 - 1, -y); G.add(n2 - 1, n1 - 1, -y); }
                } else if (auto* sp = dynamic_cast<const SParamDevice*>(d.get())) {
                    // S 参数器件：N×N Y 矩阵 stamp
                    auto Y = sp->admittanceMatrix(omega);
                    uint32_t N = sp->numPorts();
                    for (uint32_t i = 0; i < N; ++i) {
                        NodeId ni = nds[i];
                        if (ni == 0) continue;
                        for (uint32_t j = 0; j < N; ++j) {
                            NodeId nj = nds[j];
                            if (nj == 0) continue;
                            Complex yij = Y[i * N + j];
                            G.add(ni - 1, nj - 1, yij);
                        }
                    }
                }
            }
            G.finalize();
            G.commitPattern();
            firstFreq = false;
        } else {
            // 方案3: 复用 pattern——清动态值（保留 R），重新 stamp C/L
            G.zeroValues();
            for (const auto& d : devices) {
                const auto& nds = d->nodes();
                uint32_t n1 = nds.size() > 0 ? nds[0] : 0;
                uint32_t n2 = nds.size() > 1 ? nds[1] : 0;
                if (auto* cap = dynamic_cast<const Capacitor*>(d.get())) {
                    Complex y = cap->admittance(omega);
                    if (n1 != 0) G.addCommitted(n1 - 1, n1 - 1, y);
                    if (n2 != 0) G.addCommitted(n2 - 1, n2 - 1, y);
                    if (n1 != 0 && n2 != 0) { G.addCommitted(n1 - 1, n2 - 1, -y); G.addCommitted(n2 - 1, n1 - 1, -y); }
                } else if (auto* ind = dynamic_cast<const Inductor*>(d.get())) {
                    Complex y = ind->admittance(omega);
                    if (n1 != 0) G.addCommitted(n1 - 1, n1 - 1, y);
                    if (n2 != 0) G.addCommitted(n2 - 1, n2 - 1, y);
                    if (n1 != 0 && n2 != 0) { G.addCommitted(n1 - 1, n2 - 1, -y); G.addCommitted(n2 - 1, n1 - 1, -y); }
                } else if (auto* sp = dynamic_cast<const SParamDevice*>(d.get())) {
                    // S 参数器件：N×N Y 矩阵 stamp（committed 路径）
                    auto Y = sp->admittanceMatrix(omega);
                    uint32_t N = sp->numPorts();
                    for (uint32_t i = 0; i < N; ++i) {
                        NodeId ni = nds[i];
                        if (ni == 0) continue;
                        for (uint32_t j = 0; j < N; ++j) {
                            NodeId nj = nds[j];
                            if (nj == 0) continue;
                            Complex yij = Y[i * N + j];
                            G.addCommitted(ni - 1, nj - 1, yij);
                        }
                    }
                }
            }
        }

        // RHS: VS 电压 + CS 注入
        std::vector<double> B(2 * n, 0.0);
        for (uint32_t k = 0; k < numVS; ++k) {
            const auto* v = vsList[k];
            uint32_t br = numNodes + k;
            Complex vac = v->acMag();
            if (vac == Complex(0, 0)) vac = Complex(v->voltage(), 0);
            B[2 * br] = vac.real();
            B[2 * br + 1] = vac.imag();
        }
        for (const auto& d : devices) {
            if (auto* cs = dynamic_cast<const CurrentSource*>(d.get())) {
                const auto& nds = d->nodes();
                uint32_t n1 = nds.size() > 0 ? nds[0] : 0;
                uint32_t n2 = nds.size() > 1 ? nds[1] : 0;
                double I = cs->current();
                if (n1 != 0) B[2 * (n1 - 1)] += I;
                if (n2 != 0) B[2 * (n2 - 1)] -= I;
            }
        }

        // KLU 求解
        if (!solver.factorize(static_cast<int>(n), G.rowPtr(), G.colIdx(), G.values())) {
            r.diags.error({}, "AC: KLU factorize failed at f=" + std::to_string(f));
            continue;
        }

        solver.solve(B.data());

        // 提取节点电压（NodeId 索引：0=地=0V, 1..numNodes）
        AcPoint pt;
        pt.freq = f;
        pt.nodeVoltages.resize(numNodes + 1);  // 含地节点 [0]
        pt.nodeVoltages[0] = Complex(0, 0);  // 地
        for (uint32_t i = 1; i <= numNodes; ++i) {
            pt.nodeVoltages[i] = Complex(B[2 * (i - 1)], B[2 * (i - 1) + 1]);
        }
        r.points.push_back(std::move(pt));
    }

    r.ok = !r.points.empty() && !r.diags.has_errors();
    return r;
}

} // namespace rfsim
