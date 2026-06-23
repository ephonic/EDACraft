// ac_analysis.cpp — 线性 AC 小信号分析实现
#include "ac_analysis.hpp"

#include "../model/builtin_devices.hpp"
#include "../model/osdi_model.hpp"
#include <algorithm>
#include <cmath>
#include <cstdio>

namespace rfsim {

namespace {

// 复数稠密 LU 求解（部分选主元）。求解 A·x = b。
bool complexSolve(std::vector<std::vector<Complex>>& A, std::vector<Complex>& b,
                  std::vector<Complex>& x) {
    int n = static_cast<int>(b.size());
    x.assign(n, Complex(0, 0));
    for (int k = 0; k < n; ++k) {
        // 选主元（按模）
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
    // 回代
    for (int i = n - 1; i >= 0; --i) {
        Complex s = b[i];
        for (int j = i + 1; j < n; ++j) s -= A[i][j] * x[j];
        x[i] = s / A[i][i];
    }
    return true;
}

// 向复数导纳矩阵的 (n1,n2) 位置加导纳（地节点0跳过，索引-1）
void stampAdm(std::vector<std::vector<Complex>>& A, uint32_t n1, uint32_t n2, Complex y,
              uint32_t numNodes) {
    auto idx = [](uint32_t g) -> int { return g == 0 ? -1 : int(g) - 1; };
    int i1 = idx(n1), i2 = idx(n2);
    if (i1 >= 0) A[i1][i1] += y;
    if (i2 >= 0) A[i2][i2] += y;
    if (i1 >= 0 && i2 >= 0) {
        A[i1][i2] -= y;
        A[i2][i1] -= y;
    }
    (void)numNodes;
}

} // namespace

AcResult solveAc(uint32_t numNodes,
                 const std::vector<std::unique_ptr<DeviceModel>>& devices,
                 const AcSpec& spec,
                 const std::vector<double>& freqs) {
    AcResult r;
    // 生成功率扫描频率列表
    std::vector<double> fList;
    if (!freqs.empty()) {
        fList = freqs;
    } else if (spec.sweep == AcSpec::Sweep::Lin) {
        int n = std::max(1, static_cast<int>((spec.stopFreq - spec.startFreq) /
                     std::max(1e-30, (spec.stopFreq - spec.startFreq) / 100)) + 1);
        for (int i = 0; i < n; ++i) {
            double t = double(i) / double(n - 1 > 0 ? n - 1 : 1);
            fList.push_back(spec.startFreq + t * (spec.stopFreq - spec.startFreq));
        }
    } else {
        // DEC 扫描
        if (spec.startFreq <= 0 || spec.stopFreq <= 0) {
            r.diags.error({}, "AC DEC sweep: frequency must be positive");
            return r;
        }
        double decades = std::log10(spec.stopFreq / spec.startFreq);
        int n = std::max(1, int(std::ceil(decades * spec.pointsPerDecade)) + 1);
        for (int i = 0; i < n; ++i) {
            double t = double(i) / double(n - 1 > 0 ? n - 1 : 1);
            fList.push_back(spec.startFreq * std::pow(10.0, t * decades));
        }
    }

    // 找电压源/电流源的 AC 激励（用于 RHS）
    // 收集电压源分支（AC 电压源也需扩维，但简化：AC 只支持电流源激励 + 电压源 AC 幅度）
    uint32_t numVS = 0;
    std::vector<const VoltageSource*> vsList;
    for (const auto& d : devices) {
        if (auto* v = dynamic_cast<const VoltageSource*>(d.get())) {
            vsList.push_back(v);
            ++numVS;
        }
    }
    uint32_t n = numNodes + numVS;

    r.points.reserve(fList.size());
    for (double f : fList) {
        double omega = 2.0 * 3.14159265358979323846 * f;
        // 复数矩阵 + RHS
        std::vector<std::vector<Complex>> A(n, std::vector<Complex>(n, Complex(0, 0)));
        std::vector<Complex> b(n, Complex(0, 0));

        // stamp 器件导纳
        // H5: 检测非线性器件（OSDI），AC 分析当前不支持线性化
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
        for (const auto& d : devices) {
            const auto& nds = d->nodes();
            uint32_t n1 = nds.size() > 0 ? nds[0] : 0;
            uint32_t n2 = nds.size() > 1 ? nds[1] : 0;
            if (auto* res = dynamic_cast<const Resistor*>(d.get())) {
                stampAdm(A, n1, n2, Complex(1.0 / res->resistance(), 0), numNodes);
            } else if (auto* cap = dynamic_cast<const Capacitor*>(d.get())) {
                stampAdm(A, n1, n2, cap->admittance(omega), numNodes);
            } else if (auto* ind = dynamic_cast<const Inductor*>(d.get())) {
                stampAdm(A, n1, n2, ind->admittance(omega), numNodes);
            } else if (auto* cs = dynamic_cast<const CurrentSource*>(d.get())) {
                // AC 电流源激励：注入 n1 +I_ac，n2 -I_ac（取 DC 值作为 AC 幅度简化）
                // 完整实现应解析 I1 n1 n2 AC <mag> <phase>
                if (n1 != 0) b[n1 - 1] += Complex(cs->current(), 0);
                if (n2 != 0) b[n2 - 1] -= Complex(cs->current(), 0);
            }
            // 电压源 stamp 见下方分支扩维
        }

        // 电压源分支扩维 + AC 激励
        for (uint32_t k = 0; k < numVS; ++k) {
            const auto* v = vsList[k];
            uint32_t br = numNodes + k;
            int i1 = v->nodes()[0] != 0 ? int(v->nodes()[0]) - 1 : -1;
            int i2 = v->nodes()[1] != 0 ? int(v->nodes()[1]) - 1 : -1;
            int ibr = int(br);
            if (i1 >= 0) { A[i1][ibr] += Complex(1, 0); A[ibr][i1] += Complex(1, 0); }
            if (i2 >= 0) { A[i2][ibr] -= Complex(1, 0); A[ibr][i2] -= Complex(1, 0); }
            b[ibr] = v->acMag();  // AC 激励（DC 电压值不参与 AC）
        }

        std::vector<Complex> x;
        if (!complexSolve(A, b, x)) {
            r.diags.error({}, "AC: singular matrix at f=" + std::to_string(f));
            continue;
        }
        AcPoint p;
        p.freq = f;
        p.nodeVoltages.assign(numNodes + 1, Complex(0, 0));
        for (uint32_t i = 0; i < numNodes; ++i) p.nodeVoltages[i + 1] = x[i];
        r.points.push_back(std::move(p));
    }

    r.ok = !r.points.empty() && !r.diags.has_errors();
    return r;
}

} // namespace rfsim
