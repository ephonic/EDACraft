// rfsim.hpp — 跨模块共享的公共类型与工具
#ifndef RFSIM_RFSIM_HPP
#define RFSIM_RFSIM_HPP

#include <complex>
#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

namespace rfsim {

// 复数类型（AC 小信号与 HB 频域共用）
using Complex = std::complex<double>;

// 节点索引：0 保留为地（GND/0），从 1 开始编号
using NodeId   = uint32_t;
// 器件实例索引
using DeviceId = uint32_t;

// 复数未知数实数化存储时的实/虚分量索引约定（HB 求解层使用，此处仅声明）
// 约定: 索引 2k 为 Re, 2k+1 为 Im

// 统一的源码位置，用于错误报告
struct SourceLoc {
    std::string file;     // 文件名（.include/.lib 解析后可能不同）
    uint32_t    line = 0; // 1-based 行号
    uint32_t    col  = 0; // 1-based 列号
};

// 通用错误类型：携带位置与消息
struct Error {
    SourceLoc   loc;
    std::string message;
};

// 诊断信息收集（解析期累积，不抛异常以支持错误恢复）
struct Diagnostics {
    std::vector<Error> errors;
    std::vector<Error> warnings;

    [[nodiscard]] bool has_errors() const noexcept { return !errors.empty(); }
    void error(SourceLoc loc, std::string msg)  { errors.push_back({std::move(loc), std::move(msg)}); }
    void warn (SourceLoc loc, std::string msg)  { warnings.push_back({std::move(loc), std::move(msg)}); }
};

} // namespace rfsim

#endif // RFSIM_RFSIM_HPP
