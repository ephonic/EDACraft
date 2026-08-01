// hb_jacobian.cpp - Harmonic Balance 实数化频域雅可比与残差装配实现
#include "hb_jacobian.hpp"
#include "../model/builtin_devices.hpp"

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

// IFFT：谐波复电压 -> 时域实采样（N 点，N >= 2*(NH+1)）。
// A2-1：N 现可大于 2*(NH+1)（过采样）。多余的采样点由三角恒等式自然填充
// （谐波数固定为 0..NH，更高次谐波为 0），等效于对周期信号做更密的采样。
// 调用方按 config.oversample 决定 N，卷积混叠由此降低。
std::vector<double> ifftWaveform(const std::vector<Complex>& harmonics, uint32_t NH, uint32_t N) {
    if (N < 2 * (NH + 1)) N = 2 * (NH + 1);  // 安全下限
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
    // 与 addConductanceBlock 的 k+m 项配合：若 G 含 0..2NH，则 Y 也算到 2NH
    std::vector<Complex> Y(G.size(), Complex(0, 0));
    for (size_t l = 0; l < G.size(); ++l) {
        // j * l * w0 * G
        Y[l] = Complex(-static_cast<double>(l) * w0 * G[l].imag(),
                       static_cast<double>(l) * w0 * G[l].real());
    }
    addConductanceBlock(J, dim, perEntity, rowEntity, colEntity, Y, NH, sign);
}

// G 可以只含 0..NH（线性/近似），也可含 0..2NH（非线性精确雅可比：
// k+m 和频卷积项最大到 2NH，丢弃会导致强非线性下 Newton 方向非下降而停滞）。
void addConductanceBlock(std::vector<double>& J, uint32_t dim, uint32_t perEntity,
                         uint32_t rowEntity, uint32_t colEntity,
                         const std::vector<Complex>& G, uint32_t NH, double sign) {
    const int32_t gMax = static_cast<int32_t>(G.size()) - 1;
    auto Gval = [&G, gMax](int32_t l) -> Complex {
        if (l < 0) {
            int32_t p = -l;
            if (p > gMax) return Complex(0, 0);
            return std::conj(G[p]);
        }
        if (l > gMax) return Complex(0, 0);
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
            Complex gm = Gval(static_cast<int32_t>(k) + static_cast<int32_t>(m));
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

    // A2-1：FFT 过采样。N = 2*oversample*(NH+1)（oversample 来自 config，默认 2）。
    // 提升采样数吸收高次谐波混叠，改善非线性 HB 收敛（KI-1 根因之二）。
    // oversample 下限保护：至少 1（N=2(NH+1)，原行为）。
    const uint32_t os = std::max<uint32_t>(1u, config.oversample);
    const uint32_t N = 2u * os * (NH + 1);
    const double w0 = 2.0 * PI * config.fundamental;

    // IFFT：节点电压 -> 时域波形（包含地）
    std::vector<std::vector<double>> timeV(numNodes + 1);
    for (uint32_t i = 1; i <= numNodes; ++i) {
        timeV[i] = ifftWaveform(X[i], NH, N);
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

    // ---- 非线性器件：IFFT -> eval -> FFT，雅可比卷积（通用 DeviceModel 接口）----
    // 所有 !is_linear() 器件通过 evalHb 虚接口一次遍历提供时域采样
    // 电流/电荷与雅可比（默认实现基于 eval()，纯阻性）。
    // 先收集器件并并行 eval（每器件独立对象，线程安全），再串行 FFT + 装配。
    struct NlDevData {
        DeviceModel* dev;
        std::vector<NodeId> dnodes;
        StampPattern pattern;
        std::vector<std::vector<double>> currents;
        std::vector<std::vector<double>> charges;
        std::vector<std::vector<double>> jac;
        std::vector<std::vector<double>> jacReact;
    };
    std::vector<NlDevData> nlDevs;
    for (const auto& d : devices) {
        if (!d || d->is_linear()) continue;
        NlDevData e;
        e.dev = d.get();
        e.dnodes = d->nodes();
        d->stamp_pattern(e.pattern);
        nlDevs.push_back(std::move(e));
    }

    const size_t nNl = nlDevs.size();
#ifdef RFSIM_USE_OPENMP
    #pragma omp parallel for schedule(dynamic, 1) if(nNl >= 2)
#endif
    for (ptrdiff_t dip = 0; dip < static_cast<ptrdiff_t>(nNl); ++dip) {
        NlDevData& e = nlDevs[static_cast<size_t>(dip)];
        e.dev->evalHb(timeV, e.currents, e.charges, e.jac, e.jacReact);
    }

    // 串行 FFT + 装配（写共享 sys.F/sys.J）
    for (size_t di = 0; di < nNl; ++di) {
        const NlDevData& e = nlDevs[di];
        const auto& dnodes = e.dnodes;

        // 时域电流 + 电荷 -> 频域残差（F += +(I + j·ω·Q)）
        // 符号约定：生成模型 eval 的 f 是“电流从节点流入器件”（流出为正），
        // 与 DC/MNA 装配 F[nk] += f[k] 及本文件线性器件 +i（流出）stamp 一致。
        // （历史 OSDI resid 为“流入为正”，旧代码取负；生成模型路径必须取正。）
        for (size_t i = 0; i < dnodes.size(); ++i) {
            NodeId g = dnodes[i];
            if (g == 0 || g > numNodes) continue;
            std::vector<double> iTime(N, 0.0);
            std::vector<double> qTime(N, 0.0);
            bool hasQ = false;
            for (uint32_t s = 0; s < N; ++s) {
                if (s < e.currents.size() && i < e.currents[s].size())
                    iTime[s] = e.currents[s][i];
                if (s < e.charges.size() && i < e.charges[s].size()) {
                    qTime[s] = e.charges[s][i];
                    if (qTime[s] != 0.0) hasQ = true;
                }
            }
            std::vector<Complex> iHarm = currentFft(iTime, NH);
            std::vector<Complex> qHarm(NH + 1, Complex(0, 0));
            if (hasQ) qHarm = currentFft(qTime, NH);
            uint32_t ent = nodeEntity(g);
            for (uint32_t k = 0; k <= NH; ++k) {
                Complex contrib(iHarm[k].real() - k * w0 * qHarm[k].imag(),
                                iHarm[k].imag() + k * w0 * qHarm[k].real());
                addComplexResidual(sys.F, perEntity, ent, k, contrib);
            }
        }

        // 时域雅可比 -> 频域卷积块（阻性，e 对齐 stamp_pattern entries 顺序）
        const size_t nE = e.pattern.entries.size();
        for (size_t en = 0; en < nE; ++en) {
            NodeId gA = e.pattern.entries[en].first;
            NodeId gB = e.pattern.entries[en].second;
            if (gA == 0 || gA > numNodes || gB == 0 || gB > numNodes) continue;
            std::vector<double> gTime(N, 0.0);
            for (uint32_t s = 0; s < N; ++s) {
                if (s < e.jac.size() && en < e.jac[s].size())
                    gTime[s] = e.jac[s][en];
            }
            // 2NH 阶电导谱：卷积雅可比需要 k+m ≤ 2NH 的和频项才是精确雅可比
            // 符号 +1：与残差 F += +I 及线性器件 +y stamp 一致
            std::vector<Complex> G = conductanceFft(gTime, 2 * NH);
            addConductanceBlock(sys.J, dim, perEntity,
                                nodeEntity(gA), nodeEntity(gB), G, NH, +1.0);
        }

        // 时域电荷雅可比 -> 频域电纳卷积块（反应性，无电荷模型时 jacReact 为空）
        if (!e.jacReact.empty()) {
            for (size_t en = 0; en < nE; ++en) {
                NodeId gA = e.pattern.entries[en].first;
                NodeId gB = e.pattern.entries[en].second;
                if (gA == 0 || gA > numNodes || gB == 0 || gB > numNodes) continue;
                std::vector<double> gQTime(N, 0.0);
                bool nz = false;
                for (uint32_t s = 0; s < N; ++s) {
                    if (s < e.jacReact.size() && en < e.jacReact[s].size()) {
                        gQTime[s] = e.jacReact[s][en];
                        if (gQTime[s] != 0.0) nz = true;
                    }
                }
                if (!nz) continue;
                std::vector<Complex> GQ = conductanceFft(gQTime, 2 * NH);
                addSusceptanceBlock(sys.J, dim, perEntity,
                                    nodeEntity(gA), nodeEntity(gB), GQ, NH, w0, +1.0);
            }
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
