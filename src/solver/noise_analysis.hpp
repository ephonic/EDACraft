// noise_analysis.hpp — 噪声分析（.noise）
//
// 优化项4：小信号噪声分析。线性电路（R/L/C/V/I）的噪声计算。
// 在每个频率点，电阻热噪声（4kTR）经电路传输到输出节点的总噪声功率谱密度。
//
// 方法：每个频率点建复数导纳矩阵 Y(jω)，对每个噪声源（每个 R 并联一个
// 噪声电流源 i_n² = 4kT/R），求 Y·V = e_k（e_k 在噪声源节点对注入单位电流），
// 得传输函数 H_k = V_out。输出噪声 PSD += |H_k|² × (4kT/R_k)。
//
// 完整线性噪声（R 热噪声），适用于 RLC 滤波器/匹配网络等无源电路。
// OSDI 非线性器件噪声（load_noise）需 AC 扩展支持工作点线性化，留后续。
#ifndef RFSIM_SOLVER_NOISE_ANALYSIS_HPP
#define RFSIM_SOLVER_NOISE_ANALYSIS_HPP

#include "../model/device_model.hpp"
#include "../model/builtin_devices.hpp"
#include "../rfsim.hpp"
#include <string>
#include <vector>

namespace rfsim {

struct NoisePoint {
    double freq;
    double outputNoisePSD;     // V²/Hz
    double outputNoiseDbV;     // dBV/√Hz（10·log10(√PSD)）
    double inputReferencedPSD; // V²/Hz（需输入源；否则 0）
};

struct NoiseResult {
    std::vector<NoisePoint> points;
    double integratedNoiseV;   // 积分输出噪声 RMS (V)
    std::string outputNodeName;
    uint32_t outputNodeId = 0;
    bool ok = false;
    Diagnostics diags;
};

struct NoiseSpec {
    uint32_t outputNodeId = 0;  // 噪声测量输出节点（NodeId，1-based）
    double startFreq = 1;
    double stopFreq = 1e9;
    int pointsPerDecade = 10;
};

NoiseResult solveNoise(uint32_t numNodes,
                       const std::vector<std::unique_ptr<DeviceModel>>& devices,
                       const NoiseSpec& spec,
                       double temperature = 300.15);

void writeNoiseResult(std::ostream& os, const NoiseResult& r);

} // namespace rfsim

#endif // RFSIM_SOLVER_NOISE_ANALYSIS_HPP
