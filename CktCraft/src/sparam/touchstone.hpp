// touchstone.hpp — Touchstone .sNp 文件解析
//
// 支持 Touchstone 1.0 格式：
// - .s1p / .s2p / .s3p / ... / .sNp
// - 数据格式：RI（实虚部）、MA（幅度角度°）、DB（dB 角度°）
// - 频率单位：Hz / kHz / MHz / GHz（从 option line 或文件扩展推断）
// - 注释行：以 ! 开头
// - Option line：# freq_type data_type Z0（如 # MHz S RI R 50）
#ifndef RFSIM_SPARAM_TOUCHSTONE_HPP
#define RFSIM_SPARAM_TOUCHSTONE_HPP

#include <complex>
#include <cstdint>
#include <string>
#include <vector>

namespace rfsim {

using Complex = std::complex<double>;

struct TouchstoneData {
    uint32_t numPorts = 0;
    std::vector<double> freqs;               // Hz
    std::vector<std::vector<Complex>> S;      // S[freq_index][port_i * N + port_j]
    double refImpedance = 50.0;              // 参考阻抗 (Ω)
    std::string format = "RI";               // "RI" / "MA" / "DB"
    std::string freqUnit = "GHz";            // 频率单位

    [[nodiscard]] size_t numFreqs() const { return freqs.size(); }
    [[nodiscard]] size_t numSParams() const { return numPorts * numPorts; }
};

// 解析 Touchstone 文件。失败时抛出 std::runtime_error。
TouchstoneData parseTouchstone(const std::string& path);

// S → Y 参数转换（单频率点）
// Y = (1/Z0) * (I - S)^{-1} * (I + S) * (1/Z0)
// 输入 S: N×N 个 Complex（行优先），Z0: 参考阻抗
// 输出 Y: N×N 个 Complex（行优先）
std::vector<Complex> sToY(const std::vector<Complex>& S, uint32_t N, double Z0);

// 频率插值：在 TouchstoneData 中按频率查找并线性插值 S 参数
// 返回 N×N 个 Complex（行优先）
std::vector<Complex> interpolateS(const TouchstoneData& td, double freq);

} // namespace rfsim

#endif // RFSIM_SPARAM_TOUCHSTONE_HPP
