// time_stepper.hpp — 固定步长时域积分器
#ifndef RFSIM_SOLVER_TIME_STEPPER_HPP
#define RFSIM_SOLVER_TIME_STEPPER_HPP

#include "../assembly/transient_assembly.hpp"
#include "../assembly/linear_solver_factory.hpp"
#include "../model/device_model.hpp"
#include "gmin_options.hpp"
#include <vector>

namespace rfsim {

struct TimeStepperOptions {
    double tstop = 1e-6;               // 终止时间
    double dt = 1e-9;                  // 固定步长
    IntegrationMethod method = IntegrationMethod::BackwardEuler;
    // P1-8: 共享 gmin 配置。Transient 当前仅消费 gmin.gmin（同伦字段保留
    // 以备将来扩展，gminSteps 默认 0 即不启用）。
    GminOptions gmin{};
    // 内层 Newton 控制
    uint32_t localNewtonMaxIter = 50;  // 单步内 Newton 最大迭代数
    double dvmax = 0.2;                // 单步节点电压最大变化（V），PN 结保护
    double abstol = 1e-9;              // 节点电压收敛绝对容差
    double reltol = 1e-3;              // 节点电压收敛相对容差
    bool failOnNonConverge = true;     // 内层 Newton 失败时是否硬退出（true=报错；false=继续推进）
    // A1-7：线性求解方法（默认 Auto）。
    SolverMethod solver = SolverMethod::Auto;
    // B2：自动 multi-rate。开启后对所有 OSDI 器件启用 mrAutoTune——静态/慢器件的
    // 速率比 K 自适应增大（每 K 步只 eval 一次 + swapState），快器件回退 K=1。
    // 现有 setRateRatio/setMrAutoTune 机制已实现；此处仅提供统一开关。
    // 默认 false（与原 bit-identical）；大电路 transient/PSS 开启可省 eval。
    bool multiRate = false;
};

struct TimePoint {
    double time;
    std::vector<double> x;             // MNA 解：节点电压(1..numNodes) + 分支电流(numBranches)
};

struct TimeDomainResult {
    std::vector<TimePoint> points;
    bool ok = false;
    uint32_t numNodes = 0;
    uint32_t numBranches = 0;
    Diagnostics diags;
};

// 固定步长积分一个时间段 [0, tstop]。
//   numNodes: 非地节点数
//   devices:  器件列表（含动态器件，其内部状态会被更新）
//   initialNodeV: 初始节点电压（索引=NodeId；大小 >= numNodes+1）
// 返回每个时间点的完整 MNA 解。
TimeDomainResult integrateTransient(uint32_t numNodes,
                                    const std::vector<std::unique_ptr<DeviceModel>>& devices,
                                    const std::vector<double>& initialNodeV,
                                    const TimeStepperOptions& opts = {});

} // namespace rfsim

#endif // RFSIM_SOLVER_TIME_STEPPER_HPP
