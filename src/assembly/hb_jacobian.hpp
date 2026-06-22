// hb_jacobian.hpp - Harmonic Balance 实数化频域雅可比与残差装配
//
// 将线性器件的频域导纳 stamp 与非线性器件的时域雅可比卷积统一装配为
// 实数稠密 Jacobian J 与残差 F，供 Newton 步直接 LU 求解或 GMRES 使用。
//
// 未知量布局（每 entity）：
//   [V^(0), Re V^(1), Im V^(1), ..., Re V^(NH), Im V^(NH)]
// entity 0 = 地，entity 1..numNodes = 节点电压，entity numNodes+1.. = 电压源分支电流。
//
// 复数谐波 Jacobian 块 J^{complex}_{k,m} 转实数块：
//   k=0,m=0        : 1x1  = Re(J)
//   k=0,m>=1       : 1x2  = [ Re(J), -Im(J) ]
//   k>=1,m=0       : 2x1  = [ Re(J); Im(J) ]
//   k>=1,m>=1      : 2x2  = [[ Re(J), -Im(J) ], [ Im(J), Re(J) ]]
#ifndef RFSIM_ASSEMBLY_HB_JACOBIAN_HPP
#define RFSIM_ASSEMBLY_HB_JACOBIAN_HPP

#include "../model/device_model.hpp"
#include "../solver/hb_solver.hpp"
#include "../rfsim.hpp"
#include <cstdint>
#include <vector>
#include <memory>

namespace rfsim {

struct HbRealSystem {
    uint32_t dim = 0;          // 实数未知量总数
    uint32_t numNodes = 0;     // 非地节点数
    uint32_t numVS = 0;        // 电压源数（分支扩维）
    uint32_t nEntities = 0;    // 总 entity 数 = numNodes + numVS
    uint32_t NH = 0;           // 最高谐波
    uint32_t perEntity = 0;    // 每 entity 的实数分量数 = 1 + 2*NH

    std::vector<double> F;     // 残差，长度 dim
    std::vector<double> J;     // 稠密 Jacobian，行主序 dim x dim
};

// 装配完整频域 HB 残差与雅可比。
//   numNodes:       非地节点数
//   devices:        器件列表（含 R/L/C/V/I/OSDI）
//   config:         HB 配置
//   X:              当前猜测（实数化统一索引，X[0]=地，X[1..numNodes]=节点电压，
//                   X[numNodes+1..numNodes+numVS]=电压源分支电流）
//   sys:            输出残差与雅可比
// 返回 false 若装配过程中出现奇异/错误。
bool assembleHarmonicBalanceReal(
    uint32_t numNodes,
    const std::vector<std::unique_ptr<DeviceModel>>& devices,
    const HbConfig& config,
    const std::vector<std::vector<Complex>>& X,
    HbRealSystem& sys,
    Diagnostics& diags,
    double sourceScale = 1.0,
    double gmin = 0.0);

// 将复数谐波向量按实数化布局写入目标位置。
// 用于从实数解 dx 中提取并更新复数谐波未知量。
void realToHarmonic(const HbRealSystem& sys,
                    const std::vector<double>& x,
                    std::vector<std::vector<Complex>>& X);

// 周期实信号采样 -> 单边谐波复幅度（k=0..NH）。
// 输入 N=t.size() 个等间距采样覆盖一个完整周期；
// 输出 h[0]=DC 直流分量，h[k>=1]=第 k 谐波单边复幅度
//   即 v(t) ≈ Re{ h[0] + sum_{k=1..NH} h[k] e^{j k w0 t} }
// 与现有 nodeHarmonicsToWaveform 互逆。要求 N >= 2*(NH+1)。
std::vector<Complex> realSamplesToHarmonics(const std::vector<double>& t, uint32_t NH);

} // namespace rfsim

#endif // RFSIM_ASSEMBLY_HB_JACOBIAN_HPP
