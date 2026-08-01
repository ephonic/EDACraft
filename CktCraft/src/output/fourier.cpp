// fourier.cpp - .four 傅里叶分析实现
#include "fourier.hpp"
#include "../model/builtin_devices.hpp"

#include <cmath>
#include <iomanip>
#include <iostream>

namespace rfsim {

FourierResult computeFourier(const TimeDomainResult& wave,
                             const Circuit& circuit,
                             double freq,
                             const std::string& signalExpr,
                             uint32_t numHarmonics) {
    FourierResult r;
    r.fundamentalFreq = freq;
    r.signal = signalExpr;

    // 解析信号表达式 v(node) / i(branch)
    // 复用 measure.cpp 的逻辑：从 wave 中提取信号列
    auto resolveSignal = [&](const std::string& expr) -> int {
        std::string s = expr;
        // 去引号
        if (!s.empty() && s.front() == '\'') s.erase(0, 1);
        if (!s.empty() && s.back() == '\'') s.pop_back();
        if (s.size() > 2 && (s[0] == 'v' || s[0] == 'V') && s[1] == '(' && s.back() == ')') {
            std::string inner = s.substr(2, s.size() - 3);
            bool isNum = !inner.empty();
            for (char c : inner) if (!std::isdigit(static_cast<unsigned char>(c))) { isNum = false; break; }
            if (isNum) {
                uint32_t nid = static_cast<uint32_t>(std::stoul(inner));
                if (nid >= 1 && nid <= wave.numNodes) return static_cast<int>(nid - 1);
            } else {
                NodeId nid = circuit.nodes.lookup(inner);
                if (nid != 0xFFFFFFFFu && nid >= 1 && nid <= wave.numNodes)
                    return static_cast<int>(nid - 1);
            }
        }
        if (s.size() > 2 && (s[0] == 'i' || s[0] == 'I') && s[1] == '(' && s.back() == ')') {
            std::string inner = s.substr(2, s.size() - 3);
            bool isNum = !inner.empty();
            for (char c : inner) if (!std::isdigit(static_cast<unsigned char>(c))) { isNum = false; break; }
            if (isNum) {
                uint32_t bid = static_cast<uint32_t>(std::stoul(inner));
                if (bid < wave.numBranches) return static_cast<int>(wave.numNodes + bid);
            }
        }
        return -1;
    };

    int col = resolveSignal(signalExpr);
    if (col < 0) {
        r.message = "cannot resolve signal '" + signalExpr + "'";
        return r;
    }

    // 提取信号值序列
    std::vector<double> t, y;
    for (const auto& tp : wave.points) {
        double v = (static_cast<size_t>(col) < tp.x.size()) ? tp.x[col] : 0.0;
        t.push_back(tp.time);
        y.push_back(v);
    }
    if (y.size() < 4) {
        r.message = "too few time points for DFT";
        return r;
    }

    // DFT：提取 0..numHarmonics 谐波
    // 取波形最后一个完整周期的 N 个点做 DFT
    double T = 1.0 / freq;
    // 找到最后一个 >= t_stop - T 的点
    double tStop = t.back();
    double tStart = tStop - T;
    // 收集 [tStart, tStop] 内的点
    std::vector<double> yPeriod;
    for (size_t i = 0; i < t.size(); ++i) {
        if (t[i] >= tStart - 1e-15) yPeriod.push_back(y[i]);
    }
    if (yPeriod.size() < 4) {
        // 如果不够一个周期，用全部数据
        yPeriod = y;
    }

    size_t N = yPeriod.size();
    constexpr double PI = 3.14159265358979323846;

    // DFT: X[k] = sum_n x[n] * exp(-j*2*pi*k*n/N) / N
    // 只算 0..numHarmonics
    double fundMag = 0;
    for (uint32_t k = 0; k <= numHarmonics; ++k) {
        double re = 0, im = 0;
        for (size_t n = 0; n < N; ++n) {
            double ph = 2.0 * PI * k * n / N;
            re += yPeriod[n] * std::cos(ph);
            im -= yPeriod[n] * std::sin(ph);
        }
        re /= N;
        im /= N;
        FourierHarmonic h;
        h.order = k;
        h.magnitude = std::sqrt(re * re + im * im);
        if (k > 0) h.magnitude *= 2.0;  // 单边谱补偿
        h.phaseDeg = (k > 0 && h.magnitude > 1e-30) ? std::atan2(-im, re) * 180.0 / PI : 0.0;
        if (k == 1) fundMag = h.magnitude;
        h.normMag = (k > 0 && fundMag > 1e-30) ? h.magnitude / fundMag : 0.0;
        r.harmonics.push_back(h);
    }

    // THD = sqrt(sum(|Hk|^2, k>=2)) / |H1| * 100%
    if (fundMag > 1e-30) {
        double sumSq = 0;
        for (uint32_t k = 2; k <= numHarmonics; ++k) {
            if (k < r.harmonics.size()) sumSq += r.harmonics[k].magnitude * r.harmonics[k].magnitude;
        }
        r.thd = std::sqrt(sumSq) / fundMag * 100.0;
    } else {
        r.thd = 0;
    }

    r.ok = true;
    return r;
}

void writeFourier(std::ostream& os, const FourierResult& r) {
    if (!r.ok) { os << "Fourier analysis failed: " << r.message << "\n"; return; }
    os << "\n=== Fourier Analysis ===\n";
    os << "  signal: " << r.signal << "  fundamental: " << r.fundamentalFreq << " Hz\n";
    os << "  harmonics: " << r.harmonics.size() - 1 << "  THD: " << r.thd << " %\n\n";
    os << "  harm   frequency(Hz)   magnitude      phase(deg)   norm_mag\n";
    os.setf(std::ios::scientific);
    for (const auto& h : r.harmonics) {
        os << "  " << std::setw(3) << h.order
           << "  " << std::setw(14) << std::setprecision(6) << h.order * r.fundamentalFreq
           << "  " << std::setw(14) << std::setprecision(6) << h.magnitude
           << "  " << std::setw(12) << std::setprecision(4) << h.phaseDeg
           << "  " << std::setw(12) << std::setprecision(6) << h.normMag << "\n";
    }
    os.unsetf(std::ios::scientific);
}

} // namespace rfsim
