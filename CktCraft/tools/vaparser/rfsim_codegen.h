// rfsim_codegen.h - rfsim DeviceModel C++ 代码生成器
//
// 从 Verilog-A Parser 的 module AST 生成继承 DeviceModel 的 C++ 代码。
// 替代 xyce_vcomp.cpp 的 Xyce 格式输出。
#ifndef RFSIM_CODEGEN_H
#define RFSIM_CODEGEN_H

#include "vaParser.h"
#include <string>

// 生成 DeviceModel 子类的 .h 和 .cpp 文件
void RfsimGenerateHeader(module* mod, const std::string& filename);
void RfsimGenerateSource(module* mod, const std::string& filename);
void RfsimGenerateRegSnippet(module* mod, const std::string& filename);

// rfsim 版的 EquationGenerator / JacobiGenerator
void RfsimEquationGenerator(module* mod, std::ofstream& ofs);
void RfsimJacobiGenerator(module* mod, std::ofstream& ofs);

#endif // RFSIM_CODEGEN_H
