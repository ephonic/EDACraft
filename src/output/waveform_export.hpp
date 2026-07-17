// waveform_export.hpp — 波形多格式导出
//
// Phase D：把 TimeDomainResult（时域波形）导出为多种格式，供外部工具/查看器消费：
//   - CSV：rfsim 原生格式（time,v1,v2,...,i0,i1,...），向后兼容 waveview.py
//   - Rawfile：ngspice/ltx ASCII "raw" 格式（Title/Date/Plotname/Variables/Values，
//     兼容 ngspice/GTKWave/waveview 的 reader）
//   - JSON：结构化（time + signals 数组），便于 web 端 / 脚本消费
//
// 调用方（cli/main.cpp）按 .options post/format=<fmt> 选择格式，默认 csv。
// 节点名从 Circuit.nodes 取（若提供）；否则用 v1/v2/... 占位。
#ifndef RFSIM_OUTPUT_WAVEFORM_EXPORT_HPP
#define RFSIM_OUTPUT_WAVEFORM_EXPORT_HPP

#include "../solver/time_stepper.hpp"
#include "../circuit/circuit.hpp"
#include <iosfwd>
#include <string>
#include <vector>

namespace rfsim {

// 导出格式
enum class WaveFormat {
    Csv,      // rfsim 原生 CSV
    Rawfile,  // ngspice ASCII raw
    Json,     // 结构化 JSON
    All       // 全部（每种各写一个文件，后缀 .csv/.raw/.json）
};

// 从 .options format=<name> 解析格式。未知名返回 Csv。
WaveFormat parseWaveFormat(const std::string& name);
const char* waveFormatName(WaveFormat f);

// 生成信号名列表：节点电压（v(nodename) 或 vN）+ 分支电流（i(branchname) 或 iN）。
// nodes 可为空（用 v1/v2...）；若提供则用节点名。
std::vector<std::string> waveformSignalNames(const TimeDomainResult& w,
                                             const Circuit* c = nullptr);

// 各格式写入（到 stream）
void writeWaveformCsv(std::ostream& os, const TimeDomainResult& w,
                      const std::vector<std::string>& signalNames,
                      const std::string& title = "");
void writeWaveformRawfile(std::ostream& os, const TimeDomainResult& w,
                          const std::vector<std::string>& signalNames,
                          const std::string& title = "",
                          const std::string& plotname = "transient");
void writeWaveformJson(std::ostream& os, const TimeDomainResult& w,
                       const std::vector<std::string>& signalNames,
                       const std::string& title = "");

// 便捷：按格式写文件（basePath 无后缀，自动加 .csv/.raw/.json）。
// format=All 时写三种。返回实际写入的文件路径列表。
std::vector<std::string> writeWaveformFile(const std::string& basePath,
                                           const std::string& suffix,
                                           WaveFormat format,
                                           const TimeDomainResult& w,
                                           const Circuit* c = nullptr,
                                           const std::string& title = "",
                                           const std::string& plotname = "transient");

} // namespace rfsim

#endif // RFSIM_OUTPUT_WAVEFORM_EXPORT_HPP
