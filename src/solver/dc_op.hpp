// dc_op.hpp — DC 工作点分析（含非线性 Newton 迭代）
//
// 装配 MNA → 若含非线性器件则 Newton 迭代（每步重 stamp OSDI 雅可比+残差）
// → LU 求解 → 收敛检查 → 提取节点电压。
#ifndef RFSIM_SOLVER_DC_OP_HPP
#define RFSIM_SOLVER_DC_OP_HPP

#include "../assembly/mna.hpp"
#include "../model/device_model.hpp"
#include <vector>

namespace rfsim {

struct DcOpResult {
    // 节点电压（索引=NodeId，0=地=0V）
    std::vector<double> nodeVoltages;
    // 电压源分支电流
    std::vector<double> branchCurrents;
    bool converged = false;
    Diagnostics diags;
    uint32_t iterations = 0;
};

// Newton 迭代参数
struct DcOpOptions {
    uint32_t maxIterations = 100;
    double reltol = 1e-6;     // 相对收敛容差
    double abstol = 1e-12;    // 绝对收敛容差（A/V）
    double gmin = 1e-12;      // 基础 Gmin 旁路
    double dvmax = 0.1;       // 单步节点电压最大变化（V），PN 结保护
    // gmin stepping：给非线性器件节点并联电导辅助收敛，从 gminStart 逐步减到 gmin
    double gminStart = 1e-2;  // 起始并联电导（大=线性化）
    uint32_t gminSteps = 10;  // gmin 递减步数
};

// 求解 DC 工作点。
DcOpResult solveDcOp(uint32_t numNodes,
                     const std::vector<std::unique_ptr<DeviceModel>>& devices,
                     const DcOpOptions& opts = {});

} // namespace rfsim

#endif // RFSIM_SOLVER_DC_OP_HPP
