// ast.hpp — SPICE 网表抽象语法树
#ifndef RFSIM_PARSER_AST_HPP
#define RFSIM_PARSER_AST_HPP

#include "../rfsim.hpp"
#include <map>
#include <memory>
#include <string>
#include <variant>
#include <vector>

namespace rfsim {

// 参数值：可能是数值、字符串、或参数表达式引用（名字）
// M1 阶段表达式暂存原始文本，由 expression.cpp 求值
struct ParamValue {
    enum class Kind { Number, String, Expr } kind = Kind::Number;
    double      num = 0.0;
    std::string str;          // String 或 Expr 的原始文本
    SourceLoc   loc;
};

// 参数表：name -> value（保留插入顺序用 vector<pair>）
using ParamList = std::vector<std::pair<std::string, ParamValue>>;

// 器件卡（元件实例）
// 例: R1 n1 n2 1k
//     M1 d g s b bsim4 w=1u l=180n
struct DeviceCard {
    std::string name;           // 如 "r1", "m1"（已小写化）
    char        firstLetter = 0;// 原始首字母（大写小写都归一，但保留首字母判断类型）
    std::vector<std::string> nodes; // 节点名列表
    std::string model;          // 模型名（半导体器件；R/L/C/V/I 通常无）
    ParamList   params;         // 位置参数与命名参数混合（位置参数用空 name 占位）
    SourceLoc   loc;

    // 位置参数（非命名）单独抽出，便于 R/L/C 的值取值
    std::vector<ParamValue> positional;
};

// 模型卡: .model name type ( p1=v1 p2=v2 ... )
struct ModelCard {
    std::string name;           // 模型名（小写）
    std::string type;           // nmos/pmos/npn/pnp/d/...
    ParamList   params;
    SourceLoc   loc;
};

// 子电路调用: Xname n1 n2 ... subname ( params... )
struct SubcktCall {
    std::string name;
    std::vector<std::string> nodes;     // 实际连接节点
    std::string subcktName;             // 被调用的子电路名
    ParamList   params;                 // 实参
    SourceLoc   loc;
};

// 控制卡（点命令）：.tran / .ac / .dc / .hb / .print / .measure / .options / .param / .lib / ...
struct ControlCard {
    std::string command;       // 如 "tran", "hb", "print"（小写，无点）
    ParamList   params;        // 通用参数表（位置+命名）
    std::vector<std::string> args; // 位置字符串参数（如 .print 的节点表达式）
    SourceLoc   loc;
};

// 前置声明 SubcktDef（shared_ptr<SubcktDef> 不需要完整类型）
struct SubcktDef;

// 网表语句的统一变体类型
using NetlistItem = std::variant<DeviceCard, ModelCard, SubcktCall, std::shared_ptr<SubcktDef>, ControlCard>;

// 子电路定义: .subckt name n1 n2 ... ( params... ) ... .ends
struct SubcktDef {
    std::string name;
    std::vector<std::string> ports;     // 端口节点名
    ParamList   params;                 // 形参默认值
    std::vector<NetlistItem> body;      // 体内容（器件/模型/嵌套子电路/控制卡）
    SourceLoc   loc;
};

// 顶层网表：一个全局语句序列
struct Netlist {
    std::string title;         // 第一行（注释/标题）
    std::vector<NetlistItem> items;
    // 全局 .param
    ParamList globalParams;
};

} // namespace rfsim

#endif // RFSIM_PARSER_AST_HPP
