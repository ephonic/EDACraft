// fourier.hpp - .four 傅里叶分析
//
// 对 transient 波形做 DFT，提取指定基频的谐波幅度/相位。
// HSPICE 语法: .four <freq> <output_var> [nharm]
//   freq = 基频 Hz
//   output_var = v(node) 或 i(vsource)
//   nharm = 谐波数（默认 10）
//
// 输出：DC 分量 + 各次谐波的幅度/相位/归一化幅度
#ifndef RFSIM_OUTPUT_FOURIER_HPP
#define RFSIM_OUTPUT_FOURIER_HPP

#include "../solver/time_stepper.hpp"
#include "../circuit/circuit.hpp"
#include "../rfsim.hpp"
#include <complex>
#include <string>
#include <vector>

namespace rfsim {

struct FourierHarmonic {
    uint32_t order;       // 谐波次数（0=DC, 1=基频, 2..N）
    double magnitude;     // 幅度
    double phaseDeg;      // 相位（度）
    double normMag;       // 归一化幅度（相对于基频）
};

struct FourierResult {
    std::vector<FourierHarmonic> harmonics;
    double fundamentalFreq;
    std::string signal;
    double thd;           // 总谐波失真 (%)
    bool ok = false;
    std::string message;
};

// 对 transient 波形的指定信号做 DFT。
//   wave: transient 结果
//   circuit: 电路（节点名解析）
//   freq: 基频 Hz
//   signalExpr: "v(out)" 或 "i(0)" 等
//   numHarmonics: 谐波数（默认 10）
FourierResult computeFourier(const TimeDomainResult& wave,
                             const Circuit& circuit,
                             double freq,
                             const std::string& signalExpr,
                             uint32_t numHarmonics = 10);

// 打印傅里叶分析结果
void writeFourier(std::ostream& os, const FourierResult& r);

} // namespace rfsim

#endif // RFSIM_OUTPUT_FOURIER_HPP
