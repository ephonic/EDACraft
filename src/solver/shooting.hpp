// shooting.hpp — Single Shooting 周期稳态求解器
#ifndef RFSIM_SOLVER_SHOOTING_HPP
#define RFSIM_SOLVER_SHOOTING_HPP

#include "time_stepper.hpp"
#include "../model/device_model.hpp"
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
    bool verbose = false;
};

struct ShootingResult {
    TimeDomainResult waveform;         // 一个周期内的时域波形
    bool converged = false;
    uint32_t iterations = 0;
    Diagnostics diags;
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

} // namespace rfsim

#endif // RFSIM_SOLVER_SHOOTING_HPP
