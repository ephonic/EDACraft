// hb_jacobian.cpp - Harmonic Balance 实数化频域雅可比与残差装配实现
#include "hb_jacobian.hpp"
#include "../model/builtin_devices.hpp"
#include "../model/osdi_model.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>

namespace rfsim {

namespace {

const double PI = 3.14159265358979323846;

// 时域实采样 -> 谐波复系数（无 2 倍补偿，用于电导卷积）
// G[k] = (1/N) sum_n g[n] e^{-j k w n}, k=0..NH
std::vector<Complex> conductanceFft(const std::vector<double>& t, uint32_t NH) {
    uint32_t N = static_cast<uint32_t>(t.size());
    std::vector<Complex> h(NH + 1, Complex(0, 0));
    for (uint32_t k = 0; k <= NH; ++k) {
        Complex sum(0, 0);
        for (uint32_t n = 0; n < N; ++n) {
            double ph = 2.0 * PI * k * n / N;
            sum += t[n] * Complex(std::cos(ph), -std::sin(ph));
        }
        h[k] = sum / static_cast<double>(N);
    }
    return h;
}

// IFFT：谐波复电压 -> 时域实采样（2*(NH+1) 点）
std::vector<double> ifftWaveform(const std::vector<Complex>& harmonics, uint32_t NH) {
    uint32_t N = 2 * (NH + 1);
    std::vector<double> t(N, 0.0);
    for (uint32_t n = 0; n < N; ++n) {
        double sum = 0;
        for (uint32_t k = 0; k <= NH && k < harmonics.size(); ++k) {
            double ph = 2.0 * PI * k * n / N;
            sum += harmonics[k].real() * std::cos(ph) - harmonics[k].imag() * std::sin(ph);
        }
        t[n] = sum;
    }
    return t;
}

// FFT：时域实采样 -> 谐波复系数（含 2 倍补偿，用于电流/残差）
std::vector<Complex> currentFft(const std::vector<double>& t, uint32_t NH) {
    uint32_t N = static_cast<uint32_t>(t.size());
    std::vector<Complex> h(NH + 1, Complex(0, 0));
    for (uint32_t k = 0; k <= NH; ++k) {
        Complex sum(0, 0);
        for (uint32_t n = 0; n < N; ++n) {
            double ph = 2.0 * PI * k * n / N;
            sum += t[n] * Complex(std::cos(ph), -std::sin(ph));
        }
        h[k] = sum / static_cast<double>(N);
        if (k > 0) h[k] *= 2.0;
    }
    return h;
}

// 实数化索引（0-based，不含地）：0..numNodes-1=节点，numNodes..=分支
inline uint32_t nodeEntity(uint32_t nodeId) {
    return nodeId - 1;  // nodeId>=1
}
inline uint32_t branchEntity(uint32_t numNodes, uint32_t branchIdx) {
    return numNodes + branchIdx;
}

inline uint32_t compCount(uint32_t NH) { return 1 + 2 * NH; }

inline uint32_t compHarmonic(uint32_t c) {
    if (c == 0) return 0;
    return (c + 1) / 2;
}
inline bool compIsReal(uint32_t c) {
    return c == 0 || (c % 2 == 1);
}

// 复数贡献 val 加到实数 Jacobian 的 (rowEntity, rowHar, colEntity, colHar) 块
void addComplexBlock(std::vector<double>& J, uint32_t dim, uint32_t perEntity,
                     uint32_t rowEntity, uint32_t rowHar,
                     uint32_t colEntity, uint32_t colHar,
                     Complex val) {
    uint32_t rb = rowEntity * perEntity;
    uint32_t cb = colEntity * perEntity;
    auto idx = [dim](uint32_t r, uint32_t c) { return size_t(r) * dim + c; };
    if (rowHar == 0 && colHar == 0) {
        J[idx(rb, cb)] += val.real();
    } else if (rowHar == 0 && colHar >= 1) {
        uint32_t c_re = cb + 2 * colHar - 1;
        uint32_t c_im = cb + 2 * colHar;
        J[idx(rb, c_re)] += val.real();
        J[idx(rb, c_im)] += -val.imag();
    } else if (rowHar >= 1 && colHar == 0) {
        uint32_t r_re = rb + 2 * rowHar - 1;
        uint32_t r_im = rb + 2 * rowHar;
        J[idx(r_re, cb)] += val.real();
        J[idx(r_im, cb)] += val.imag();
    } else {
        uint32_t r_re = rb + 2 * rowHar - 1;
        uint32_t r_im = rb + 2 * rowHar;
        uint32_t c_re = cb + 2 * colHar - 1;
        uint32_t c_im = cb + 2 * colHar;
        J[idx(r_re, c_re)] += val.real();
        J[idx(r_re, c_im)] += -val.imag();
        J[idx(r_im, c_re)] += val.imag();
        J[idx(r_im, c_im)] += val.real();
    }
}

// 复数残差 val 加到实数残差的 (entity, har) 位置
void addComplexResidual(std::vector<double>& F, uint32_t perEntity,
                        uint32_t entity, uint32_t har, Complex val) {
    uint32_t base = entity * perEntity;
    if (har == 0) {
        F[base] += val.real();
    } else {
        F[base + 2 * har - 1] += val.real();
        F[base + 2 * har]     += val.imag();
    }
}

// 将电导 g(t) 的 FFT 系数 G[0..NH] 转实数 Jacobian 块，按符号 sign 加到全局矩阵
// sign = -1 用于非线性器件（F = -I）；sign = +1 用于线性器件（F = +Y V）
void addConductanceBlock(std::vector<double>& J, uint32_t dim, uint32_t perEntity,
                         uint32_t rowEntity, uint32_t colEntity,
                         const std::vector<Complex>& G, uint32_t NH, double sign);

// 将电荷 Jacobian g_Q(t) 的 FFT 系数转电纳块：Y_Q[l] = j l w0 G_Q[l]，再加到全局矩阵
void addSusceptanceBlock(std::vector<double>& J, uint32_t dim, uint32_t perEntity,
                         uint32_t rowEntity, uint32_t colEntity,
                         const std::vector<Complex>& G, uint32_t NH, double w0, double sign) {
    std::vector<Complex> Y(NH + 1, Complex(0, 0));
    for (uint32_t l = 0; l <= NH; ++l) {
        // j * l * w0 * G
        Y[l] = Complex(-l * w0 * G[l].imag(), l * w0 * G[l].real());
    }
    addConductanceBlock(J, dim, perEntity, rowEntity, colEntity, Y, NH, sign);
}

void addConductanceBlock(std::vector<double>& J, uint32_t dim, uint32_t perEntity,
                         uint32_t rowEntity, uint32_t colEntity,
                         const std::vector<Complex>& G, uint32_t NH, double sign) {
    auto Gval = [&G, NH](int32_t l) -> Complex {
        if (l < 0) {
            int32_t p = -l;
            if (p > static_cast<int32_t>(NH)) return Complex(0, 0);
            return std::conj(G[p]);
        }
        if (l > static_cast<int32_t>(NH)) return Complex(0, 0);
        return G[l];
    };
    auto addBlock = [&](uint32_t k, uint32_t m, double a00,
                        double a01, double a10, double a11) {
        uint32_t rb = rowEntity * perEntity;
        uint32_t cb = colEntity * perEntity;
        auto idx = [dim](uint32_t r, uint32_t c) { return size_t(r) * dim + c; };
        if (k == 0 && m == 0) {
            J[idx(rb, cb)] += sign * a00;
        } else if (k == 0 && m >= 1) {
            uint32_t c_re = cb + 2 * m - 1;
            uint32_t c_im = cb + 2 * m;
            J[idx(rb, c_re)] += sign * a00;
            J[idx(rb, c_im)] += sign * a01;
        } else if (k >= 1 && m == 0) {
            uint32_t r_re = rb + 2 * k - 1;
            uint32_t r_im = rb + 2 * k;
            J[idx(r_re, cb)] += sign * a00;
            J[idx(r_im, cb)] += sign * a10;
        } else {
            uint32_t r_re = rb + 2 * k - 1;
            uint32_t r_im = rb + 2 * k;
            uint32_t c_re = cb + 2 * m - 1;
            uint32_t c_im = cb + 2 * m;
            J[idx(r_re, c_re)] += sign * a00;
            J[idx(r_re, c_im)] += sign * a01;
            J[idx(r_im, c_re)] += sign * a10;
            J[idx(r_im, c_im)] += sign * a11;
        }
    };

    for (uint32_t k = 0; k <= NH; ++k) {
        for (uint32_t m = 0; m <= NH; ++m) {
            Complex gp = Gval(static_cast<int32_t>(k) - static_cast<int32_t>(m));
            Complex gm = (k + m <= NH) ? G[k + m] : Complex(0, 0);
            if (k == 0 && m == 0) {
                addBlock(0, 0, gp.real(), 0, 0, 0);
            } else if (k == 0 && m >= 1) {
                // M3: 补 2× 因子——与 (k≥1, m=0) 对称
                Complex g = G[m];
                addBlock(0, m, 2.0 * g.real(), 2.0 * g.imag(), 0, 0);
            } else if (k >= 1 && m == 0) {
                // [[2 Re(G[k])]; [2 Im(G[k])]]
                addBlock(k, 0, 2.0 * gp.real(), 0, 2.0 * gp.imag(), 0);
            } else {
                // 2x2
                double a00 = gp.real() + gm.real();
                double a01 = -gp.imag() + gm.imag();
                double a10 = gp.imag() + gm.imag();
                double a11 = gp.real() - gm.real();
                addBlock(k, m, a00, a01, a10, a11);
            }
        }
    }
}

} // namespace

bool assembleHarmonicBalanceReal(
    uint32_t numNodes,
    const std::vector<std::unique_ptr<DeviceModel>>& devices,
    const HbConfig& config,
    const std::vector<std::vector<Complex>>& X,
    HbRealSystem& sys,
    Diagnostics& diags,
    double sourceScale,
    double gmin) {
    (void)diags;
    uint32_t NH = config.numHarmonics;
    uint32_t perEntity = compCount(NH);

    // 收集电压源并建立映射
    std::vector<const VoltageSource*> vsList;
    std::vector<uint32_t> vsDeviceIdx; // devices 中对应索引
    for (uint32_t di = 0; di < devices.size(); ++di) {
        if (auto* v = dynamic_cast<VoltageSource*>(devices[di].get())) {
            vsList.push_back(v);
            vsDeviceIdx.push_back(di);
        }
    }
    uint32_t numVS = static_cast<uint32_t>(vsList.size());
    uint32_t nEntities = numNodes + numVS;
    uint32_t dim = nEntities * perEntity;

    sys.numNodes = numNodes;
    sys.numVS = numVS;
    sys.nEntities = nEntities;
    sys.NH = NH;
    sys.perEntity = perEntity;
    sys.dim = dim;
    sys.F.assign(dim, 0.0);
    sys.J.assign(size_t(dim) * dim, 0.0);

    const uint32_t N = 2 * (NH + 1);
    const double w0 = 2.0 * PI * config.fundamental;

    // IFFT：节点电压 -> 时域波形（包含地）
    std::vector<std::vector<double>> timeV(numNodes + 1);
    for (uint32_t i = 1; i <= numNodes; ++i) {
        timeV[i] = ifftWaveform(X[i], NH);
    }
    timeV[0].assign(N, 0.0);

    // ---- 线性器件 stamp ----
    for (const auto& d : devices) {
        const auto& nds = d->nodes();
        uint32_t n1 = nds.size() > 0 ? nds[0] : 0;
        uint32_t n2 = nds.size() > 1 ? nds[1] : 0;
        uint32_t e1 = nodeEntity(n1);
        uint32_t e2 = nodeEntity(n2);

        if (auto* res = dynamic_cast<Resistor*>(d.get())) {
            double g = res->conductance();
            for (uint32_t k = 0; k <= NH; ++k) {
                Complex y(g, 0);
                Complex v1 = (n1 != 0 && n1 <= numNodes) ? X[n1][k] : Complex(0, 0);
                Complex v2 = (n2 != 0 && n2 <= numNodes) ? X[n2][k] : Complex(0, 0);
                Complex i = y * (v1 - v2);
                if (n1 != 0) addComplexResidual(sys.F, perEntity, e1, k, +i);
                if (n2 != 0) addComplexResidual(sys.F, perEntity, e2, k, -i);
                if (n1 != 0) addComplexBlock(sys.J, dim, perEntity, e1, k, e1, k, +y);
                if (n2 != 0) addComplexBlock(sys.J, dim, perEntity, e2, k, e2, k, +y);
                if (n1 != 0 && n2 != 0) {
                    addComplexBlock(sys.J, dim, perEntity, e1, k, e2, k, -y);
                    addComplexBlock(sys.J, dim, perEntity, e2, k, e1, k, -y);
                }
            }
        } else if (auto* cap = dynamic_cast<Capacitor*>(d.get())) {
            for (uint32_t k = 0; k <= NH; ++k) {
                Complex y = (k == 0) ? Complex(1e-12, 0) : Complex(0, w0 * k * cap->capacitance());
                Complex v1 = (n1 != 0 && n1 <= numNodes) ? X[n1][k] : Complex(0, 0);
                Complex v2 = (n2 != 0 && n2 <= numNodes) ? X[n2][k] : Complex(0, 0);
                Complex i = y * (v1 - v2);
                if (n1 != 0) addComplexResidual(sys.F, perEntity, e1, k, +i);
                if (n2 != 0) addComplexResidual(sys.F, perEntity, e2, k, -i);
                if (n1 != 0) addComplexBlock(sys.J, dim, perEntity, e1, k, e1, k, +y);
                if (n2 != 0) addComplexBlock(sys.J, dim, perEntity, e2, k, e2, k, +y);
                if (n1 != 0 && n2 != 0) {
                    addComplexBlock(sys.J, dim, perEntity, e1, k, e2, k, -y);
                    addComplexBlock(sys.J, dim, perEntity, e2, k, e1, k, -y);
                }
            }
        } else if (auto* ind = dynamic_cast<Inductor*>(d.get())) {
            for (uint32_t k = 0; k <= NH; ++k) {
                Complex y = (k == 0) ? Complex(1e6, 0) : Complex(0, -1.0 / (w0 * k * ind->inductance()));
                Complex v1 = (n1 != 0 && n1 <= numNodes) ? X[n1][k] : Complex(0, 0);
                Complex v2 = (n2 != 0 && n2 <= numNodes) ? X[n2][k] : Complex(0, 0);
                Complex i = y * (v1 - v2);
                if (n1 != 0) addComplexResidual(sys.F, perEntity, e1, k, +i);
                if (n2 != 0) addComplexResidual(sys.F, perEntity, e2, k, -i);
                if (n1 != 0) addComplexBlock(sys.J, dim, perEntity, e1, k, e1, k, +y);
                if (n2 != 0) addComplexBlock(sys.J, dim, perEntity, e2, k, e2, k, +y);
                if (n1 != 0 && n2 != 0) {
                    addComplexBlock(sys.J, dim, perEntity, e1, k, e2, k, -y);
                    addComplexBlock(sys.J, dim, perEntity, e2, k, e1, k, -y);
                }
            }
        } else if (auto* cs = dynamic_cast<CurrentSource*>(d.get())) {
            for (uint32_t k = 0; k <= NH; ++k) {
                Complex src = (k == 0) ? Complex(cs->current(), 0) : Complex(0, 0);
                if (n1 != 0) addComplexResidual(sys.F, perEntity, e1, k, -src);
                if (n2 != 0) addComplexResidual(sys.F, perEntity, e2, k, +src);
            }
        }
    }

    // 电压源分支扩维： stamp 分支电流到 KCL，以及电压约束方程
    for (uint32_t vi = 0; vi < numVS; ++vi) {
        const auto* v = vsList[vi];
        uint32_t brEntity = branchEntity(numNodes, vi);   // 0-based entity for row/col
        uint32_t brNodeId = numNodes + vi + 1;             // 1-based index into X (current unknown)
        uint32_t n1 = v->nodes()[0];
        uint32_t n2 = v->nodes()[1];
        uint32_t e1 = nodeEntity(n1);
        uint32_t e2 = nodeEntity(n2);
        for (uint32_t k = 0; k <= NH; ++k) {
            Complex brI = X[brNodeId][k];
            // KCL: +I_br at n1, -I_br at n2
            if (n1 != 0) addComplexResidual(sys.F, perEntity, e1, k, +brI);
            if (n2 != 0) addComplexResidual(sys.F, perEntity, e2, k, -brI);
            // Jacobian d(KCL)/dI_br
            if (n1 != 0) addComplexBlock(sys.J, dim, perEntity, e1, k, brEntity, k, Complex(1, 0));
            if (n2 != 0) addComplexBlock(sys.J, dim, perEntity, e2, k, brEntity, k, Complex(-1, 0));
            // Branch equation: V_n1 - V_n2 - V_src = 0
            Complex v1 = (n1 != 0 && n1 <= numNodes) ? X[n1][k] : Complex(0, 0);
            Complex v2 = (n2 != 0 && n2 <= numNodes) ? X[n2][k] : Complex(0, 0);
            Complex src = (k == 0) ? Complex(v->voltage() * sourceScale, 0)
                                   : (k == 1 ? v->acMag() * sourceScale : Complex(0, 0));
            Complex res = (v1 - v2) - src;
            addComplexResidual(sys.F, perEntity, brEntity, k, res);
            // Jacobian d(br_eq)/dV
            if (n1 != 0) addComplexBlock(sys.J, dim, perEntity, brEntity, k, e1, k, Complex(1, 0));
            if (n2 != 0) addComplexBlock(sys.J, dim, perEntity, brEntity, k, e2, k, Complex(-1, 0));
        }
    }

    // ---- 全局 gmin 旁路：每个非地节点对地加电导 ----
    if (gmin != 0.0) {
        Complex y(gmin, 0);
        for (uint32_t i = 1; i <= numNodes; ++i) {
            uint32_t ent = nodeEntity(i);
            for (uint32_t k = 0; k <= NH; ++k) {
                addComplexResidual(sys.F, perEntity, ent, k, y * X[i][k]);
                addComplexBlock(sys.J, dim, perEntity, ent, k, ent, k, +y);
            }
        }
    }

    // ---- 非线性 OSDI 器件：IFFT -> eval -> FFT，雅可比卷积 ----
    for (const auto& d : devices) {
        auto* osdi = dynamic_cast<OsdiModel*>(d.get());
        if (!osdi || !osdi->ready()) continue;
        const OsdiDescriptor* desc = osdi->descriptor();
        uint32_t dn = desc->num_nodes;
        const auto& dnodes = d->nodes();

        std::vector<uint32_t> nodeMap(dn, 0);
        for (uint32_t i = 0; i < dn && i < dnodes.size(); ++i) nodeMap[i] = dnodes[i];

        // 构造本地节点电压时域采样
        std::vector<std::vector<double>> timeVoltages(N, std::vector<double>(dn, 0.0));
        for (uint32_t s = 0; s < N; ++s) {
            for (uint32_t i = 0; i < dn; ++i) {
                NodeId g = (i < dnodes.size()) ? dnodes[i] : 0;
                timeVoltages[s][i] = (g != 0 && g <= numNodes) ? timeV[g][s] : 0.0;
            }
        }

        // 时域电流 + 电荷采样（阻性 I + 电抗 Q）
        std::vector<std::vector<double>> timeCurrents;
        std::vector<std::vector<double>> timeCharges;   // S5 路径 B2: 节点电荷 Q(t)
        osdi->evalTimeSamples(timeVoltages, nodeMap, timeCurrents, timeCharges);

        // 电荷 Jacobian 采样（∂Q/∂V），用于频域电纳 Jacobian 块。
        // S5 路径 B2: 残差侧现也补 j·ω_k·qHarm[k] 项，与雅可比 addSusceptanceBlock
        // 对齐，实现 F/J 一致（原 TODO 已完成）。
        uint32_t nE = desc->num_jacobian_entries;
        std::vector<std::vector<double>> timeJacReact;
        osdi->evalTimeJacobiansReact(timeVoltages, nodeMap, timeJacReact);

        // 时域电流 + 电荷 -> 频域残差（F = -(I + j·ω·Q) for 非线性器件）
        // 符号约定与雅可比 addSusceptanceBlock(sign=-1) 严格对齐：
        //   雅可比侧贡献 -j·ω·Q（addConductanceBlock(Y, sign=-1)）
        //   残差侧同样 -j·ω·Q（与 -I 同号，KCL: Y·V - I_nonlin = 0）
        //   Re(-jωQ) = +ω·Im(Q), Im(-jωQ) = -ω·Re(Q)
        for (uint32_t i = 0; i < dn; ++i) {
            NodeId g = (i < dnodes.size()) ? dnodes[i] : 0;
            if (g == 0 || g > numNodes) continue;
            std::vector<double> iTime(N, 0.0);
            std::vector<double> qTime(N, 0.0);
            for (uint32_t s = 0; s < N; ++s) {
                iTime[s] = (i < timeCurrents[s].size()) ? timeCurrents[s][i] : 0.0;
                qTime[s] = (s < timeCharges.size() && i < timeCharges[s].size())
                           ? timeCharges[s][i] : 0.0;
            }
            std::vector<Complex> iHarm = currentFft(iTime, NH);
            std::vector<Complex> qHarm = currentFft(qTime, NH);
            uint32_t ent = nodeEntity(g);
            for (uint32_t k = 0; k <= NH; ++k) {
                // F_k = -I_k - j·ω_k·Q_k  (sign 与雅可比 addSusceptanceBlock 一致)
                Complex contrib;
                contrib.real(-iHarm[k].real() + k * w0 * qHarm[k].imag());   // Re(-I) + ω·Im(Q)
                contrib.imag(-iHarm[k].imag() - k * w0 * qHarm[k].real());  // Im(-I) - ω·Re(Q)
                addComplexResidual(sys.F, perEntity, ent, k, contrib);
            }
        }

        // 时域雅可比 -> 频域卷积块（阻性）
        std::vector<std::vector<double>> timeJac;
        osdi->evalTimeJacobians(timeVoltages, nodeMap, timeJac);
        for (uint32_t e = 0; e < nE; ++e) {
            const OsdiJacobianEntry& je = desc->jacobian_entries[e];
            uint32_t localA = std::min(je.nodes.node_1, dn - 1);
            uint32_t localB = std::min(je.nodes.node_2, dn - 1);
            NodeId gA = (localA < dnodes.size()) ? dnodes[localA] : 0;
            NodeId gB = (localB < dnodes.size()) ? dnodes[localB] : 0;
            if (gA == 0 || gA > numNodes || gB == 0 || gB > numNodes) continue;

            std::vector<double> gTime(N, 0.0);
            for (uint32_t s = 0; s < N; ++s) gTime[s] = timeJac[s][e];
            std::vector<Complex> G = conductanceFft(gTime, NH);
            uint32_t entA = nodeEntity(gA);
            uint32_t entB = nodeEntity(gB);
            addConductanceBlock(sys.J, dim, perEntity, entA, entB, G, NH, -1.0);
        }

        // 时域电荷雅可比 -> 频域电纳卷积块（反应性）
        for (uint32_t e = 0; e < nE; ++e) {
            const OsdiJacobianEntry& je = desc->jacobian_entries[e];
            if (je.react_ptr_off == 0) continue;
            uint32_t localA = std::min(je.nodes.node_1, dn - 1);
            uint32_t localB = std::min(je.nodes.node_2, dn - 1);
            NodeId gA = (localA < dnodes.size()) ? dnodes[localA] : 0;
            NodeId gB = (localB < dnodes.size()) ? dnodes[localB] : 0;
            if (gA == 0 || gA > numNodes || gB == 0 || gB > numNodes) continue;

            std::vector<double> gQTime(N, 0.0);
            for (uint32_t s = 0; s < N; ++s) gQTime[s] = timeJacReact[s][e];
            std::vector<Complex> GQ = conductanceFft(gQTime, NH);
            uint32_t entA = nodeEntity(gA);
            uint32_t entB = nodeEntity(gB);
            addSusceptanceBlock(sys.J, dim, perEntity, entA, entB, GQ, NH, w0, -1.0);
        }
    }

    return true;
}

void realToHarmonic(const HbRealSystem& sys,
                    const std::vector<double>& x,
                    std::vector<std::vector<Complex>>& X) {
    X.assign(sys.nEntities + 1, std::vector<Complex>(sys.NH + 1, Complex(0, 0)));
    for (uint32_t idx = 0; idx < sys.nEntities; ++idx) {
        uint32_t base = idx * sys.perEntity;
        uint32_t e = (idx < sys.numNodes) ? (idx + 1) : (idx + 1);  // entity ID = idx+1
        X[e][0] = Complex(x[base], 0);
        for (uint32_t k = 1; k <= sys.NH; ++k) {
            X[e][k] = Complex(x[base + 2 * k - 1], x[base + 2 * k]);
        }
    }
}

// 周期实信号采样 -> 单边谐波复幅度。
// 实信号 v(t) = h0 + sum_{k>=1} 2*Re{ H[k] e^{j k w0 t} }
//            = h0 + sum_{k>=1} ( H[k] e^{j k w t} + H*[k] e^{-j k w t} )
// 其中 H[k] 是双边谱第 k 个分量。我们把 h[0]=H[0]，h[k>=1]=2*H[k] 作为单边复幅度，
// 这样 nodeHarmonicsToWaveform(h, NH) 与本函数互为逆变换。
//
// 离散估计：H[k] = (1/N) sum_n v[n] exp(-j 2π k n / N)
// 因此 h[k] = (1/N) sum_n v[n] exp(-j 2π k n / N) , k=0
//        h[k] = (2/N) sum_n v[n] exp(-j 2π k n / N) , k>=1
std::vector<Complex> realSamplesToHarmonics(const std::vector<double>& t, uint32_t NH) {
    return currentFft(t, NH);
}

} // namespace rfsim
