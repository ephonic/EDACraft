// parser.hpp — SPICE 网表递归下降语法分析器
#ifndef RFSIM_PARSER_PARSER_HPP
#define RFSIM_PARSER_PARSER_HPP

#include "../rfsim.hpp"
#include "ast.hpp"
#include "token.hpp"
#include <string>

namespace rfsim {

// 解析选项
struct ParseOptions {
    bool caseInsensitive = true;   // HSPICE 不区分大小写（默认）
};

// 解析结果
struct ParseResult {
    Netlist     netlist;
    Diagnostics diags;
    bool        ok = false;

    [[nodiscard]] bool hasErrors() const { return diags.has_errors(); }
};

// 解析整段源文本
ParseResult parseNetlist(std::string source, std::string filename, ParseOptions opts = {});

// 解析文件（读取后调用 parseNetlist）
ParseResult parseFile(const std::string& path, ParseOptions opts = {});

} // namespace rfsim

#endif // RFSIM_PARSER_PARSER_HPP
