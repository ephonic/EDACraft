// measure.hpp — .measure 测量指令求值
//
// 优化项2：HSPICE .measure 后端。parser 已把 .measure 解析成 ControlCard；
// 本模块在仿真结果（transient 波形 / DC sweep / AC 频率响应）上求值测量。
//
// 支持的测量类型（tran，最常用）：
//   .measure tran <name> max v(out)          最大值
//   .measure tran <name> min v(out)          最小值
//   .measure tran <name> pp  v(out)          峰峰值 (max - min)
//   .measure tran <name> avg v(out)          平均值
//   .measure tran <name> rms v(out)          有效值
//   .measure tran <name> when v(out)=<val> [rise|fall|cross]=<N>  首次/第N次穿越
//   .measure tran <name> trig v(a)=<va> targ v(b)=<vb>            延迟（trig→targ）
//
// 可选子句（适用于所有类型）：
//   from=<t1> to=<t2>   限定时间窗口
//
// 不支持（留后续）：deriv/integ/find/param-driven 测量、AC/DC measure。
#ifndef RFSIM_OUTPUT_MEASURE_HPP
#define RFSIM_OUTPUT_MEASURE_HPP

#include "../solver/time_stepper.hpp"
#include "../circuit/circuit.hpp"
#include "../parser/ast.hpp"
#include <iostream>
#include <string>
#include <vector>

namespace rfsim {

// 单次测量结果
struct MeasureResult {
    std::string name;        // 测量名
    std::string analysis;    // "tran"/"ac"/"dc"
    std::string type;        // "max"/"min"/"pp"/"avg"/"rms"/"when"/"delay"
    double value = 0.0;      // 测量值
    bool ok = false;         // 是否成功（找到穿越点等）
    std::string message;     // 诊断信息（失败原因或附注）
};

// 从 ControlCard（.measure）+ transient 波形求值一个测量。
// circuit 用于把节点名解析为 NodeId（信号索引）。
MeasureResult evaluateMeasureTran(const ControlCard& card,
                                  const TimeDomainResult& wave,
                                  const Circuit& circuit);

// 批量求值：对网表中所有 .measure 卡在给定波形上求值，打印到 os。
// 返回各测量结果。
std::vector<MeasureResult> evaluateAllMeasures(
    const std::vector<ControlCard>& controls,
    const TimeDomainResult& wave,
    const Circuit& circuit,
    std::ostream& os = std::cout);

} // namespace rfsim

#endif // RFSIM_OUTPUT_MEASURE_HPP
