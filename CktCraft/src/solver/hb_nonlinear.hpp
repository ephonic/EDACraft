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
#include "../assembly/linear_solver_factory.hpp"
#include "../model/device_model.hpp"
#include "../model/osdi_model.hpp"
#include "../util/bench.hpp"
#include "gmin_options.hpp"
#include "nonlinear_damping.hpp"
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

    // V2-γ C3: 性能计数器（RFSIM_BENCH_JSON=1 时填充）
    BenchCounters bench;
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

    // P1-8: 共享 gmin 配置；HbNl 默认关同伦（gminSteps=0）。
    GminOptions gmin{};

    // V2-γ post-S2: 自动同伦。若调用者保持默认 sourceSteps=0 **且** gminSteps=0
    // 且本开关开启，solveHbNonlinear 会覆盖为 sourceSteps=4, gminSteps=4,
    // gminStart=max(opts.gminStart, 1e-3)，专为 BSIM4 等 OSDI 强非线性器件的
    // S2-grid 收敛场景使用。
    // 默认 false：保持向后兼容；显式置 true 才启用（如 LargeCircuitBsim4 S2 grid）。
    bool autoHomotopy = false;

    // V2-δ S1 plan0621-v4 §1.3 路径 D：AC 小信号 warm-start。
    // 在 HB Newton 入口先做一次线性化 AC 求解，把 X[e][k>=1] 填充为
    // Y⁻¹(jω_k)·source(k) 的小信号解，再进入完整 Newton。
    // 失败时静默回退到 DC-only 暖启动，等价原行为，无回归风险。
    // 默认 true：AC 仅在 NH>=1 且 sources 非零时生效，零激励/纯 DC 测试无影响。
    bool acWarmStart = true;

    // A1-7：线性求解方法（默认 Auto）。HB-NL 当前走内部 dense LU / GMRES 路径
    //（按 dim<=gmresThreshold 自动选，见 hb_nonlinear.cpp），此字段为预留——
    // 未来若把 HB 内层求解也纳入 LinearSolver 抽象时启用。
    SolverMethod solver = SolverMethod::Auto;

    // A1-7：GMRES 可配参数（替换 hb_nonlinear.cpp 的硬编码 min(50,dim)/dim*2）。
    // 0 表示用默认（restart=50 或 dim，maxIter=dim*2）。
    uint32_t gmresRestart = 0;
    uint32_t gmresMaxIter = 0;
    double gmresReltol = 1e-8;

    // A2-4：Newton 阻尼策略。默认 LevenbergMarquardt（自适应 λ，对强非线性/病态
    // 雅可比比固定 Tikhonov 更鲁棒）。可选 Backtracking（原行为）/TrustRegion。
    // lambda 仍作为 LM 的初始 λ（lambda>0 时启用 LM 正则；=0 退化为纯 Newton）。
    DampingStrategy damping = DampingStrategy::LevenbergMarquardt;
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
