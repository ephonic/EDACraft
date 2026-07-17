// circuit.hpp — 扁平化后的电路对象（供装配/求解层使用）
#ifndef RFSIM_CIRCUIT_CIRCUIT_HPP
#define RFSIM_CIRCUIT_CIRCUIT_HPP

#include "../rfsim.hpp"
#include "node_table.hpp"
#include "../parser/ast.hpp"
#include <string>
#include <vector>

namespace rfsim {

// 扁平化后的器件实例（节点已解析为 NodeId）
struct FlatDevice {
    std::string name;           // 实例名（带层级前缀，如 x1.m5）
    char        firstLetter = 0;// R/L/C/V/I/M/Q/D/...
    std::string model;          // 模型名（半导体器件；空表示内置线性器件）
    std::vector<NodeId> nodes;  // 已解析的节点索引
    ParamList   params;         // 命名参数
    std::vector<ParamValue> positional; // 位置参数
    SourceLoc   loc;
};

// 扁平化后的模型表
struct FlatModel {
    std::string name;
    std::string type;           // nmos/pmos/npn/pnp/d/...
    ParamList   params;
    SourceLoc   loc;
};

// 扁平化电路：节点表 + 器件列表 + 模型表 + 分析/输出控制卡 + 全局参数
struct Circuit {
    NodeTable nodes;
    std::vector<FlatDevice>  devices;
    std::vector<FlatModel>   models;
    std::vector<ControlCard> controls;   // 分析与输出控制卡
    ParamList                globalParams;
    std::string              title;
};

// 控制卡分类（便于求解/输出层取用）
[[nodiscard]] inline bool isAnalysisCard(const std::string& cmd) {
    return cmd == "hb" || cmd == "ac" || cmd == "dc" || cmd == "tran" || cmd == "op" || cmd == "pss";
}

} // namespace rfsim

#endif // RFSIM_CIRCUIT_CIRCUIT_HPP
