// stability.cpp — S 参数稳定性分析实现
//
// 详见 stability.hpp。纯复数运算，无求解器依赖。
#include "stability.hpp"

#include <cmath>
#include <iomanip>
#include <iostream>

namespace rfsim {

namespace {
// 复数 dB：20·log10(|z|)
double magDb(const Complex& z) {
    double m = std::abs(z);
    return (m > 0) ? 20.0 * std::log10(m) : -999.0;
}
} // namespace

StabilityResult computeStability(const TouchstoneData& td) {
    StabilityResult r;
    r.numPorts = td.numPorts;
    if (td.numPorts != 2) {
        r.message = "stability analysis requires 2-port S-parameters (got "
                    + std::to_string(td.numPorts) + ")";
        return r;
    }
    for (size_t fi = 0; fi < td.freqs.size(); ++fi) {
        const auto& S = td.S[fi];
        if (S.size() < 4) continue;
        Complex S11 = S[0], S21 = S[1], S12 = S[2], S22 = S[3];  // S[i*2+j]
        Complex delta = S11 * S22 - S12 * S21;
        double dMag = std::abs(delta);
        double denom = 2.0 * std::abs(S12 * S21);
        double K = (denom > 1e-30)
                   ? (1.0 - std::norm(S11) - std::norm(S22) + dMag * dMag) / denom
                   : 1e30;
        // μ = (1 - |S11|²) / (|S22 - Δ·S11*| + |S12·S21|)
        Complex t = S22 - delta * std::conj(S11);
        double muDenom = std::abs(t) + std::abs(S12 * S21);
        double mu = (muDenom > 1e-30) ? (1.0 - std::norm(S11)) / muDenom : 1e30;
        bool stable = (K > 1.0) && (dMag < 1.0);
        // 增益
        double gainDb;
        if (K >= 1.0 && denom > 1e-30) {
            // MAG = |S21/S12|·(K - sqrt(K²-1))
            double magRatio = std::abs(S21) / std::max(std::abs(S12), 1e-30);
            double magFactor = K - std::sqrt(std::max(K * K - 1.0, 0.0));
            gainDb = 10.0 * std::log10(std::max(magRatio * magFactor, 1e-30));
        } else {
            // MSG = |S21/S12|
            double msg = std::abs(S21) / std::max(std::abs(S12), 1e-30);
            gainDb = 10.0 * std::log10(std::max(msg, 1e-30));
        }
        // 单边化增益 G_U = |S21|²/((1-|S11|²)(1-|S22|²))
        double denomU = (1.0 - std::norm(S11)) * (1.0 - std::norm(S22));
        double gu = (denomU > 1e-30) ? std::norm(S21) / denomU : 0.0;
        double guDb = (gu > 1e-30) ? 10.0 * std::log10(gu) : -999.0;

        StabilityPoint p;
        p.freq = td.freqs[fi];
        p.K = K;
        p.deltaMag = dMag;
        p.mu = mu;
        p.unconditionallyStable = stable;
        p.maxStableGain_dB = gainDb;
        p.unilateralGain_dB = guDb;
        r.points.push_back(p);
    }
    r.ok = !r.points.empty();
    return r;
}

void writeStability(std::ostream& os, const StabilityResult& r) {
    if (!r.ok) { os << "stability analysis failed: " << r.message << "\n"; return; }
    os << "\n=== S-parameter Stability Analysis (2-port) ===\n";
    os << "  freq(Hz)       K        |Δ|      μ      stable  MAG/MSG(dB)  G_U(dB)\n";
    os.setf(std::ios::scientific);
    for (const auto& p : r.points) {
        os << "  " << std::setprecision(4) << std::setw(12) << p.freq
           << "  " << std::setprecision(4) << std::setw(8) << p.K
           << "  " << std::setw(8) << p.deltaMag
           << "  " << std::setw(8) << p.mu
           << "  " << (p.unconditionallyStable ? "YES" : "no ")
           << "    " << std::setw(9) << p.maxStableGain_dB
           << "    " << std::setw(8) << p.unilateralGain_dB << "\n";
    }
    os.unsetf(std::ios::scientific);
    os << "\n  unconditional stability: K>1 and |Δ|<1\n";
}

} // namespace rfsim
