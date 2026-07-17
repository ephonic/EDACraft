// dc_sweep.hpp — DC 扫描分析
//
// 扫描一个电压源/电流源（或参数）的值，对每个扫描点求解 DC 工作点，
// 记录指定节点的电压，供输出层绘制 DC 传输曲线。
//
// 语法（HSPICE 风格）: .dc V1 0 5 0.1     （扫 V1 从 0 到 5，步长 0.1）
//                      .dc I1 1m 10m 1m
#ifndef RFSIM_SOLVER_DC_SWEEP_HPP
#define RFSIM_SOLVER_DC_SWEEP_HPP

#include "dc_op.hpp"
#include "../model/device_model.hpp"
#include "../model/builtin_devices.hpp"
#include <string>
#include <vector>

namespace rfsim {

// 单次扫描点结果
struct DcSweepPoint {
    double sweepValue;                 // 扫描变量的值
    std::vector<double> nodeVoltages;  // 各节点电压（索引=NodeId）
};

struct DcSweepResult {
    std::string sweepSourceName;       // 被扫描的源名
    std::vector<DcSweepPoint> points;  // 各扫描点
    bool ok = false;
    Diagnostics diags;
};

struct DcSweepSpec {
    std::string sourceName;  // 被扫描源名（如 "v1"）
    double start = 0;
    double stop = 0;
    double step = 0;
};

// 执行 DC 扫描。
//   numNodes: 非地节点数
//   devices:  器件 wrapper 列表（会被原地修改源值）
//   spec:     扫描规格
// 扫描方向自动适应 start/stop 大小关系；step 取绝对值。
DcSweepResult solveDcSweep(uint32_t numNodes,
                           std::vector<std::unique_ptr<DeviceModel>>& devices,
                           const DcSweepSpec& spec);

} // namespace rfsim

#endif // RFSIM_SOLVER_DC_SWEEP_HPP
