// ac_analysis.hpp — 线性 AC 小信号分析
//
// 在 DC 工作点附近线性化，对每个频率求解复数线性系统 (G + jωC)·v = i_ac。
// L/C 用频域导纳: Y_C = jωC, Y_L = 1/(jωL)。
// R 用导纳 1/R。电压源/电流源的 AC 分量作为激励。
//
// 注意: 当前 AC 假设电路线性（无非线性器件贡献）。完整 AC（含非线性器件
// 在工作点线性化）待 OSDI 接入后扩展——非线性器件的 C/G 矩阵从工作点取。
#ifndef RFSIM_SOLVER_AC_ANALYSIS_HPP
#define RFSIM_SOLVER_AC_ANALYSIS_HPP

#include "../model/device_model.hpp"
#include "../model/builtin_devices.hpp"
#include "../circuit/circuit.hpp"
#include "../rfsim.hpp"
#include <string>
#include <vector>

namespace rfsim {

struct AcPoint {
    double freq;                          // 频率 Hz
    std::vector<Complex> nodeVoltages;    // 复节点电压（索引=NodeId，0=地）
};

struct AcResult {
    std::vector<AcPoint> points;
    bool ok = false;
    Diagnostics diags;
};

struct AcSpec {
    double startFreq = 0;
    double stopFreq = 0;
    int    pointsPerDecade = 10;  // DEC 扫描
    enum class Sweep { Dec, Lin } sweep = Sweep::Dec;
};

// 执行 AC 分析。
//   numNodes: 非地节点数
//   devices:  器件 wrapper（需含 C/L 的电容/电感值，R 的阻值，源的 AC 幅度）
//   freqs:    显式频率列表（若非空则覆盖 spec）
AcResult solveAc(uint32_t numNodes,
                 const std::vector<std::unique_ptr<DeviceModel>>& devices,
                 const AcSpec& spec,
                 const std::vector<double>& freqs = {});

} // namespace rfsim

#endif // RFSIM_SOLVER_AC_ANALYSIS_HPP
