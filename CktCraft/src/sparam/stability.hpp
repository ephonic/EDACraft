// stability.hpp — S 参数稳定性分析（K-factor / Mu / 稳定性圆）
//
// 优化项5：从二端口 S 参数计算 RF 稳定性指标。纯后处理（无求解器）。
// 用于放大器设计：判断器件是否无条件稳定（任意无源负载/源都不振荡）。
//
// 指标（二端口）：
//   - Rollett K-factor: K = (1 - |S11|² - |S22|² + |Δ|²) / (2·|S12·S21|)
//     无条件稳定当且仅当 K > 1 且 |Δ| < 1（Δ = S11·S22 - S12·S21）
//   - |Δ| = |S11·S22 - S12·S21|
//   - 单边化增益 G_U = |S21|² / ((1-|S11|²)(1-|S22|²))（S12=0 假设下的最大增益）
//   - 最大可用增益 MAG（K>1 时）= |S21/S12|·(K - sqrt(K²-1))
//   - 最大稳定增益 MSG（K<1 时）= |S21/S12|
//   - 稳定性因子 μ（mu）= (1 - |S11|²) / ((|S22-Δ·conj(S11)|) + |S12·S21|)；μ>1 无条件稳定
//
// 适用于 2 端口网络（numPorts == 2）。
#ifndef RFSIM_SPARAM_STABILITY_HPP
#define RFSIM_SPARAM_STABILITY_HPP

#include "touchstone.hpp"
#include <string>
#include <vector>

namespace rfsim {

// 单频率点的稳定性指标
struct StabilityPoint {
    double freq;          // Hz
    double K = 0.0;       // Rollett K-factor
    double deltaMag = 0.0;// |Δ|
    double mu = 0.0;      // μ（mu）稳定性因子
    bool unconditionallyStable = false;  // K>1 且 |Δ|<1
    double maxStableGain_dB = 0.0;  // MSG (K<1) 或 MAG (K>=1)，dB
    double unilateralGain_dB = 0.0; // G_U，dB
};

struct StabilityResult {
    std::vector<StabilityPoint> points;
    size_t numPorts = 0;
    bool ok = false;
    std::string message;
};

// 从 Touchstone S 参数计算各频率点的稳定性指标（要求 numPorts == 2）。
StabilityResult computeStability(const TouchstoneData& td);

// 打印稳定性表到流（freq, K, |Δ|, μ, stable?, MAG/MSG, G_U）。
void writeStability(std::ostream& os, const StabilityResult& r);

} // namespace rfsim

#endif // RFSIM_SPARAM_STABILITY_HPP
