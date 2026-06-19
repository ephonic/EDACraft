// hb_nonlinear.hpp - Nonlinear Harmonic Balance (plan.md 4.4/4.5)
//
// Nonlinear HB: Newton iteration in frequency domain.
// Each iteration:
//   1. IFFT X (node harmonic voltages) to time-domain samples V(t)
//   2. At each sample t: eval nonlinear devices -> I(t), jacobian G(t)
//   3. FFT I(t) -> residual F_k; convolve G(t) -> jacobian J (quasi-block)
//   4. Linear devices stamp directly in frequency domain
//   5. Solve J·dX = -F, update X with damping
//
// This implements the full nonlinear HB for circuits with OSDI devices.
#ifndef RFSIM_SOLVER_HB_NONLINEAR_HPP
#define RFSIM_SOLVER_HB_NONLINEAR_HPP

#include "hb_solver.hpp"
#include "../model/device_model.hpp"
#include "../model/osdi_model.hpp"
#include <complex>
#include <vector>

namespace rfsim {

// 非线性 HB 结果（同 HbResult 但经 Newton 求解）
struct HbNlResult {
    std::vector<NodeHarmonics> nodeVoltages;
    bool converged = false;
    Diagnostics diags;
    HbConfig config;
    uint32_t iterations = 0;
    uint32_t continuationSteps = 0; // 实际使用的 source/gmin continuation 步数
};

// 非线性 HB Newton 求解选项
struct HbNlOptions {
    uint32_t maxIter = 100;   // 每步 Newton 最大迭代次数
    double reltol = 1e-6;     // 相对收敛容差
    double abstol = 1e-9;     // 绝对收敛容差
    double dvmax = 0.5;       // 每谐波最大电压修正（V）
    double lambda = 1e-6;     // Tikhonov 正则化（加到 Jacobian 对角线）

    // source stepping：将独立源幅度从 sourceStart 逐步提升到 sourceStop
    double sourceStart = 0.0; // 起始源幅度（0=关）
    double sourceStop  = 1.0; // 最终源幅度
    uint32_t sourceSteps = 0; // 分段数；0 表示不启用 source stepping

    // gmin stepping：给每个非地节点并联 gmin 电导辅助收敛
    double gmin = 1e-12;      // 最终 gmin
    double gminStart = 1e-2;  // 起始 gmin（大电导使非线性器件更线性）
    uint32_t gminSteps = 0;   // 分段数；0 表示不启用 gmin stepping
};

// 求解非线性 HB。
//   numNodes: 非地节点数
//   devices:  器件（含 OSDI 非线性器件 + 线性器件）
//   config:   基频与谐波数
//   initialGuess: 初始猜测（可为空，默认用 DC 工作点）
//   opts:     Newton 与 continuation 选项
HbNlResult solveHbNonlinear(uint32_t numNodes,
                            const std::vector<std::unique_ptr<DeviceModel>>& devices,
                            const HbConfig& config,
                            const std::vector<double>* dcOpNodeV = nullptr,
                            const HbNlOptions& opts = {});

} // namespace rfsim

#endif // RFSIM_SOLVER_HB_NONLINEAR_HPP
