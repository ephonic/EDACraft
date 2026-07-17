// dc_op.hpp — DC 工作点分析（含非线性 Newton 迭代）
//
// 装配 MNA → 若含非线性器件则 Newton 迭代（每步重 stamp OSDI 雅可比+残差）
// → LU 求解 → 收敛检查 → 提取节点电压。
#ifndef RFSIM_SOLVER_DC_OP_HPP
#define RFSIM_SOLVER_DC_OP_HPP

#include "../assembly/mna.hpp"
#include "../assembly/linear_solver_factory.hpp"
#include "../model/device_model.hpp"
#include "../util/bench.hpp"
#include "gmin_options.hpp"
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

    // P1-7 / B4: gmin homotopy floor-accept path coverage.
    // floorAcceptsInner: count of inner-Newton "residual floor" accepts
    //   (alpha <<1 + |F| stagnant -> accept current point as gmin-step solution).
    // floorAcceptOuter:  full gmin sweep failed to reach target gmin; we fell
    //   back to the last converged gmin OP (early break path).
    uint32_t floorAcceptsInner = 0;
    bool floorAcceptOuter = false;

    // V2-γ C3: 性能计数器（RFSIM_BENCH_JSON=1 时填充）
    BenchCounters bench;
};

// Newton 迭代参数
struct DcOpOptions {
    uint32_t maxIterations = 100;
    double reltol = 1e-6;     // 相对收敛容差
    double abstol = 1e-12;    // 绝对收敛容差（A/V）
    double dvmax = 0.1;       // 单步节点电压最大变化（V），PN 结保护
    // P1-8: 共享 gmin 配置；DcOp 历史默认开启同伦（gminSteps=10）。
    // 字段顺序见 GminOptions：{gmin, gminStart, gminSteps}。
    GminOptions gmin{1e-12, 1e-2, 10};

    // V2-γ source stepping：把所有 VS 电压乘以 vsScale（0..1）后求解。
    // 用于 solveDcOp 外层"源步进"同伦：当级联 MOSFET 拓扑在 V_spec 下无法
    // 从冷启动收敛（OSDI limiter 在 V_DS=0 处产生大量级负 Jacobian 项），
    // 通过 ε∈{0.1,...,1.0} 多步 warm-start 解出最终工作点。
    // 装配阶段对 VS 电压做 V *= vsScale。
    double vsScale = 1.0;

    // 源步进同伦的中间步数（0 表示禁用，>=1 表示先以 ε<1 做若干步，
    // 再以 ε=1 做最终一步）。仅当存在非线性器件时启用。
    uint32_t sourceStepCount = 0;

    // A1-7：线性求解方法（默认 Auto）。从 .options method=<name> 解析。
    // Auto 按规模/稀疏度选 KLU / DenseLu；显式可指定 klu/dense/bicgstab。
    SolverMethod solver = SolverMethod::Auto;
};

// 求解 DC 工作点。
DcOpResult solveDcOp(uint32_t numNodes,
                     const std::vector<std::unique_ptr<DeviceModel>>& devices,
                     const DcOpOptions& opts = {});

} // namespace rfsim

#endif // RFSIM_SOLVER_DC_OP_HPP
