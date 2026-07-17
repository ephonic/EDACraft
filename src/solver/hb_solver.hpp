// hb_solver.hpp — Harmonic Balance 求解器（plan.md §4.5 M3）
//
// 单音 HB：基频 f0，谐波集 K={0,1,...,NH}。每节点每谐波一个复未知数。
// 线性电路 HB 退化为各谐波独立频域 MNA（每谐波一次复求解）。
// 非线性电路需 Newton 迭代（IFFT→eval→FFT 装配，§4.4），M3 先实现线性。
//
// 求解流程（线性）：
//   for k in 0..NH:
//     装配频域 MNA: Y_k(ω_k) · V_k = I_source_k
//     复 LU 求解得各节点第 k 谐波电压
//   输出：各节点各谐波复幅度（可 IFFT 到时域波形）
#ifndef RFSIM_SOLVER_HB_SOLVER_HPP
#define RFSIM_SOLVER_HB_SOLVER_HPP

#include "../model/device_model.hpp"
#include "../model/builtin_devices.hpp"
#include "../rfsim.hpp"
#include <complex>
#include <string>
#include <vector>

namespace rfsim {

// HB 配置
struct HbConfig {
    double fundamental = 1e9;   // 基频 Hz
    uint32_t numHarmonics = 5;  // NH（谐波 0..NH，0=DC）
    // A2-1：FFT 过采样因子。卷积采样点数 N = 2*oversample*(NH+1)。
    //   oversample=1 → N=2(NH+1)（最低采样，易混叠，原行为）；
    //   oversample=2 → N=4(NH+1)（默认，吸收高次谐波混叠，改善 HB-NL 收敛，KI-1 根因之二）。
    // 提升采样数会增加每 Newton 步的 OSDI eval 次数（线性），但显著降低卷积混叠噪声。
    uint32_t oversample = 2;
    // 源的各谐波激励（按源名 -> 谐波复幅度）。M3 简化：正弦源只激励基频(1次谐波)。
};

// 单节点的谐波电压（谐波 0=DC, 1..NH）
struct NodeHarmonics {
    std::vector<Complex> v;  // v[k] = 第 k 谐波复电压
};

struct HbResult {
    // 节点谐波电压（索引=NodeId，0=地）
    std::vector<NodeHarmonics> nodeVoltages;
    bool ok = false;
    Diagnostics diags;
    HbConfig config;
};

// 求解单音 HB（线性电路）。
//   numNodes: 非地节点数
//   devices:  器件（线性 R/L/C/V/I；V/I 源的正弦分量作为谐波激励）
//   config:   基频与谐波数
HbResult solveHbLinear(uint32_t numNodes,
                       const std::vector<std::unique_ptr<DeviceModel>>& devices,
                       const HbConfig& config);

// 将节点谐波电压 IFFT 为时域波形（2*(NH+1) 点）
// 返回 [numTimePoints] 个时刻的实电压
std::vector<double> nodeHarmonicsToWaveform(const NodeHarmonics& nh, uint32_t numHarmonics);

} // namespace rfsim

#endif // RFSIM_SOLVER_HB_SOLVER_HPP
