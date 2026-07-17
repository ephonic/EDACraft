// hspice_out.hpp — HSPICE 兼容输出（plan.md §4.7 R6）
//
// 输出格式：
//   1. .lis 列表文件：banner、网表回显、节点表、分析结果、测量
//   2. .print 表格：ASCII 列表（节点电压/电流 vs 扫描变量/频率/时间）
//   3. .measure 结果
//   4. 二进制 .tr0/.ac0/.sw0（HSPICE 私有格式，后续实现）
//
// v1 先实现 ASCII 部分（.lis + .print 表格），二进制 .tr0 待逆向格式后补。
#ifndef RFSIM_OUTPUT_HSPICE_OUT_HPP
#define RFSIM_OUTPUT_HSPICE_OUT_HPP

#include "../solver/dc_op.hpp"
#include "../solver/dc_sweep.hpp"
#include "../solver/ac_analysis.hpp"
#include "../solver/hb_solver.hpp"
#include "../circuit/circuit.hpp"
#include <ostream>
#include <string>

namespace rfsim {

// 输出 banner（仿真器标识 + 版本 + 时间）
void writeBanner(std::ostream& os);

// 输出网表回显
void writeNetlistEcho(std::ostream& os, const std::string& title, const std::string& source);

// 输出节点表
void writeNodeTable(std::ostream& os, const Circuit& c);

// 输出 DC 工作点结果（.lis 风格）
void writeDcOp(std::ostream& os, const Circuit& c, const DcOpResult& r);

// 输出 DC 扫描结果（.print 表格风格）
void writeDcSweep(std::ostream& os, const Circuit& c, const DcSweepResult& r);

// 输出 AC 分析结果（.print 频率响应表格：mag/phase）
void writeAc(std::ostream& os, const Circuit& c, const AcResult& r);

// 输出 HB 分析结果（谐波幅度/相位表 + 可选时域波形）
void writeHb(std::ostream& os, const Circuit& c, const HbResult& r, bool includeWaveform = true);

// 便捷：把整个仿真结果写入 .lis 文件
void writeListing(const std::string& path,
                  const Circuit& c,
                  const std::string& source);

} // namespace rfsim

#endif // RFSIM_OUTPUT_HSPICE_OUT_HPP
