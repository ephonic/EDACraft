// hb_solver.cpp — Harmonic Balance 求解器实现（线性电路）
#include "hb_solver.hpp"

#include <algorithm>
#include <cmath>

namespace rfsim {

namespace {

const double PI = 3.14159265358979323846;

// 复数稠密 LU 求解（部分选主元），与 ac_analysis.cpp 中相同逻辑。
// 这里内联一份避免跨文件依赖耦合。
bool complexSolve(std::vector<std::vector<Complex>>& A, std::vector<Complex>& b,
                  std::vector<Complex>& x) {
    int n = static_cast<int>(b.size());
    x.assign(n, Complex(0, 0));
    for (int k = 0; k < n; ++k) {
        int piv = k;
        double maxMod = std::abs(A[k][k]);
        for (int i = k + 1; i < n; ++i) {
            double m = std::abs(A[i][k]);
            if (m > maxMod) { maxMod = m; piv = i; }
        }
        if (maxMod < 1e-300) return false;
        if (piv != k) { std::swap(A[k], A[piv]); std::swap(b[k], b[piv]); }
        Complex pivot = A[k][k];
        for (int i = k + 1; i < n; ++i) {
            Complex f = A[i][k] / pivot;
            A[i][k] = f;
            for (int j = k + 1; j < n; ++j) A[i][j] -= f * A[k][j];
            b[i] -= f * b[k];
        }
    }
    for (int i = n - 1; i >= 0; --i) {
        Complex s = b[i];
        for (int j = i + 1; j < n; ++j) s -= A[i][j] * x[j];
        x[i] = s / A[i][i];
    }
    return true;
}

// 向复矩阵 stamp 导纳 y 到 (n1,n2)
void stampY(std::vector<std::vector<Complex>>& A, uint32_t n1, uint32_t n2, Complex y) {
    auto idx = [](uint32_t g) -> int { return g == 0 ? -1 : int(g) - 1; };
    int i1 = idx(n1), i2 = idx(n2);
    if (i1 >= 0) A[i1][i1] += y;
    if (i2 >= 0) A[i2][i2] += y;
    if (i1 >= 0 && i2 >= 0) { A[i1][i2] -= y; A[i2][i1] -= y; }
}

} // namespace

HbResult solveHbLinear(uint32_t numNodes,
                       const std::vector<std::unique_ptr<DeviceModel>>& devices,
                       const HbConfig& config) {
    HbResult r;
    r.config = config;
    uint32_t NH = config.numHarmonics;

    // 收集电压源（需分支扩维，与 DC/AC 一致）
    std::vector<const VoltageSource*> vsList;
    for (const auto& d : devices) {
        if (auto* v = dynamic_cast<const VoltageSource*>(d.get())) vsList.push_back(v);
    }
    uint32_t numVS = static_cast<uint32_t>(vsList.size());
    uint32_t n = numNodes + numVS;

    // 初始化节点谐波电压（numNodes+1 含地）
    r.nodeVoltages.assign(numNodes + 1, NodeHarmonics{});
    for (auto& nh : r.nodeVoltages) nh.v.assign(NH + 1, Complex(0, 0));

    // 对每个谐波独立求解频域 MNA
    for (uint32_t k = 0; k <= NH; ++k) {
        double omega = (k == 0) ? 0.0 : 2.0 * PI * config.fundamental * k;
        std::vector<std::vector<Complex>> A(n, std::vector<Complex>(n, Complex(0, 0)));
        std::vector<Complex> b(n, Complex(0, 0));

        // stamp 线性器件
        for (const auto& d : devices) {
            const auto& nds = d->nodes();
            uint32_t n1 = nds.size() > 0 ? nds[0] : 0;
            uint32_t n2 = nds.size() > 1 ? nds[1] : 0;

            if (auto* res = dynamic_cast<const Resistor*>(d.get())) {
                stampY(A, n1, n2, Complex(1.0 / res->resistance(), 0));
            } else if (auto* cap = dynamic_cast<const Capacitor*>(d.get())) {
                // DC (k=0): 开路 Y=0; 否则 Y=jωC
                Complex y = (k == 0) ? Complex(1e-12, 0) : Complex(0, omega * cap->capacitance());
                stampY(A, n1, n2, y);
            } else if (auto* ind = dynamic_cast<const Inductor*>(d.get())) {
                // DC: 短路 Y=大; 否则 Y=1/(jωL)
                Complex y = (k == 0) ? Complex(1e6, 0) : Complex(0, -1.0 / (omega * ind->inductance()));
                stampY(A, n1, n2, y);
            } else if (auto* cs = dynamic_cast<const CurrentSource*>(d.get())) {
                // 电流源激励：DC 分量在 k=0，正弦分量在 k=1（基频）
                if (k == 0) {
                    if (n1 != 0) b[n1 - 1] -= Complex(cs->current(), 0);
                    if (n2 != 0) b[n2 - 1] += Complex(cs->current(), 0);
                }
                // 正弦电流源在基频的激励由 setAcMag 或参数指定，M3 简化暂略
            }
        }

        // 电压源分支扩维 + 谐波激励
        for (uint32_t vi = 0; vi < numVS; ++vi) {
            const auto* v = vsList[vi];
            uint32_t br = numNodes + vi;
            int i1 = v->nodes()[0] != 0 ? int(v->nodes()[0]) - 1 : -1;
            int i2 = v->nodes()[1] != 0 ? int(v->nodes()[1]) - 1 : -1;
            int ibr = int(br);
            if (i1 >= 0) { A[i1][ibr] += Complex(1, 0); A[ibr][i1] += Complex(1, 0); }
            if (i2 >= 0) { A[i2][ibr] -= Complex(1, 0); A[ibr][i2] -= Complex(1, 0); }
            // 谐波激励：DC 分量在 k=0；正弦分量（acMag）在 k=1（基频）
            if (k == 0) {
                b[ibr] = Complex(v->voltage(), 0);  // DC 偏置
            } else if (k == 1) {
                b[ibr] = v->acMag();  // 基频正弦激励（AC 幅度）
            }
            // 高阶谐波激励为 0
        }

        std::vector<Complex> x;
        if (!complexSolve(A, b, x)) {
            r.diags.error({}, "HB: singular matrix at harmonic " + std::to_string(k));
            return r;
        }
        // 提取节点谐波电压
        for (uint32_t i = 0; i < numNodes; ++i) {
            r.nodeVoltages[i + 1].v[k] = x[i];
        }
    }

    r.ok = true;
    return r;
}

std::vector<double> nodeHarmonicsToWaveform(const NodeHarmonics& nh, uint32_t numHarmonics) {
    // IFFT: 2*(NH+1) 个时域采样点，覆盖一个基频周期 T=1/f0
    uint32_t N = 2 * (numHarmonics + 1);
    std::vector<double> wave(N, 0.0);
    for (uint32_t t = 0; t < N; ++t) {
        double sum = 0;
        for (uint32_t k = 0; k <= numHarmonics && k < nh.v.size(); ++k) {
            double phase = 2.0 * PI * k * t / N;
            // Re{ V_k * exp(j*phase) }
            sum += nh.v[k].real() * std::cos(phase) - nh.v[k].imag() * std::sin(phase);
        }
        wave[t] = sum;
    }
    return wave;
}

} // namespace rfsim
