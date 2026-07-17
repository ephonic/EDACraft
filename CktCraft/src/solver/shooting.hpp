// shooting.hpp — Single Shooting 周期稳态求解器
#ifndef RFSIM_SOLVER_SHOOTING_HPP
#define RFSIM_SOLVER_SHOOTING_HPP

#include "time_stepper.hpp"
#include "hb_solver.hpp"
#include "../assembly/linear_solver_factory.hpp"
#include "../model/device_model.hpp"
#include "../util/bench.hpp"
#include "gmin_options.hpp"
#include <vector>

namespace rfsim {

struct ShootingConfig {
    double fundamental = 1e6;          // 基频 (Hz)，周期 T = 1/fundamental
    uint32_t numTimePoints = 100;      // 每周期时间点数（决定 dt）
    IntegrationMethod method = IntegrationMethod::BackwardEuler;
};

struct ShootingOptions {
    uint32_t maxIter = 50;
    double reltol = 1e-6;
    double abstol = 1e-9;
    double dvmax = 0.5;                // 外层单步最大电压修正
    double localNewtonDvMax = 0.5;     // 每个时间步内部 Newton 软阻尼上限
    double epsilon = 1e-7;             // 有限差分灵敏度步长
    uint32_t localNewtonMaxIter = 50;  // 每个时间步内部 Newton 最大迭代数

    // P1-5/P1-8: 内层 Newton 的 gmin log-spaced homotopy（DC 同款模式）。
    //   gminSteps=0（默认）→ 零开销，单 gmin 级（=opts.gmin.gmin）求解；
    //   gminSteps>0       → 从 gminStart 对数等距递降到 gmin，共 gminSteps+1
    //                       级，每级使用上一级的解作为 warm start。
    // 注意：homotopy schedule 必须只依赖于 opts，不能依赖 trialNodeV，否则
    // 会破坏外层 FD 雅可比的 main↔perturb 一致性（参见 shooting.cpp 内的
    // P0-4 设计注释）。
    GminOptions gmin{};

    bool verbose = false;

    // A1-7：线性求解方法（默认 Auto）。外层 monodromy 雅可比与内层时间步 Newton 共用。
    SolverMethod solver = SolverMethod::Auto;

    // B2：自动 multi-rate。开启后对所有 OSDI 器件启用 mrAutoTune（K 自适应）。
    // 注意：Shooting 的 FD 雅可比路径已强制 needsEval（见 integrateOnePeriod），
    // 故 multi-rate 仅影响主路径与最终波形积分的器件 eval 频率，不破坏 FD 一致性。
    // 默认 false（与原 bit-identical）。
    bool multiRate = false;
};

struct ShootingResult {
    TimeDomainResult waveform;         // 一个周期内的时域波形
    bool converged = false;
    uint32_t iterations = 0;
    Diagnostics diags;

    // V2-γ C3: 性能计数器（RFSIM_BENCH_JSON=1 时填充）
    BenchCounters bench;
};

// Single Shooting PSS 求解。
//   numNodes: 非地节点数
//   devices:  器件列表
//   dcOpNodeV: DC 工作点（作为初始猜测；可为空，此时内部用 0 猜测）
ShootingResult solveShooting(uint32_t numNodes,
                             const std::vector<std::unique_ptr<DeviceModel>>& devices,
                             const ShootingConfig& config,
                             const std::vector<double>* dcOpNodeV = nullptr,
                             const ShootingOptions& opts = {});

// 把 Shooting 收敛后的稳态波形转换为 HB 单边谐波表示。
// 从 sr.waveform.points 抽取每个非地节点（NodeId 1..numNodes）的电压采样
// （TimePoint::x[nodeId-1]，对应 transient_assembly 的 numNodes 个节点电压未知量），
// 做 DFT 得到 NodeHarmonics。
//   numHarmonics: 输出谐波数 NH（包含 0=DC, 1..NH）。
//   fundamental: 基频 Hz，写入 HbResult.config。
// 要求采样点数 >= 2*(NH+1)，否则 HbResult.ok=false 并写入诊断。
HbResult shootingToHarmonics(const ShootingResult& sr,
                             uint32_t numNodes,
                             uint32_t numHarmonics,
                             double fundamental);

} // namespace rfsim

#endif // RFSIM_SOLVER_SHOOTING_HPP
