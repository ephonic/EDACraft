// time_stepper.hpp — 固定步长时域积分器
#ifndef RFSIM_SOLVER_TIME_STEPPER_HPP
#define RFSIM_SOLVER_TIME_STEPPER_HPP

#include "../assembly/transient_assembly.hpp"
#include "../model/device_model.hpp"
#include <vector>

namespace rfsim {

struct TimeStepperOptions {
    double tstop = 1e-6;               // 终止时间
    double dt = 1e-9;                  // 固定步长
    IntegrationMethod method = IntegrationMethod::BackwardEuler;
    double gmin = 1e-12;               // 节点对地小电导，保证可解性
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
